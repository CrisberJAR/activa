"""Recuperaciones: cartera de seguimiento, pagos registrados, gestiones, compromisos y reprogramaciones.

La plataforma NO realiza desembolsos ni cobros: solo registra lo que la entidad informa.
"""
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalogos import CANALES
from app.config import hoy_peru
from app.db import get_db
from app.models import (Cliente, CompromisoPago, Credito, GestionCobranza, Pago, Reprogramacion, Solicitud, Usuario)
from app.schemas import CreditoEntrada, errores_es
from app.security import requiere_rol
from app.services import negocios
from app.services import recuperaciones as rec
from app.services.auditoria import registrar
from app.services.simulador import FRECUENCIAS
from app.templating import avisar, templates

router = APIRouter(prefix="/recuperaciones")
roles_rec = requiere_rol("gestor_recuperaciones", "gerente")
solo_gerente = requiere_rol("gerente")


def _credito(db: Session, usuario: Usuario, credito_id: int) -> Credito:
    cr = db.get(Credito, credito_id)
    if not cr:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Crédito no encontrado")
    if usuario.rol == "gestor_recuperaciones" and cr.gestor_id != usuario.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Este crédito está asignado a otro gestor")
    return cr


def _volver(cr: Credito, ancla: str = "") -> RedirectResponse:
    return RedirectResponse(f"/recuperaciones/creditos/{cr.id}{ancla}", status.HTTP_303_SEE_OTHER)


def _gestores(db: Session) -> list[Usuario]:
    return db.scalars(select(Usuario).where(Usuario.rol == "gestor_recuperaciones", Usuario.activo.is_(True)).order_by(Usuario.nombre)).all()


def _decimal(valor: str, campo: str) -> Decimal:
    try:
        d = Decimal(str(valor).replace(",", ".")).quantize(Decimal("0.01"))
    except Exception:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{campo}: debe ser un número")
    if d <= 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{campo}: debe ser mayor que cero")
    return d


def _fecha(valor: str, campo: str) -> date:
    try:
        return date.fromisoformat(str(valor))
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{campo}: fecha inválida")


# ---------- Cartera ----------

@router.get("")
def cartera(request: Request, tramo: str = "", usuario: Usuario = Depends(roles_rec), db: Session = Depends(get_db)):
    rec.actualizar_compromisos(db)
    hoy = hoy_peru()
    filas = [{"cr": cr, "r": rec.resumen(cr, hoy)} for cr in rec.creditos_de(db, usuario)]
    filas.sort(key=lambda f: -f["r"]["dias_atraso"])
    total_saldo = sum((f["r"]["saldo"] for f in filas), Decimal("0"))
    total_vencido = sum((f["r"]["vencido"] for f in filas), Decimal("0"))
    en_mora = sum(1 for f in filas if f["r"]["dias_atraso"] > 0)
    por_tramo = {}
    for f in filas:
        por_tramo[f["r"]["tramo"]["clave"]] = por_tramo.get(f["r"]["tramo"]["clave"], 0) + 1
    if tramo:
        filas = [f for f in filas if f["r"]["tramo"]["clave"] == tramo]
    return templates.TemplateResponse(
        request, "cartera.html",
        {"usuario": usuario, "filas": filas, "total_saldo": total_saldo, "total_vencido": total_vencido, "en_mora": en_mora,
         "por_tramo": por_tramo, "tramos": rec.config()["tramos"], "tramo": tramo,
         "pct_mora": round(100 * float(total_vencido) / float(total_saldo), 1) if total_saldo else 0},
    )


@router.get("/alertas")
def alertas(request: Request, usuario: Usuario = Depends(roles_rec), db: Session = Depends(get_db)):
    rec.actualizar_compromisos(db)
    lista = rec.alertas(db, usuario)
    mensajes = {}
    for i, a in enumerate(lista):
        tipo = {"cuota_vencida": "vencida", "proximo_vencimiento": "proximo", "compromiso_proximo": "compromiso"}.get(a["tipo"])
        texto = rec.mensaje_sugerido(tipo, a["credito"], a["fecha"], a["monto"]) if tipo and "monto" in a else None
        mensajes[i] = {"texto": texto, "whatsapp": rec.enlace_whatsapp(a["credito"], texto) if texto else None}
    return templates.TemplateResponse(
        request, "recuperaciones_alertas.html",
        {"usuario": usuario, "alertas": lista, "mensajes": mensajes, "tipos": rec.TIPOS_ALERTA,
         "reglas": rec.config()["reglas_trato"]},
    )


# ---------- Registrar crédito (solo gerente: operador autorizado) ----------

def _form_credito(request, usuario, db, v, errores, status_code=200):
    return templates.TemplateResponse(
        request, "credito_form.html",
        {"usuario": usuario, "v": v, "errores": errores, "productos": negocios.productos(),
         "clientes": db.scalars(select(Cliente).order_by(Cliente.nombres)).all(), "gestores": _gestores(db),
         "frecuencias": {k: f["nombre"] for k, f in FRECUENCIAS.items()}},
        status_code=status_code,
    )


@router.get("/creditos/nuevo")
def credito_nuevo(request: Request, solicitud_id: int | None = None, usuario: Usuario = Depends(solo_gerente), db: Session = Depends(get_db)):
    v = {"fecha_desembolso": hoy_peru().isoformat(), "frecuencia": "mensual"}
    if solicitud_id:
        s = db.get(Solicitud, solicitud_id)
        if s and s.estado == "aprobada":
            p = negocios.productos().get(s.producto, {})
            v |= {"cliente_id": str(s.cliente_id), "solicitud_id": str(s.id), "producto": s.producto, "monto": str(s.monto),
                  "plazo_meses": str(s.plazo_meses), "frecuencia": s.frecuencia, "tea": str(p.get("tea_demo", ""))}
    return _form_credito(request, usuario, db, v, {})


@router.post("/creditos/nuevo")
async def credito_crear(request: Request, usuario: Usuario = Depends(solo_gerente), db: Session = Depends(get_db)):
    datos = dict(await request.form())
    try:
        e = CreditoEntrada(**datos)
    except ValidationError as ex:
        return _form_credito(request, usuario, db, datos, errores_es(ex), status.HTTP_422_UNPROCESSABLE_ENTITY)
    errores = {}
    if not db.get(Cliente, e.cliente_id):
        errores["cliente_id"] = "Elige un cliente"
    if e.producto not in negocios.productos():
        errores["producto"] = "Elige un producto"
    if e.solicitud_id:
        s = db.get(Solicitud, e.solicitud_id)
        if not s or s.cliente_id != e.cliente_id or s.estado != "aprobada":
            errores["solicitud_id"] = "La solicitud debe estar aprobada y ser del mismo cliente"
        elif db.scalar(select(Credito).where(Credito.solicitud_id == s.id)):
            errores["solicitud_id"] = "Esa solicitud ya tiene un crédito registrado"
    if e.gestor_id:
        g = db.get(Usuario, e.gestor_id)
        if not g or g.rol != "gestor_recuperaciones":
            errores["gestor_id"] = "Elige un gestor de recuperaciones"
    if errores:
        return _form_credito(request, usuario, db, datos, errores, status.HTTP_422_UNPROCESSABLE_ENTITY)
    cr = Credito(**e.model_dump(), registrado_por=usuario.id, estado="vigente")
    rec.generar_cuotas(cr)
    db.add(cr)
    db.flush()
    registrar(db, "credito_registrado", usuario, f"crédito {cr.id} · cliente {cr.cliente_id}")
    db.commit()
    avisar(request, f"Crédito registrado para seguimiento con {len(cr.cuotas)} cuotas")
    return _volver(cr)


# ---------- Detalle y gestión ----------

@router.get("/creditos/{credito_id}")
def credito_detalle(credito_id: int, request: Request, usuario: Usuario = Depends(roles_rec), db: Session = Depends(get_db)):
    rec.actualizar_compromisos(db)
    cr = _credito(db, usuario, credito_id)
    hoy = hoy_peru()
    r = rec.resumen(cr, hoy)
    cfg = rec.config()
    mensaje = None
    if r["proxima"]:
        tipo = "vencida" if r["dias_atraso"] > 0 else "proximo"
        cuota = next(c for c in cr.cuotas if rec.pendiente(c) > 0)
        texto = rec.mensaje_sugerido(tipo, cr, cuota.fecha_vencimiento, rec.pendiente(cuota))
        mensaje = {"texto": texto, "whatsapp": rec.enlace_whatsapp(cr, texto)}
    return templates.TemplateResponse(
        request, "credito_detalle.html",
        {"usuario": usuario, "cr": cr, "r": r, "hoy": hoy, "estado_cuota": rec.estado_cuota, "pendiente": rec.pendiente,
         "resultados": cfg["resultados_gestion"], "canales": CANALES, "reglas": cfg["reglas_trato"], "mensaje": mensaje,
         "gestores": _gestores(db), "productos": negocios.productos(), "frecuencias": FRECUENCIAS},
    )


@router.post("/creditos/{credito_id}/pago")
async def registrar_pago(credito_id: int, request: Request, usuario: Usuario = Depends(roles_rec), db: Session = Depends(get_db)):
    cr = _credito(db, usuario, credito_id)
    form = await request.form()
    monto = _decimal(form.get("monto", ""), "Monto")
    fecha = _fecha(form.get("fecha", ""), "Fecha")
    if fecha > hoy_peru() or fecha < cr.fecha_desembolso:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La fecha del pago debe estar entre el desembolso y hoy")
    try:
        rec.aplicar_pago(cr, monto, fecha)
    except ValueError as e:
        avisar(request, str(e))
        return _volver(cr, "#pagos")
    db.add(Pago(credito_id=cr.id, fecha=fecha, monto=monto, registrado_por=usuario.id,
                observacion=str(form.get("observacion", "")).strip()[:500] or None))
    # Si hay un compromiso pendiente y el pago lo cubre, se marca como cumplido
    for cp in cr.compromisos:
        if cp.estado == "pendiente" and monto >= cp.monto and fecha <= cp.fecha:
            cp.estado = "cumplido"
    registrar(db, "pago_registrado", usuario, f"crédito {cr.id} · S/ {monto}")
    db.commit()
    avisar(request, "Pago registrado" + (". El crédito quedó cancelado." if cr.estado == "cancelado" else ""))
    return _volver(cr, "#pagos")


@router.post("/creditos/{credito_id}/gestion")
async def registrar_gestion(credito_id: int, request: Request, usuario: Usuario = Depends(roles_rec), db: Session = Depends(get_db)):
    cr = _credito(db, usuario, credito_id)
    form = await request.form()
    canal, resultado = str(form.get("canal", "")), str(form.get("resultado", ""))
    if canal not in CANALES or resultado not in rec.config()["resultados_gestion"]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Elige canal y resultado")
    db.add(GestionCobranza(credito_id=cr.id, usuario_id=usuario.id, canal=canal, resultado=resultado,
                           observacion=str(form.get("observacion", "")).strip()[:1000] or None))
    registrar(db, "gestion_registrada", usuario, f"crédito {cr.id} · {resultado}")
    db.commit()
    avisar(request, "Gestión registrada")
    return _volver(cr, "#gestiones")


@router.post("/creditos/{credito_id}/compromiso")
async def registrar_compromiso(credito_id: int, request: Request, usuario: Usuario = Depends(roles_rec), db: Session = Depends(get_db)):
    cr = _credito(db, usuario, credito_id)
    form = await request.form()
    fecha = _fecha(form.get("fecha", ""), "Fecha")
    monto = _decimal(form.get("monto", ""), "Monto")
    if fecha < hoy_peru():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El compromiso debe ser para hoy o una fecha futura")
    db.add(CompromisoPago(credito_id=cr.id, fecha=fecha, monto=monto, creado_por=usuario.id))
    registrar(db, "compromiso_registrado", usuario, f"crédito {cr.id} · {fecha.isoformat()}")
    db.commit()
    avisar(request, "Compromiso de pago registrado")
    return _volver(cr, "#compromisos")


@router.post("/compromisos/{compromiso_id}/estado")
async def estado_compromiso(compromiso_id: int, request: Request, usuario: Usuario = Depends(roles_rec), db: Session = Depends(get_db)):
    cp = db.get(CompromisoPago, compromiso_id)
    if not cp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compromiso no encontrado")
    cr = _credito(db, usuario, cp.credito_id)
    nuevo = str((await request.form()).get("estado", ""))
    if nuevo not in ("cumplido", "incumplido"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Estado inválido")
    cp.estado = nuevo
    registrar(db, "compromiso_estado", usuario, f"compromiso {cp.id} → {nuevo}")
    db.commit()
    return _volver(cr, "#compromisos")


@router.post("/creditos/{credito_id}/reprogramacion")
async def pedir_reprogramacion(credito_id: int, request: Request, usuario: Usuario = Depends(roles_rec), db: Session = Depends(get_db)):
    cr = _credito(db, usuario, credito_id)
    form = await request.form()
    tipo = str(form.get("tipo", ""))
    motivo = str(form.get("motivo", "")).strip()
    if tipo not in ("reprogramacion", "refinanciamiento") or len(motivo) < 10:
        avisar(request, "Elige el tipo y describe el motivo (mínimo 10 caracteres)")
        return _volver(cr, "#reprogramaciones")
    db.add(Reprogramacion(credito_id=cr.id, tipo=tipo, motivo=motivo[:2000], solicitada_por=usuario.id))
    registrar(db, "reprogramacion_solicitada", usuario, f"crédito {cr.id} · {tipo}")
    db.commit()
    avisar(request, "Solicitud registrada: la revisará el gerente")
    return _volver(cr, "#reprogramaciones")


@router.post("/reprogramaciones/{reprogramacion_id}/revisar")
async def revisar_reprogramacion(reprogramacion_id: int, request: Request, usuario: Usuario = Depends(solo_gerente), db: Session = Depends(get_db)):
    rp = db.get(Reprogramacion, reprogramacion_id)
    if not rp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Solicitud no encontrada")
    if rp.estado != "pendiente":
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya fue revisada")
    form = await request.form()
    decision = str(form.get("decision", ""))
    comentario = str(form.get("comentario", "")).strip()
    if decision not in ("aprobada", "rechazada") or len(comentario) < 5:
        avisar(request, "Elige la decisión y escribe un comentario")
        return _volver(rp.credito, "#reprogramaciones")
    rp.estado, rp.comentario_revision = decision, comentario[:2000]
    rp.revisada_por, rp.revisado_en = usuario.id, datetime.now(timezone.utc)
    registrar(db, "reprogramacion_revisada", usuario, f"reprogramación {rp.id} → {decision}")
    db.commit()
    avisar(request, f"Solicitud {decision}. Los nuevos términos los define la entidad en su sistema oficial.")
    return _volver(rp.credito, "#reprogramaciones")


@router.post("/creditos/{credito_id}/asignar")
async def asignar_gestor(credito_id: int, request: Request, usuario: Usuario = Depends(solo_gerente), db: Session = Depends(get_db)):
    cr = _credito(db, usuario, credito_id)
    gestor_id = str((await request.form()).get("gestor_id", ""))
    g = db.get(Usuario, int(gestor_id)) if gestor_id.isdigit() else None
    if not g or g.rol != "gestor_recuperaciones" or not g.activo:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Elige un gestor activo")
    cr.gestor_id = g.id
    registrar(db, "credito_asignado", usuario, f"crédito {cr.id} → usuario {g.id}")
    db.commit()
    avisar(request, f"Crédito asignado a {g.nombre}")
    return _volver(cr)
