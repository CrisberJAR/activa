from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.catalogos import TEMPORADAS
from app.config import cargar_tipos_campana
from app.db import get_db
from app.models import Bloque, Encuesta, Usuario
from app.services import ml
from app.services.analisis import analisis_a_dict, analizar_bloque, ultimo_analisis
from app.services.clima import diagnostico_actual
from app.security import requiere_rol, usuario_web_o_api
from app.templating import avisar, templates

router = APIRouter()


def _bloque(db: Session, bloque_id: int) -> Bloque:
    bloque = db.get(Bloque, bloque_id)
    if not bloque:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bloque no encontrado")
    return bloque


def _estacion(db: Session) -> dict | None:
    """Estación actual del IoT (si no hay registros, el análisis sigue sin ella)."""
    diag = diagnostico_actual(db)
    return diag if diag.get("estacion_actual") else None


# ---------- Web ----------

@router.get("/analisis")
def pagina(
    request: Request,
    bloque_id: int | None = None,
    usuario: Usuario = Depends(requiere_rol("asesor", "gerente")),
    db: Session = Depends(get_db),
):
    filas = db.execute(
        select(Bloque, func.count(Encuesta.id))
        .outerjoin(Encuesta).group_by(Bloque.id).order_by(Bloque.fecha_inicio.desc())
    ).all()
    totales = {b.id: n for b, n in filas}
    bloque = _bloque(db, bloque_id) if bloque_id else None
    analisis = ultimo_analisis(db, bloque.id) if bloque else None
    return templates.TemplateResponse(
        request,
        "analisis.html",
        {
            "usuario": usuario,
            "filas": filas,
            "bloque": bloque,
            "total_actual": totales.get(bloque.id, 0) if bloque else 0,
            "analisis": analisis,
            "nombres": TEMPORADAS,
            "tipos": cargar_tipos_campana(),
        },
    )


@router.get("/analisis/modelo")
def pagina_modelo(request: Request, usuario: Usuario = Depends(requiere_rol("asesor", "gerente"))):
    """Métricas del Random Forest (para revisar el modelo y para el informe)."""
    return templates.TemplateResponse(
        request, "modelo.html", {"usuario": usuario, "m": ml.leer_metricas(), "tipos": cargar_tipos_campana()}
    )


@router.post("/analisis/{bloque_id}")
def analizar(
    request: Request,
    bloque_id: int,
    usuario: Usuario = Depends(requiere_rol("asesor", "gerente")),
    db: Session = Depends(get_db),
):
    bloque = _bloque(db, bloque_id)
    analisis = analizar_bloque(db, bloque, _estacion(db))
    if analisis is None:
        avisar(request, "El bloque no tiene encuestas: registra al menos una antes de analizar")
    elif analisis.indicadores["fuente_texto"] == "gemini":
        avisar(request, f"Análisis listo (texto generado con Gemini, modelo {analisis.indicadores['modelo_ia']})")
    else:
        avisar(request, f"Análisis listo con texto automático. Gemini no respondió: {analisis.indicadores['error_ia']}")
    return RedirectResponse(f"/analisis?bloque_id={bloque_id}", status.HTTP_303_SEE_OTHER)


# ---------- API ----------

@router.get("/api/analisis/{bloque_id}")
def api_ultimo(bloque_id: int, usuario: Usuario = Depends(usuario_web_o_api), db: Session = Depends(get_db)):
    analisis = ultimo_analisis(db, _bloque(db, bloque_id).id)
    if not analisis:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El bloque todavía no tiene análisis")
    return analisis_a_dict(analisis)


@router.post("/api/analisis/{bloque_id}")
def api_analizar(bloque_id: int, usuario: Usuario = Depends(usuario_web_o_api), db: Session = Depends(get_db)):
    analisis = analizar_bloque(db, _bloque(db, bloque_id), _estacion(db))
    if not analisis:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El bloque no tiene encuestas")
    return analisis_a_dict(analisis)
