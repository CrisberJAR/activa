from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.config import cargar_necesidades, settings
from app.db import SessionLocal
from app.models import AnalisisBloque, Bloque, Encuesta, Usuario
from app.services import ia
from app.services.analisis import calcular_indicadores, clasificar, ranking_necesidades
from tests.conftest import ASESOR, GERENTE, iniciar_sesion

CONFIG = cargar_necesidades()


def encuesta(**cambios) -> dict:
    datos = {
        "zona": "Amarilis", "sector": "agricola", "ingreso_mensual": Decimal("1500"), "anios_negocio": 5,
        "trabajadores": 1, "frecuencia_ingresos": "cosecha", "credito_vigente": False, "garantia": "ninguna",
        "necesidad": "Comprar semillas antes de las lluvias", "monto": Decimal("3000"), "plazo_meses": 6,
        "temporada_necesidad": "lluvias", "riesgo_principal": "lluvias", "interes_campana": True,
        "contacto_preferido": "whatsapp",
    }
    return datos | cambios


# ---------- Clasificación de necesidades ----------

@pytest.mark.parametrize("texto, categoria", [
    ("Comprar semillas y abono antes de la siembra de lluvias", "insumos_agricolas"),
    ("Comprar fertilizante y fumigar antes de las lluvias", "insumos_agricolas"),
    ("Cambiar llantas y frenos antes de la temporada de lluvias", "vehiculo"),
    ("Pagar la conversión del auto a GLP", "vehiculo"),
    ("Reparar el canal de riego dañado por huaicos", "riego"),
    ("Contratar peones para la cosecha de maíz", "mano_obra"),
    ("Comprar un carrito con techo para vender emoliente", "equipamiento"),
    ("Aumentar MERCADERÍA para la campaña navideña", "mercaderia"),
    ("Surtir ropa de abrigo para el invierno", "mercaderia"),
    ("Comprar mallas antiheladas para el cultivo", "proteccion_clima"),
    ("Capital de trabajo para fiestas patrias", "capital_trabajo"),
    ("Viajar a Lima", "otros"),
])
def test_clasifica_necesidades_por_palabras_clave(texto, categoria):
    assert clasificar(texto, CONFIG) == categoria


def test_palabra_solo_cuenta_al_inicio_de_palabra():
    # "auto" no debe encontrarse dentro de "rauto"; "techo" sí dentro de "techos"
    assert clasificar("rauto", CONFIG) == "otros"
    assert clasificar("Arreglar techos", CONFIG) == "proteccion_clima"


# ---------- Indicadores y ranking ----------

def test_indicadores_del_bloque():
    encuestas = [
        encuesta(),
        encuesta(sector="taxista", ingreso_mensual=Decimal("2500"), monto=Decimal("2000"), plazo_meses=12,
                 credito_vigente=True, garantia="vehiculo", interes_campana=False, temporada_necesidad="verano"),
        encuesta(monto=Decimal("4000"), plazo_meses=6),
    ]
    ind = calcular_indicadores(encuestas)
    assert ind["total"] == 3
    assert ind["por_sector"] == {"agricola": 2, "taxista": 1}
    assert ind["sector_principal"] == "agricola" and ind["temporada_frecuente"] == "lluvias"
    assert ind["ingreso_promedio"] == pytest.approx(1833.3)
    assert ind["monto_promedio"] == 3000.0 and ind["monto_total"] == 9000.0
    assert ind["plazo_promedio"] == 8.0
    assert ind["pct_credito_vigente"] == 33.3 and ind["pct_interes"] == 66.7 and ind["pct_sin_garantia"] == 66.7


def test_ranking_ordenado_de_mayor_a_menor():
    encuestas = [
        encuesta(necesidad="Cambiar llantas", sector="taxista", monto=Decimal("1000")),
        encuesta(necesidad="Comprar semillas"),
        encuesta(necesidad="Comprar abono", monto=Decimal("5000")),
        encuesta(necesidad="Viajar"),
    ]
    ranking = ranking_necesidades(encuestas, CONFIG)
    assert [r["categoria"] for r in ranking] == ["insumos_agricolas", "vehiculo", "otros"]
    assert ranking[0]["cantidad"] == 2 and ranking[0]["porcentaje"] == 50.0
    assert ranking[0]["monto_promedio"] == 4000.0
    assert sum(r["porcentaje"] for r in ranking) == 100.0


# ---------- Anonimización y Gemini ----------

def test_anonimizar_quita_nombres_telefonos_y_correos():
    texto = "Rosa Quispe necesita mercadería, llamar al 987 654 321 o rosa@mail.com"
    limpio = ia.anonimizar(texto, ["Rosa Quispe Tarazona"])
    assert "Rosa" not in limpio and "Quispe" not in limpio
    assert "987" not in limpio and "@" not in limpio
    assert "mercadería" in limpio


def test_sin_clave_usa_texto_automatico():
    ranking = ranking_necesidades([encuesta()], CONFIG)
    patron = ia.texto_patron(calcular_indicadores([encuesta()]), ranking, ["x"], None)
    assert patron["fuente"] == "plantilla" and "GEMINI_API_KEY" in patron["error"]
    assert "Insumos agrícolas" in patron["texto"]


# ---------- Páginas y API ----------

def preparar_bloques():
    """Dos bloques: el análisis del primero no debe mezclar encuestas del segundo."""
    with SessionLocal() as db:
        asesor = db.scalar(select(Usuario).where(Usuario.email == ASESOR["email"]))
        b1 = Bloque(nombre="Valle", fecha_inicio=date(2026, 10, 1), creado_por=asesor.id)
        b2 = Bloque(nombre="Taxistas", fecha_inicio=date(2026, 10, 1), creado_por=asesor.id)
        vacio = Bloque(nombre="Vacío", fecha_inicio=date(2026, 10, 1), creado_por=asesor.id)
        db.add_all([b1, b2, vacio])
        db.flush()
        for i, (bloque, necesidad) in enumerate([
            (b1, "Comprar semillas"), (b1, "Comprar abono"), (b2, "Cambiar llantas"),
        ]):
            db.add(Encuesta(bloque_id=bloque.id, asesor_id=asesor.id, nombre=f"Cliente Secreto{i}",
                            telefono=f"98765432{i}", consentimiento=True, **encuesta(necesidad=necesidad)))
        db.commit()
        return b1.id, b2.id, vacio.id


def test_asesor_analiza_solo_las_encuestas_del_bloque(client):
    b1, _, _ = preparar_bloques()
    iniciar_sesion(client, ASESOR)
    assert client.post(f"/analisis/{b1}", follow_redirects=False).status_code == 303
    with SessionLocal() as db:
        analisis = db.scalar(select(AnalisisBloque))
        assert analisis.bloque_id == b1
        assert analisis.indicadores["total"] == 2
        assert [r["categoria"] for r in analisis.ranking_necesidades] == ["insumos_agricolas"]
        assert analisis.indicadores["fuente_texto"] == "plantilla"
    pagina = client.get(f"/analisis?bloque_id={b1}").text
    assert "Insumos agrícolas" in pagina and "Texto automático" in pagina


def test_con_gemini_no_se_envian_datos_personales(client, monkeypatch):
    enviados = []

    def gemini_falso(prompt):
        enviados.append(prompt)
        return "Los clientes necesitan insumos antes de las lluvias.", "modelo-prueba"

    monkeypatch.setattr(ia, "llamar_gemini", gemini_falso)
    b1, _, _ = preparar_bloques()
    iniciar_sesion(client, GERENTE)
    client.post(f"/analisis/{b1}")
    prompt = enviados[0]
    assert "Secreto" not in prompt and "98765432" not in prompt
    assert "Comprar semillas" in prompt and "Cambiar llantas" not in prompt  # solo su bloque
    with SessionLocal() as db:
        analisis = db.scalar(select(AnalisisBloque))
        assert analisis.indicadores["fuente_texto"] == "gemini"
        assert analisis.indicadores["modelo_ia"] == "modelo-prueba"
        assert analisis.texto_patron.startswith("Los clientes")


def test_si_gemini_falla_se_usa_respaldo(client, monkeypatch):
    def gemini_caido(prompt):
        raise ia.ErrorIA("Se agotó la cuota gratuita de Gemini")

    monkeypatch.setattr(ia, "llamar_gemini", gemini_caido)
    b1, _, _ = preparar_bloques()
    iniciar_sesion(client, ASESOR)
    assert "cuota" in client.post(f"/analisis/{b1}").text
    with SessionLocal() as db:
        assert db.scalar(select(AnalisisBloque)).indicadores["fuente_texto"] == "plantilla"


def test_bloque_sin_encuestas_no_se_analiza(client):
    _, _, vacio = preparar_bloques()
    iniciar_sesion(client, ASESOR)
    assert "no tiene encuestas" in client.post(f"/analisis/{vacio}").text
    with SessionLocal() as db:
        assert db.scalar(select(AnalisisBloque)) is None


def test_api_requiere_sesion_y_devuelve_ultimo(client):
    b1, b2, _ = preparar_bloques()
    assert client.get(f"/api/analisis/{b1}").status_code == 401
    iniciar_sesion(client, ASESOR)
    assert client.get(f"/api/analisis/{b1}").status_code == 404  # aún sin análisis
    assert client.post(f"/api/analisis/{b2}").json()["indicadores"]["total"] == 1
    datos = client.get(f"/api/analisis/{b2}").json()
    assert datos["ranking_necesidades"][0]["categoria"] == "vehiculo"
    assert client.get("/api/analisis/9999").status_code == 404


class RespuestaFalsa:
    """Imita la respuesta HTTP de Gemini."""

    def __init__(self, status_code, texto="Hola"):
        self.status_code = status_code
        self.text = ""
        self._texto = texto

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": f" {self._texto} "}]}}]}


@pytest.fixture
def gemini_http(monkeypatch):
    """Simula Gemini por modelo: {modelo: código HTTP}. Devuelve la lista de modelos consultados."""
    monkeypatch.setattr(settings, "gemini_api_key", "clave-falsa")
    monkeypatch.setattr(settings, "gemini_modelo", "principal")
    monkeypatch.setattr(settings, "gemini_modelos_respaldo", "respaldo1, respaldo2")
    codigos, consultados = {}, []

    def post(url, **kwargs):
        modelo = url.split("/models/")[1].split(":")[0]
        consultados.append(modelo)
        return RespuestaFalsa(codigos.get(modelo, 200), texto=modelo)

    monkeypatch.setattr(ia.httpx, "post", post)
    return codigos, consultados


def test_gemini_lee_la_respuesta(gemini_http):
    assert ia.llamar_gemini("x") == ("principal", "principal")


def test_si_el_modelo_esta_saturado_usa_el_de_respaldo(gemini_http):
    codigos, consultados = gemini_http
    codigos.update({"principal": 503, "respaldo1": 429})
    assert ia.llamar_gemini("x") == ("respaldo2", "respaldo2")
    assert consultados == ["principal", "respaldo1", "respaldo2"]


def test_todos_saturados_da_error(gemini_http):
    codigos, _ = gemini_http
    codigos.update({"principal": 503, "respaldo1": 503, "respaldo2": 429})
    with pytest.raises(ia.ErrorIA, match="Ningún modelo"):
        ia.llamar_gemini("x")


def test_clave_invalida_no_prueba_otros_modelos(gemini_http):
    codigos, consultados = gemini_http
    codigos["principal"] = 403
    with pytest.raises(ia.ErrorIA, match="GEMINI_API_KEY"):
        ia.llamar_gemini("x")
    assert consultados == ["principal"]
