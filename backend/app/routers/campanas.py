"""Campañas: el asesor y el gerente las generan; SOLO el gerente edita, regenera, publica y retira."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalogos import TIPOS_CLIENTE
from app.config import cargar_tipos_campana
from app.db import get_db
from app.models import Bloque, Campana, Usuario
from app.schemas import CampanaContenido, CampanaEntrada, errores_es
from app.security import requiere_rol, usuario_web_o_api
from app.services import campanas as servicio
from app.services.clima import diagnostico_actual
from app.templating import avisar, templates

router = APIRouter()

ESTADOS = ["borrador", "programada", "vigente", "finalizada", "retirada"]
MAX_OBJECIONES = 6


def _estacion(db: Session) -> dict | None:
    diag = diagnostico_actual(db)
    return diag if diag.get("estacion_actual") else None


def _obtener(db: Session, campana_id: int) -> Campana:
    campana = db.get(Campana, campana_id)
    if not campana:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaña no encontrada")
    return campana


def _solo_borrador(campana: Campana) -> None:
    if campana.estado != "borrador":
        raise HTTPException(status.HTTP_409_CONFLICT, "Solo se pueden cambiar campañas en borrador")


def _volver(campana_id: int) -> RedirectResponse:
    return RedirectResponse(f"/campanas/{campana_id}", status.HTTP_303_SEE_OTHER)


def _contexto_formulario(db: Session) -> dict:
    return {
        "tipos": cargar_tipos_campana(),
        "tipos_cliente": TIPOS_CLIENTE,
        "bloques": db.scalars(select(Bloque).order_by(Bloque.fecha_inicio.desc())).all(),
    }


# ---------- Lista y detalle ----------

@router.get("/campanas")
def listar(
    request: Request,
    estado: str | None = None,
    usuario: Usuario = Depends(requiere_rol("asesor", "gerente")),
    db: Session = Depends(get_db),
):
    todas = db.scalars(select(Campana).order_by(Campana.creado_en.desc(), Campana.id.desc())).all()
    filas = [(c, servicio.estado_visible(c)) for c in todas]
    if estado:
        filas = [(c, e) for c, e in filas if e == estado]
    return templates.TemplateResponse(
        request, "campanas.html",
        {"usuario": usuario, "filas": filas, "estado": estado, "estados": ESTADOS, "tipos": cargar_tipos_campana()},
    )


@router.get("/campanas/nueva")
def nueva(
    request: Request,
    bloque_id: int | None = None,
    usuario: Usuario = Depends(requiere_rol("asesor", "gerente")),
    db: Session = Depends(get_db),
):
    v = servicio.valores_sugeridos(db, bloque_id, _estacion(db))
    return templates.TemplateResponse(
        request, "campana_form.html", {"usuario": usuario, "v": v, "errores": {}} | _contexto_formulario(db)
    )


@router.post("/campanas/nueva")
async def crear(
    request: Request, usuario: Usuario = Depends(requiere_rol("asesor", "gerente")), db: Session = Depends(get_db)
):
    datos = dict(await request.form())
    try:
        entrada = CampanaEntrada(**datos)
    except ValidationError as e:
        return templates.TemplateResponse(
            request, "campana_form.html",
            {"usuario": usuario, "v": datos, "errores": errores_es(e)} | _contexto_formulario(db),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    estacion = _estacion(db)
    contenido, generado_con, error = servicio.generar_contenido(entrada, servicio.contexto_bloque(db, entrada.bloque_id, estacion))
    campana = Campana(nombre=contenido["nombre"], contenido=contenido, generado_con=generado_con, creado_por=usuario.id)
    servicio.aplicar_entrada(campana, entrada)
    db.add(campana)
    db.commit()
    if error:
        avisar(request, f"Campaña creada con la plantilla automática. Gemini no respondió: {error}")
    else:
        avisar(request, f"Campaña generada con Gemini ({generado_con}). Queda en borrador hasta que el gerente la publique.")
    return _volver(campana.id)


@router.get("/campanas/{campana_id}")
def detalle(
    campana_id: int,
    request: Request,
    usuario: Usuario = Depends(requiere_rol("asesor", "gerente")),
    db: Session = Depends(get_db),
):
    campana = _obtener(db, campana_id)
    return templates.TemplateResponse(
        request, "campana_detalle.html",
        {"usuario": usuario, "c": campana, "estado": servicio.estado_visible(campana),
         "tipos": cargar_tipos_campana(), "tipos_cliente": TIPOS_CLIENTE},
    )


# ---------- Solo el gerente ----------

def _valores_edicion(c: Campana) -> dict:
    cont = c.contenido
    return {
        "nombre": cont["nombre"],
        "propuesta_valor": cont["propuesta_valor"],
        "decisiones_gerencia": "\n".join(cont["decisiones_gerencia"]),
        "speech": cont["capacitacion"]["speech"],
        "objeciones": cont["capacitacion"]["objeciones"],
        "canales": "\n".join(cont["marketing"]["canales"]),
        "gancho": cont["marketing"]["gancho"],
        "mensaje_whatsapp": cont["marketing"]["mensaje_whatsapp"],
        "fecha_inicio": c.entradas["fecha_inicio"],
        "duracion_semanas": str(c.entradas["duracion_semanas"]),
    }


def _leer_edicion(form) -> tuple[dict, dict]:
    """Formulario de edición → (valores para volver a mostrar, contenido)."""
    lineas = lambda campo: [x.strip() for x in form.get(campo, "").splitlines() if x.strip()]  # noqa: E731
    objeciones = [
        {"objecion": form.get(f"objecion_{i}", "").strip(), "respuesta": form.get(f"respuesta_{i}", "").strip()}
        for i in range(MAX_OBJECIONES)
    ]
    objeciones = [o for o in objeciones if o["objecion"] or o["respuesta"]]
    valores = dict(form) | {"objeciones": objeciones}
    contenido = {
        "nombre": form.get("nombre", ""),
        "propuesta_valor": form.get("propuesta_valor", ""),
        "decisiones_gerencia": lineas("decisiones_gerencia"),
        "capacitacion": {"speech": form.get("speech", ""), "objeciones": objeciones},
        "marketing": {"canales": lineas("canales"), "gancho": form.get("gancho", ""),
                      "mensaje_whatsapp": form.get("mensaje_whatsapp", "")},
    }
    return valores, contenido


def _formulario_edicion(request, usuario, c, v, errores, status_code=200):
    return templates.TemplateResponse(
        request, "campana_editar.html",
        {"usuario": usuario, "c": c, "v": v, "errores": errores, "max_objeciones": MAX_OBJECIONES},
        status_code=status_code,
    )


@router.get("/campanas/{campana_id}/editar")
def editar_form(
    campana_id: int, request: Request, usuario: Usuario = Depends(requiere_rol("gerente")), db: Session = Depends(get_db)
):
    campana = _obtener(db, campana_id)
    _solo_borrador(campana)
    return _formulario_edicion(request, usuario, campana, _valores_edicion(campana), {})


@router.post("/campanas/{campana_id}/editar")
async def editar(
    campana_id: int, request: Request, usuario: Usuario = Depends(requiere_rol("gerente")), db: Session = Depends(get_db)
):
    campana = _obtener(db, campana_id)
    _solo_borrador(campana)
    valores, contenido = _leer_edicion(await request.form())
    errores = {}
    try:
        contenido = CampanaContenido(**contenido).model_dump()
    except ValidationError as e:
        errores |= errores_es(e, anidado=True)
    try:
        # La vigencia se valida con las mismas reglas que al crear
        entrada = CampanaEntrada(**(campana.entradas | {
            "fecha_inicio": valores.get("fecha_inicio"), "duracion_semanas": valores.get("duracion_semanas")}))
    except ValidationError as e:
        errores |= errores_es(e)
    if errores:
        return _formulario_edicion(request, usuario, campana, valores, errores, status.HTTP_422_UNPROCESSABLE_ENTITY)
    campana.contenido = contenido
    campana.nombre = contenido["nombre"]
    servicio.aplicar_entrada(campana, entrada)
    db.commit()
    avisar(request, "Cambios guardados")
    return _volver(campana.id)


@router.post("/campanas/{campana_id}/regenerar")
def regenerar(
    campana_id: int, request: Request, usuario: Usuario = Depends(requiere_rol("gerente")), db: Session = Depends(get_db)
):
    campana = _obtener(db, campana_id)
    _solo_borrador(campana)
    entrada = CampanaEntrada(**campana.entradas)
    contenido, generado_con, error = servicio.generar_contenido(
        entrada, servicio.contexto_bloque(db, entrada.bloque_id, _estacion(db))
    )
    campana.contenido, campana.nombre, campana.generado_con = contenido, contenido["nombre"], generado_con
    db.commit()
    avisar(request, f"Plantilla automática: Gemini no respondió ({error})" if error else f"Campaña regenerada con {generado_con}")
    return _volver(campana.id)


@router.post("/campanas/{campana_id}/publicar")
def publicar(
    campana_id: int, request: Request, usuario: Usuario = Depends(requiere_rol("gerente")), db: Session = Depends(get_db)
):
    campana = _obtener(db, campana_id)
    error = servicio.publicar(campana, usuario.id)
    if error:
        avisar(request, error)
    else:
        db.commit()
        avisar(request, f"Campaña publicada: estará vigente del {campana.vigente_desde:%d/%m/%Y} al {campana.vigente_hasta:%d/%m/%Y}")
    return _volver(campana.id)


@router.post("/campanas/{campana_id}/retirar")
def retirar(
    campana_id: int, request: Request, usuario: Usuario = Depends(requiere_rol("gerente")), db: Session = Depends(get_db)
):
    campana = _obtener(db, campana_id)
    if campana.estado != "publicada":
        raise HTTPException(status.HTTP_409_CONFLICT, "Solo se retiran campañas publicadas")
    campana.estado = "retirada"
    db.commit()
    avisar(request, "Campaña retirada: el chatbot ya no la ofrecerá")
    return _volver(campana.id)


@router.post("/campanas/{campana_id}/eliminar")
def eliminar(
    campana_id: int, request: Request, usuario: Usuario = Depends(requiere_rol("gerente")), db: Session = Depends(get_db)
):
    campana = _obtener(db, campana_id)
    _solo_borrador(campana)
    db.delete(campana)
    db.commit()
    avisar(request, "Borrador eliminado")
    return RedirectResponse("/campanas", status.HTTP_303_SEE_OTHER)


# ---------- API ----------

@router.get("/api/campanas/vigentes")
def api_vigentes(usuario: Usuario = Depends(usuario_web_o_api), db: Session = Depends(get_db)):
    return [servicio.campana_a_dict(c) for c in servicio.vigentes(db)]
