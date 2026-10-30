"""Revisión rápida antes de una demostración o de la sustentación.

Comprueba la conexión con Supabase, Gemini y Firebase, el modelo Random Forest
y que existan datos para mostrar. No modifica nada (solo lee).

Uso (desde backend/, con el entorno activado):
    python -m scripts.verificar_sistema
    python -m scripts.verificar_sistema --sin-gemini     # no gasta cuota de Gemini
"""
import argparse
from pathlib import Path

from sqlalchemy import func, select, text

from app.config import cargar_yaml, hoy_peru, settings
from app.db import SessionLocal
from app.models import Bloque, Encuesta, Interesado, RegistroDiario, Usuario
from app.services import campanas, firebase, ia, ml
from app.services.clima import diagnostico_actual

OK, AVISO, ERROR = "ok", "aviso", "error"
ICONOS = {OK: "[OK]   ", AVISO: "[AVISO]", ERROR: "[ERROR]"}
ALEMBIC = Path(__file__).resolve().parent.parent / "alembic.ini"


def revisar_base() -> list[tuple]:
    try:
        with SessionLocal() as db:
            db.execute(text("select 1"))
    except Exception as e:  # noqa: BLE001 - se informa cualquier fallo de conexión
        return [(ERROR, "Base de datos", f"No conecta ({type(e).__name__}). "
                 "Revisa en el panel de Supabase si el proyecto está pausado y DATABASE_URL en .env")]
    return [(OK, "Base de datos", "Conectada")] + [revisar_migraciones()]


def revisar_migraciones() -> tuple:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    ultima = ScriptDirectory.from_config(Config(str(ALEMBIC))).get_current_head()
    try:
        with SessionLocal() as db:
            actual = db.scalar(text("select version_num from alembic_version"))
    except Exception:  # noqa: BLE001
        actual = None
    if actual == ultima:
        return OK, "Migraciones", f"Al día ({ultima})"
    return ERROR, "Migraciones", f"La base está en {actual}, falta llegar a {ultima}: ejecuta alembic upgrade head"


def revisar_datos() -> list[tuple]:
    resultados = []
    try:
        with SessionLocal() as db:
            roles = set(db.scalars(select(Usuario.rol)))
            n_bloques = db.scalar(select(func.count(Bloque.id)))
            n_encuestas = db.scalar(select(func.count(Encuesta.id)))
            vigentes = campanas.vigentes(db)
            pendientes = db.scalar(select(func.count(Interesado.id)).where(Interesado.atendido.is_(False)))
            ultimo_dia = db.scalar(select(func.max(RegistroDiario.fecha)))
            diag = diagnostico_actual(db) if ultimo_dia else {}
    except Exception as e:  # noqa: BLE001
        return [(ERROR, "Datos", f"No se pudieron leer ({type(e).__name__})")]

    faltan = {"asesor", "gerente"} - roles
    resultados.append((ERROR, "Usuarios", f"Falta un usuario {', '.join(faltan)}: python -m scripts.seed_usuarios")
                      if faltan else (OK, "Usuarios", "Hay asesor y gerente"))
    resultados.append((OK if n_encuestas else AVISO, "Encuestas",
                       f"{n_bloques} bloques y {n_encuestas} encuestas" if n_encuestas
                       else "No hay encuestas: python -m scripts.seed_encuestas"))
    if vigentes:
        resultados.append((OK, "Campañas vigentes", ", ".join(c.nombre for c in vigentes)))
    else:
        resultados.append((AVISO, "Campañas vigentes",
                           "Ninguna: la página pública y Uku no tendrán qué ofrecer. Publica una como gerente"))
    resultados.append((OK, "Interesados", f"{pendientes} pendientes de atender"))
    if not ultimo_dia:
        resultados.append((AVISO, "Clima", "Sin registros: python -m scripts.generar_datos_clima --escenario lluvias"))
    else:
        antiguedad = (hoy_peru() - ultimo_dia).days
        estado = OK if antiguedad <= 2 else AVISO
        detalle = f"Último registro {ultimo_dia:%d/%m/%Y}"
        if diag.get("estacion_actual"):
            detalle += f"; estación {diag['estacion_nombre']}, temporada próxima {diag['temporada_nombre']}"
        if antiguedad > 2:
            detalle += ". Datos antiguos: vuelve a generar el escenario simulado o enciende el sensor en Wokwi"
        resultados.append((estado, "Clima", detalle))
    return resultados


def revisar_gemini(probar: bool) -> tuple:
    if not settings.gemini_api_key:
        return AVISO, "Gemini", "Falta GEMINI_API_KEY: el sistema usará las plantillas automáticas"
    if not probar:
        return OK, "Gemini", "Clave configurada (no probada)"
    try:
        _, modelo = ia.llamar_gemini("Responde solo: OK", timeout=20)
        return OK, "Gemini", f"Responde (modelo {modelo})"
    except ia.ErrorIA as e:
        return AVISO, "Gemini", f"No responde ({e}). El sistema seguirá con las plantillas"


def revisar_firebase() -> tuple:
    if not settings.firebase_db_url:
        return AVISO, "Firebase", "Falta FIREBASE_DB_URL en .env"
    try:
        ultimas = firebase.leer_ultimas()
    except Exception as e:  # noqa: BLE001
        return AVISO, "Firebase", f"No responde ({type(e).__name__}); el análisis usa los registros ya guardados"
    return OK, "Firebase", f"Conectado ({len(ultimas)} sensores con lecturas)"


def revisar_modelo() -> tuple:
    try:
        ml.cargar_modelo()
    except Exception as e:  # noqa: BLE001
        return ERROR, "Random Forest", f"No se pudo cargar ml/modelo.joblib ({type(e).__name__}): python -m ml.entrenar"
    metricas = ml.leer_metricas() or {}
    exactitud = metricas.get("prueba", {}).get("exactitud")
    return OK, "Random Forest", f"Cargado (exactitud {exactitud:.0%})" if exactitud else "Cargado"


def revisar_institucion() -> tuple:
    pendientes = [k for k, v in cargar_yaml("institucion")["contacto"].items() if "[COMPLETAR" in str(v)]
    if pendientes:
        return AVISO, "Datos de la empresa", f"Completar en config/institucion.yaml: {', '.join(pendientes)}"
    return OK, "Datos de la empresa", "Completos"


def revisar(probar_gemini: bool = True) -> list[tuple]:
    return [
        *revisar_base(), *revisar_datos(), revisar_modelo(),
        revisar_gemini(probar_gemini), revisar_firebase(), revisar_institucion(),
    ]


def main():
    parser = argparse.ArgumentParser(description="Revisión del sistema antes de una demostración")
    parser.add_argument("--sin-gemini", action="store_true", help="no hace la consulta de prueba a Gemini")
    args = parser.parse_args()

    resultados = revisar(probar_gemini=not args.sin_gemini)
    for estado, nombre, detalle in resultados:
        print(f"{ICONOS[estado]} {nombre}: {detalle}")
    errores = sum(r[0] == ERROR for r in resultados)
    avisos = sum(r[0] == AVISO for r in resultados)
    print()
    if errores:
        print(f"Hay {errores} error(es): corrígelos antes de la demostración.")
    elif avisos:
        print(f"Todo funciona, con {avisos} aviso(s) para revisar.")
    else:
        print("Todo listo para la demostración.")


if __name__ == "__main__":
    main()
