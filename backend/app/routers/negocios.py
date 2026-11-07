"""Negocios: expediente del cliente, solicitud digital, documentos, simulador y catálogo de productos."""
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Campana, Cliente, Credito, DocumentoSolicitud, MovimientoSolicitud, Prospecto, Solicitud, Usuario
from app.schemas import ClienteEntrada, SimulacionEntrada, SolicitudEntrada, errores_es
from app.security import requiere_rol, usuario_web, usuario_web_o_api
from app.services import negocios, riesgos
from app.services.auditoria import registrar
from app.services.simulador import FRECUENCIAS, simular
from app.templating import avisar, templates

router = APIRouter()
roles_negocios = requiere_rol("asesor", "gerente", "analista_riesgos")
roles_registro = requiere_rol("asesor", "gerente")

DOC_ESTADOS = {"pendiente": "Pendiente", "recibido": "Recibido", "validado": "Validado", "observado": "Observado"}

# Estado de la solicitud → estado del prospecto que la originó (embudo comercial)
SOLICITUD_A_PROSPECTO = {"borrador": "solicitud", "enviada": "evaluacion", "en_evaluacion": "evaluacion", "observada": "evaluacion",
                         "evaluada": "evaluacion", "aprobada": "convertido", "denegada": "no_convertido", "desistida": "no_convertido"}


# ---------- Utilidades ----------

def _cliente(db: Session, usuario: Usuario, cliente_id: int) -> Cliente:
    c = db.get(Cliente, cliente_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expediente no encontrado")
    if not negocios.puede_ver_cliente(usuario, c):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes acceso a este expediente")
    return c


def _solicitud(db: Session, usuario: Usuario, solicitud_id: int) -> Solicitud:
    s = db.get(Solicitud, solicitud_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada")
    if not negocios.puede_ver_solicitud(usuario, s):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes acceso a esta solicitud")
    return s


def _sincronizar_prospecto(db: Session, s: Solicitud) -> None:
    if s.cliente.prospecto_id:
        p = db.get(Prospecto, s.cliente.prospecto_id)
        if p and s.estado in SOLICITUD_A_PROSPECTO:
            p.estado = SOLICITUD_A_PROSPECTO[s.estado]


def _mover(db: Session, s: Solicitud, usuario: Usuario, nuevo: str, comentario: str | None = None) -> None:
    db.add(MovimientoSolicitud(solicitud_id=s.id, usuario_id=usuario.id, estado_anterior=s.estado, estado_nuevo=nuevo,
                               comentario=comentario))
    s.estado = nuevo
    _sincronizar_prospecto(db, s)


def _leer_cliente(form) -> dict:
    datos = dict(form)
    datos["consentimiento"] = "consentimiento" in form
    return datos


# ---------- Expedientes ----------

def _clientes_visibles(db: Session, usuario: Usuario):
    consulta = select(Cliente).order_by(Cliente.id.desc())
    if usuario.rol == "asesor":
        consulta = consulta.where(Cliente.asesor_id == usuario.id)
    elif usuario.rol == "analista_riesgos":
        consulta = consulta.where(Cliente.id.in_(select(Solicitud.cliente_id).where(Solicitud.estado != "borrador")))
    return db.scalars(consulta).all()


@router.get("/clientes")
def clientes(request: Request, usuario: Usuario = Depends(roles_negocios), db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "clientes.html", {"usuario": usuario, "clientes": _clientes_visibles(db, usuario)})


def _form_cliente(request, usuario, v, errores, cliente=None, status_code=200):
    return templates.TemplateResponse(
        request, "cliente_form.html", {"usuario": usuario, "v": v, "errores": errores, "cliente": cliente},
        status_code=status_code,
    )


@router.get("/clientes/nuevo")
def cliente_nuevo(
    request: Request, prospecto_id: int | None = None, usuario: Usuario = Depends(roles_registro), db: Session = Depends(get_db)
):
    v = {}
    if prospecto_id:
        p = db.get(Prospecto, prospecto_id)
        if p:
            v = {"nombres": p.nombre, "telefono": p.telefono, "dni": p.dni or "", "segmento": p.segmento,
                 "ocupacion": p.actividad, "region": p.region, "ubicacion": p.ubicacion or "", "necesidades": p.necesidad,
                 "consentimiento": p.consentimiento, "prospecto_id": str(p.id)}
    return _form_cliente(request, usuario, v, {})


@router.post("/clientes/nuevo")
async def cliente_crear(request: Request, usuario: Usuario = Depends(roles_registro), db: Session = Depends(get_db)):
    datos = _leer_cliente(await request.form())
    try:
        entrada = ClienteEntrada(**datos)
    except ValidationError as e:
        return _form_cliente(request, usuario, datos, errores_es(e), status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    if db.scalar(select(Cliente).where(Cliente.dni == entrada.dni)):
        return _form_cliente(request, usuario, datos, {"dni": "Ya existe un expediente con ese DNI"},
                             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    prospecto_id = str(datos.get("prospecto_id", ""))
    c = Cliente(**entrada.model_dump(), asesor_id=usuario.id, creado_por=usuario.id,
                prospecto_id=int(prospecto_id) if prospecto_id.isdigit() and db.get(Prospecto, int(prospecto_id)) else None)
    db.add(c)
    db.flush()
    registrar(db, "cliente_creado", usuario, f"cliente {c.id}")
    db.commit()
    avisar(request, "Expediente creado. Ahora puedes iniciar una solicitud.")
    return RedirectResponse(f"/clientes/{c.id}", status.HTTP_303_SEE_OTHER)


@router.get("/clientes/{cliente_id}")
def cliente_detalle(cliente_id: int, request: Request, usuario: Usuario = Depends(roles_negocios), db: Session = Depends(get_db)):
    c = _cliente(db, usuario, cliente_id)
    creditos = db.scalars(select(Credito).where(Credito.cliente_id == c.id).order_by(Credito.id.desc())).all()
    ingreso_neto = Decimal(c.ingresos_mensuales) - Decimal(c.gastos_mensuales)
    return templates.TemplateResponse(
        request, "cliente_detalle.html",
        {"usuario": usuario, "c": c, "creditos": creditos, "ingreso_neto": ingreso_neto,
         "capacidad": ingreso_neto - Decimal(c.cuotas_otras_deudas or 0),
         "editable": negocios.puede_editar_cliente(usuario, c), "productos": negocios.productos(),
         "estados": negocios.ESTADOS_TEXTO, "colores": negocios.ESTADOS_COLOR},
    )


@router.get("/clientes/{cliente_id}/editar")
def cliente_editar_form(cliente_id: int, request: Request, usuario: Usuario = Depends(roles_registro), db: Session = Depends(get_db)):
    c = _cliente(db, usuario, cliente_id)
    if not negocios.puede_editar_cliente(usuario, c):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el asesor responsable o el gerente editan el expediente")
    v = {k: ("" if getattr(c, k) is None else str(getattr(c, k))) for k in ClienteEntrada.model_fields}
    v["consentimiento"] = c.consentimiento
    return _form_cliente(request, usuario, v, {}, c)


@router.post("/clientes/{cliente_id}/editar")
async def cliente_editar(cliente_id: int, request: Request, usuario: Usuario = Depends(roles_registro), db: Session = Depends(get_db)):
    c = _cliente(db, usuario, cliente_id)
    if not negocios.puede_editar_cliente(usuario, c):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el asesor responsable o el gerente editan el expediente")
    datos = _leer_cliente(await request.form())
    try:
        entrada = ClienteEntrada(**datos)
    except ValidationError as e:
        return _form_cliente(request, usuario, datos, errores_es(e), c, status.HTTP_422_UNPROCESSABLE_ENTITY)
    otro = db.scalar(select(Cliente).where(Cliente.dni == entrada.dni, Cliente.id != c.id))
    if otro:
        return _form_cliente(request, usuario, datos, {"dni": "Ya existe otro expediente con ese DNI"}, c,
                             status.HTTP_422_UNPROCESSABLE_ENTITY)
    for campo, valor in entrada.model_dump().items():
        setattr(c, campo, valor)
    registrar(db, "cliente_editado", usuario, f"cliente {c.id}")
    db.commit()
    avisar(request, "Expediente actualizado")
    return RedirectResponse(f"/clientes/{c.id}", status.HTTP_303_SEE_OTHER)


# ---------- Solicitudes ----------

def _campanas_vigentes(db: Session) -> list[Campana]:
    from app.services.campanas import vigentes
    return vigentes(db)


def _form_solicitud(request, usuario, db, c: Cliente, v, errores, s=None, status_code=200):
    return templates.TemplateResponse(
        request, "solicitud_form.html",
        {"usuario": usuario, "c": c, "s": s, "v": v, "errores": errores,
         "productos": negocios.productos_para(c.segmento), "frecuencias": {k: f["nombre"] for k, f in FRECUENCIAS.items()},
         "campos_perfil": negocios.CAMPOS_PERFIL.get(c.segmento, []), "campanas": _campanas_vigentes(db),
         "aviso_demo": negocios.catalogo()["aviso"]},
        status_code=status_code,
    )


def _validar_solicitud(c: Cliente, form: dict):
    errores = {}
    entrada = None
    try:
        entrada = SolicitudEntrada(**{k: form.get(k) for k in SolicitudEntrada.model_fields if k in form})
    except ValidationError as e:
        errores |= errores_es(e)
    perfil, errores_perfil = negocios.validar_perfil(c.segmento, form)
    errores |= errores_perfil
    if entrada:
        errores |= negocios.validar_condiciones(entrada.producto, c.segmento, entrada.monto, entrada.plazo_meses, entrada.frecuencia)
    return entrada, perfil, errores


@router.get("/clientes/{cliente_id}/solicitud/nueva")
def solicitud_nueva(cliente_id: int, request: Request, usuario: Usuario = Depends(roles_registro), db: Session = Depends(get_db)):
    c = _cliente(db, usuario, cliente_id)
    if not negocios.puede_editar_cliente(usuario, c):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el asesor responsable o el gerente inician solicitudes")
    return _form_solicitud(request, usuario, db, c, {"frecuencia": "mensual"}, {})


@router.post("/clientes/{cliente_id}/solicitud/nueva")
async def solicitud_crear(cliente_id: int, request: Request, usuario: Usuario = Depends(roles_registro), db: Session = Depends(get_db)):
    c = _cliente(db, usuario, cliente_id)
    if not negocios.puede_editar_cliente(usuario, c):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el asesor responsable o el gerente inician solicitudes")
    form = dict(await request.form())
    entrada, perfil, errores = _validar_solicitud(c, form)
    if errores:
        return _form_solicitud(request, usuario, db, c, form, errores, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    s = Solicitud(cliente_id=c.id, asesor_id=c.asesor_id, datos_perfil=perfil, estado="borrador", **entrada.model_dump())
    s.documentos = [DocumentoSolicitud(tipo=t, estado="pendiente") for t in negocios.documentos_requeridos(c.segmento)]
    db.add(s)
    db.flush()
    db.add(MovimientoSolicitud(solicitud_id=s.id, usuario_id=usuario.id, estado_anterior=None, estado_nuevo="borrador",
                               comentario="Solicitud creada"))
    _sincronizar_prospecto(db, s)
    registrar(db, "solicitud_creada", usuario, f"solicitud {s.id} · cliente {c.id}")
    db.commit()
    avisar(request, "Solicitud guardada como borrador. Completa los documentos y envíala a evaluación.")
    return RedirectResponse(f"/solicitudes/{s.id}", status.HTTP_303_SEE_OTHER)


@router.get("/solicitudes")
def solicitudes(request: Request, estado: str = "", usuario: Usuario = Depends(roles_negocios), db: Session = Depends(get_db)):
    consulta = select(Solicitud).order_by(Solicitud.id.desc())
    if usuario.rol == "asesor":
        consulta = consulta.where(Solicitud.asesor_id == usuario.id)
    elif usuario.rol == "analista_riesgos":
        consulta = consulta.where(Solicitud.estado != "borrador")
    if estado:
        consulta = consulta.where(Solicitud.estado == estado)
    filas = db.scalars(consulta).all()
    return templates.TemplateResponse(
        request, "solicitudes.html",
        {"usuario": usuario, "solicitudes": filas, "estado": estado, "estados": negocios.ESTADOS_TEXTO,
         "colores": negocios.ESTADOS_COLOR, "productos": negocios.productos(), "ultima": riesgos.ultima_evaluacion},
    )


@router.get("/solicitudes/{solicitud_id}")
def solicitud_detalle(solicitud_id: int, request: Request, usuario: Usuario = Depends(roles_negocios), db: Session = Depends(get_db)):
    s = _solicitud(db, usuario, solicitud_id)
    producto = negocios.productos().get(s.producto, {})
    simulacion = None
    if producto:
        try:
            simulacion = simular(s.monto, float(producto["tea_demo"]), s.plazo_meses, s.frecuencia)
        except ValueError:
            simulacion = None
    cat = negocios.catalogo()
    return templates.TemplateResponse(
        request, "solicitud_detalle.html",
        {"usuario": usuario, "s": s, "c": s.cliente, "producto": producto, "simulacion": simulacion,
         "estados": negocios.ESTADOS_TEXTO, "colores": negocios.ESTADOS_COLOR, "acciones": negocios.acciones_permitidas(usuario, s),
         "acciones_texto": negocios.ACCIONES_TEXTO, "requiere_comentario": {k: a[4] for k, a in negocios.ACCIONES.items()},
         "editable": negocios.editable(usuario, s), "documentos_nombres": cat["documentos"], "doc_estados": DOC_ESTADOS,
         "campos_perfil": negocios.CAMPOS_PERFIL.get(s.cliente.segmento, []), "evaluacion": riesgos.ultima_evaluacion(s),
         "aviso_demo": cat["aviso"], "frecuencias": FRECUENCIAS, "puede_documentos": _puede_documentos(usuario, s)},
    )


def _puede_documentos(usuario: Usuario, s: Solicitud) -> bool:
    if s.estado in ("aprobada", "denegada", "desistida"):
        return False
    return usuario.rol in ("gerente", "analista_riesgos") or (usuario.rol == "asesor" and s.asesor_id == usuario.id)


@router.get("/solicitudes/{solicitud_id}/editar")
def solicitud_editar_form(solicitud_id: int, request: Request, usuario: Usuario = Depends(roles_registro), db: Session = Depends(get_db)):
    s = _solicitud(db, usuario, solicitud_id)
    if not negocios.editable(usuario, s):
        raise HTTPException(status.HTTP_409_CONFLICT, "Solo se editan solicitudes en borrador u observadas")
    v = {"producto": s.producto, "monto": str(s.monto), "plazo_meses": str(s.plazo_meses), "frecuencia": s.frecuencia,
         "destino": s.destino, "campana_id": str(s.campana_id or "")}
    v |= {f"perfil_{k}": (str(int(x)) if isinstance(x, float) and x.is_integer() else str(x)) for k, x in (s.datos_perfil or {}).items()}
    return _form_solicitud(request, usuario, db, s.cliente, v, {}, s)


@router.post("/solicitudes/{solicitud_id}/editar")
async def solicitud_editar(solicitud_id: int, request: Request, usuario: Usuario = Depends(roles_registro), db: Session = Depends(get_db)):
    s = _solicitud(db, usuario, solicitud_id)
    if not negocios.editable(usuario, s):
        raise HTTPException(status.HTTP_409_CONFLICT, "Solo se editan solicitudes en borrador u observadas")
    form = dict(await request.form())
    entrada, perfil, errores = _validar_solicitud(s.cliente, form)
    if errores:
        return _form_solicitud(request, usuario, db, s.cliente, form, errores, s, status.HTTP_422_UNPROCESSABLE_ENTITY)
    for campo, valor in entrada.model_dump().items():
        setattr(s, campo, valor)
    s.datos_perfil = perfil
    registrar(db, "solicitud_editada", usuario, f"solicitud {s.id}")
    db.commit()
    avisar(request, "Solicitud actualizada")
    return RedirectResponse(f"/solicitudes/{s.id}", status.HTTP_303_SEE_OTHER)


@router.post("/solicitudes/{solicitud_id}/accion")
async def solicitud_accion(solicitud_id: int, request: Request, usuario: Usuario = Depends(roles_negocios), db: Session = Depends(get_db)):
    s = _solicitud(db, usuario, solicitud_id)
    form = await request.form()
    accion = str(form.get("accion", ""))
    comentario = str(form.get("comentario", "")).strip()[:2000] or None
    if accion not in negocios.acciones_permitidas(usuario, s):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes realizar esta acción en el estado actual")
    _, nuevo, _, _, requiere = negocios.ACCIONES[accion]
    if requiere and not comentario:
        avisar(request, "Escribe un comentario para registrar esta acción")
        return RedirectResponse(f"/solicitudes/{s.id}#acciones", status.HTTP_303_SEE_OTHER)
    if accion in ("enviar", "evaluar"):
        # Se guarda una foto de la evaluación preliminar: así queda trazado con qué datos se decidió
        ev = riesgos.guardar_evaluacion(db, s, usuario.id)
        if accion == "evaluar":
            ev.opinion, ev.opinion_por = comentario, usuario.id
            registrar(db, "riesgo_opinion", usuario, f"solicitud {s.id} · {ev.semaforo}")
    _mover(db, s, usuario, nuevo, comentario)
    registrar(db, "solicitud_estado", usuario, f"solicitud {s.id} → {nuevo}")
    db.commit()
    avisar(request, f"Solicitud: {negocios.ESTADOS_TEXTO[nuevo]}")
    return RedirectResponse(f"/solicitudes/{s.id}", status.HTTP_303_SEE_OTHER)


@router.post("/solicitudes/{solicitud_id}/evaluar")
def solicitud_evaluar(solicitud_id: int, request: Request, usuario: Usuario = Depends(roles_negocios), db: Session = Depends(get_db)):
    """Recalcula la evaluación preliminar (no cambia el estado ni decide nada)."""
    s = _solicitud(db, usuario, solicitud_id)
    if usuario.rol == "asesor" and s.asesor_id != usuario.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes acceso a esta solicitud")
    ev = riesgos.guardar_evaluacion(db, s, usuario.id)
    registrar(db, "riesgo_evaluado", usuario, f"solicitud {s.id} · {ev.semaforo}")
    db.commit()
    avisar(request, "Evaluación preliminar actualizada")
    return RedirectResponse(f"/solicitudes/{s.id}#riesgos", status.HTTP_303_SEE_OTHER)


@router.post("/solicitudes/{solicitud_id}/documentos/{documento_id}")
async def documento_estado(
    solicitud_id: int, documento_id: int, request: Request, usuario: Usuario = Depends(roles_negocios), db: Session = Depends(get_db)
):
    s = _solicitud(db, usuario, solicitud_id)
    if not _puede_documentos(usuario, s):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No puedes revisar documentos de esta solicitud")
    d = db.get(DocumentoSolicitud, documento_id)
    if not d or d.solicitud_id != s.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Documento no encontrado")
    form = await request.form()
    estado = str(form.get("estado", ""))
    if estado not in DOC_ESTADOS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Estado de documento inválido")
    observacion = str(form.get("observacion", "")).strip()[:500] or None
    if estado == "observado" and not observacion:
        avisar(request, "Indica qué falta o qué está mal en el documento observado")
        return RedirectResponse(f"/solicitudes/{s.id}#documentos", status.HTTP_303_SEE_OTHER)
    d.estado, d.observacion = estado, observacion
    d.revisado_por, d.revisado_en = usuario.id, datetime.now(timezone.utc)
    registrar(db, "documento_estado", usuario, f"solicitud {s.id} · {d.tipo} → {estado}")
    db.commit()
    return RedirectResponse(f"/solicitudes/{s.id}#documentos", status.HTTP_303_SEE_OTHER)


# ---------- Simulador y productos ----------

@router.get("/simulador")
def simulador(
    request: Request,
    monto: str = "",
    tea: str = "",
    plazo_meses: str = "",
    frecuencia: str = "mensual",
    producto: str = "",
    usuario: Usuario = Depends(usuario_web),
):
    cat = negocios.catalogo()
    v = {"monto": monto, "tea": tea, "plazo_meses": plazo_meses, "frecuencia": frecuencia, "producto": producto}
    resultado, errores = None, {}
    if producto and not tea and producto in cat["productos"]:
        v["tea"] = tea = str(cat["productos"][producto]["tea_demo"])
    if monto or plazo_meses:
        try:
            e = SimulacionEntrada(monto=monto, tea=tea or "0", plazo_meses=plazo_meses, frecuencia=frecuencia)
            resultado = simular(e.monto, e.tea, e.plazo_meses, e.frecuencia)
        except ValidationError as ex:
            errores = errores_es(ex)
        except ValueError as ex:
            errores = {"monto": str(ex)}
    return templates.TemplateResponse(
        request, "simulador.html",
        {"usuario": usuario, "v": v, "r": resultado, "errores": errores, "productos": cat["productos"],
         "frecuencias": {k: f["nombre"] for k, f in FRECUENCIAS.items()}, "aviso_demo": cat["aviso"]},
    )


@router.get("/api/simulador")
def api_simulador(monto: str, tea: str, plazo_meses: str, frecuencia: str = "mensual", usuario: Usuario = Depends(usuario_web_o_api)):
    try:
        e = SimulacionEntrada(monto=monto, tea=tea, plazo_meses=plazo_meses, frecuencia=frecuencia)
    except ValidationError as ex:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, errores_es(ex))
    r = simular(e.monto, e.tea, e.plazo_meses, e.frecuencia)
    return {
        "aviso": "Cálculo referencial con método francés; no incluye comisiones ni seguros y no es una cotización.",
        **{k: (str(v) if isinstance(v, Decimal) else v) for k, v in r.items() if k != "cronograma"},
        "cronograma": [{k: (str(x) if isinstance(x, Decimal) else x.isoformat() if hasattr(x, "isoformat") else x)
                        for k, x in c.items()} for c in r["cronograma"]],
    }


@router.get("/productos")
def productos(request: Request, usuario: Usuario = Depends(usuario_web)):
    cat = negocios.catalogo()
    return templates.TemplateResponse(
        request, "productos.html",
        {"usuario": usuario, "productos": cat["productos"], "aviso_demo": cat["aviso"], "documentos": cat["documentos"],
         "frecuencias": {k: f["nombre"] for k, f in FRECUENCIAS.items()}},
    )
