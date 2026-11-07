"""Comercial: prospectos (captación), embudo, contactos, asignación y mensajes con IA."""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalogos import CANALES
from app.db import get_db
from app.models import Campana, ContactoProspecto, Interesado, Prospecto, Usuario
from app.schemas import ContactoEntrada, ProspectoEntrada, errores_es
from app.security import requiere_rol
from app.services import comercial
from app.services.auditoria import registrar
from app.services.campanas import estado_visible
from app.templating import avisar, templates

router = APIRouter()
comercial_roles = requiere_rol("asesor", "gerente")

# Oficio del chatbot → segmento de ACTIVA 360°
OFICIO_A_SEGMENTO = {"agricola": "agricultor", "comerciante": "comerciante", "ambulante": "comerciante", "taxista": "transportista"}


def _obtener(db: Session, usuario: Usuario, prospecto_id: int) -> Prospecto:
    p = db.get(Prospecto, prospecto_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prospecto no encontrado")
    if not comercial.puede_ver(usuario, p):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Este prospecto está asignado a otro asesor")
    return p


def _campanas_activas(db: Session) -> list[Campana]:
    return [c for c in db.scalars(select(Campana).where(Campana.estado == "publicada").order_by(Campana.id.desc())).all()
            if estado_visible(c) in ("vigente", "programada")]


def _asesores(db: Session) -> list[Usuario]:
    return db.scalars(select(Usuario).where(Usuario.rol.in_(("asesor", "gerente")), Usuario.activo.is_(True)).order_by(Usuario.nombre)).all()


def _formulario(request, usuario, db, v, errores, prospecto=None, status_code=200):
    return templates.TemplateResponse(
        request, "prospecto_form.html",
        {"usuario": usuario, "v": v, "errores": errores, "p": prospecto, "canales": CANALES,
         "campanas": _campanas_activas(db), "asesores": _asesores(db)},
        status_code=status_code,
    )


def _leer(form) -> dict:
    datos = dict(form)
    datos["consentimiento"] = "consentimiento" in form
    return datos


@router.get("/prospectos")
def listar(
    request: Request,
    estado: str = "",
    segmento: str = "",
    region: str = "",
    usuario: Usuario = Depends(comercial_roles),
    db: Session = Depends(get_db),
):
    consulta = comercial.visibles(usuario).order_by(Prospecto.id.desc())
    if estado:
        consulta = consulta.where(Prospecto.estado == estado)
    if segmento:
        consulta = consulta.where(Prospecto.segmento == segmento)
    if region:
        consulta = consulta.where(Prospecto.region == region)
    return templates.TemplateResponse(
        request, "prospectos.html",
        {"usuario": usuario, "prospectos": db.scalars(consulta).all(), "embudo": comercial.embudo(db, usuario),
         "estados": comercial.ESTADOS_TEXTO, "colores": comercial.ESTADOS_COLOR,
         "f": {"estado": estado, "segmento": segmento, "region": region}},
    )


@router.get("/prospectos/nuevo")
def nuevo(request: Request, usuario: Usuario = Depends(comercial_roles), db: Session = Depends(get_db)):
    return _formulario(request, usuario, db, {"asesor_id": str(usuario.id) if usuario.rol == "asesor" else ""}, {})


@router.post("/prospectos/nuevo")
async def crear(request: Request, usuario: Usuario = Depends(comercial_roles), db: Session = Depends(get_db)):
    datos = _leer(await request.form())
    try:
        entrada = ProspectoEntrada(**datos)
    except ValidationError as e:
        return _formulario(request, usuario, db, datos, errores_es(e), status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    valores = entrada.model_dump()
    if usuario.rol == "asesor":
        valores["asesor_id"] = usuario.id  # el asesor solo registra para sí mismo
    p = Prospecto(**valores, creado_por=usuario.id, estado="nuevo", origen="manual")
    db.add(p)
    db.flush()
    registrar(db, "prospecto_creado", usuario, f"prospecto {p.id}")
    db.commit()
    avisar(request, f"Prospecto {p.nombre} registrado")
    return RedirectResponse(f"/prospectos/{p.id}", status.HTTP_303_SEE_OTHER)


@router.get("/prospectos/{prospecto_id}")
def detalle(prospecto_id: int, request: Request, usuario: Usuario = Depends(comercial_roles), db: Session = Depends(get_db)):
    p = _obtener(db, usuario, prospecto_id)
    mensaje = request.session.pop("mensaje_ia", None)
    if mensaje and mensaje.get("prospecto_id") != p.id:
        mensaje = None
    return templates.TemplateResponse(
        request, "prospecto_detalle.html",
        {"usuario": usuario, "p": p, "estados": comercial.ESTADOS_TEXTO, "colores": comercial.ESTADOS_COLOR,
         "canales": CANALES, "asesores": _asesores(db), "mensaje": mensaje, "v": {}, "errores": {}},
    )


@router.get("/prospectos/{prospecto_id}/editar")
def editar_form(prospecto_id: int, request: Request, usuario: Usuario = Depends(comercial_roles), db: Session = Depends(get_db)):
    p = _obtener(db, usuario, prospecto_id)
    v = {c: ("" if getattr(p, c) is None else str(getattr(p, c))) for c in ProspectoEntrada.model_fields if c != "consentimiento"}
    v["consentimiento"] = p.consentimiento
    return _formulario(request, usuario, db, v, {}, p)


@router.post("/prospectos/{prospecto_id}/editar")
async def editar(prospecto_id: int, request: Request, usuario: Usuario = Depends(comercial_roles), db: Session = Depends(get_db)):
    p = _obtener(db, usuario, prospecto_id)
    datos = _leer(await request.form())
    try:
        entrada = ProspectoEntrada(**datos)
    except ValidationError as e:
        return _formulario(request, usuario, db, datos, errores_es(e), p, status.HTTP_422_UNPROCESSABLE_ENTITY)
    valores = entrada.model_dump()
    if usuario.rol == "asesor":
        valores["asesor_id"] = p.asesor_id or usuario.id  # solo el gerente reasigna
    for campo, valor in valores.items():
        setattr(p, campo, valor)
    registrar(db, "prospecto_editado", usuario, f"prospecto {p.id}")
    db.commit()
    avisar(request, "Prospecto actualizado")
    return RedirectResponse(f"/prospectos/{p.id}", status.HTTP_303_SEE_OTHER)


@router.post("/prospectos/{prospecto_id}/contacto")
async def registrar_contacto(prospecto_id: int, request: Request, usuario: Usuario = Depends(comercial_roles), db: Session = Depends(get_db)):
    p = _obtener(db, usuario, prospecto_id)
    datos = dict(await request.form())
    try:
        entrada = ContactoEntrada(**datos)
    except ValidationError as e:
        return templates.TemplateResponse(
            request, "prospecto_detalle.html",
            {"usuario": usuario, "p": p, "estados": comercial.ESTADOS_TEXTO, "colores": comercial.ESTADOS_COLOR,
             "canales": CANALES, "asesores": _asesores(db), "mensaje": None, "v": datos, "errores": errores_es(e)},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    db.add(ContactoProspecto(prospecto_id=p.id, usuario_id=usuario.id, **entrada.model_dump()))
    p.estado = entrada.estado_nuevo
    p.proxima_accion = entrada.proxima_accion
    if p.asesor_id is None and usuario.rol == "asesor":
        p.asesor_id = usuario.id  # quien atiende un prospecto libre se lo queda
    registrar(db, "prospecto_contacto", usuario, f"prospecto {p.id} · {entrada.estado_nuevo}")
    db.commit()
    avisar(request, f"Contacto registrado. Estado: {comercial.ESTADOS_TEXTO[p.estado]}")
    return RedirectResponse(f"/prospectos/{p.id}", status.HTTP_303_SEE_OTHER)


@router.post("/prospectos/{prospecto_id}/asignar")
async def asignar(prospecto_id: int, request: Request, usuario: Usuario = Depends(requiere_rol("gerente")), db: Session = Depends(get_db)):
    p = _obtener(db, usuario, prospecto_id)
    form = await request.form()
    asesor_id = str(form.get("asesor_id", ""))
    asesor = db.get(Usuario, int(asesor_id)) if asesor_id.isdigit() else None
    if not asesor or asesor.rol not in ("asesor", "gerente") or not asesor.activo:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Elige un asesor activo")
    p.asesor_id = asesor.id
    registrar(db, "prospecto_asignado", usuario, f"prospecto {p.id} → usuario {asesor.id}")
    db.commit()
    avisar(request, f"Prospecto asignado a {asesor.nombre}")
    return RedirectResponse(f"/prospectos/{p.id}", status.HTTP_303_SEE_OTHER)


@router.post("/prospectos/{prospecto_id}/mensaje")
def mensaje_ia(prospecto_id: int, request: Request, usuario: Usuario = Depends(comercial_roles), db: Session = Depends(get_db)):
    """Sugiere un mensaje de WhatsApp. A Gemini solo van datos anonimizados (sin nombre, teléfono ni DNI)."""
    p = _obtener(db, usuario, prospecto_id)
    r = comercial.mensaje_comercial(p)
    request.session["mensaje_ia"] = {"prospecto_id": p.id, **r}
    return RedirectResponse(f"/prospectos/{p.id}#mensaje", status.HTTP_303_SEE_OTHER)


@router.post("/interesados/{interesado_id}/prospecto")
def desde_interesado(interesado_id: int, request: Request, usuario: Usuario = Depends(comercial_roles), db: Session = Depends(get_db)):
    """Convierte un interesado del chatbot en prospecto del embudo comercial."""
    i = db.get(Interesado, interesado_id)
    if not i:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interesado no encontrado")
    existente = db.scalar(select(Prospecto).where(Prospecto.interesado_id == i.id))
    if existente:
        return RedirectResponse(f"/prospectos/{existente.id}", status.HTTP_303_SEE_OTHER)
    if not i.consentimiento:
        raise HTTPException(status.HTTP_409_CONFLICT, "El interesado no dio su consentimiento (Ley 29733)")
    from app.config import cargar_yaml

    oficios = cargar_yaml("chatbot")["oficios"]
    actividad = oficios.get(i.sector, {}).get("nombre", "Por confirmar") if i.sector else "Por confirmar"
    p = Prospecto(
        nombre=i.nombre, telefono=i.telefono, segmento=OFICIO_A_SEGMENTO.get(i.sector, "persona_natural"),
        actividad=actividad[:120],
        necesidad=f"Interés en la campaña «{i.campana.nombre}» (captado por el chatbot)" if i.campana else "Captado por el chatbot",
        region=cargar_yaml("institucion").get("region_por_defecto", "huanuco"), contacto_preferido="whatsapp",
        consentimiento=True, estado="interesado", origen="chatbot", campana_id=i.campana_id, interesado_id=i.id,
        asesor_id=usuario.id if usuario.rol == "asesor" else None, creado_por=usuario.id,
    )
    db.add(p)
    db.flush()
    registrar(db, "prospecto_creado", usuario, f"prospecto {p.id} · desde interesado {i.id}")
    db.commit()
    avisar(request, "Interesado agregado al embudo comercial como prospecto")
    return RedirectResponse(f"/prospectos/{p.id}", status.HTTP_303_SEE_OTHER)
