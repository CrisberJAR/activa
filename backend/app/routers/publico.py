"""Página pública (landing) con las campañas vigentes y el chat del asesor virtual. No requiere login."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import cargar_tipos_campana, cargar_yaml
from app.db import get_db
from app.services.campanas import vigentes
from app.templating import templates

router = APIRouter()

ICONO_GRUPO = {
    "Festivas y comerciales": "gift-fill",
    "Agrícolas y pecuarias": "tree-fill",
    "Rubro y equipamiento": "tools",
    "Vivienda y salud": "house-heart-fill",
}


def campanas_publicas(db: Session) -> list[dict]:
    """Solo lo que ve el cliente: sin datos internos (decisiones de gerencia, sensores, etc.)."""
    tipos = cargar_tipos_campana()
    lista = []
    for c in vigentes(db):
        tipo = tipos.get(c.tipo_campana, {})
        e = c.entradas
        lista.append({
            "id": c.id,
            "nombre": c.nombre,
            "tipo": tipo.get("nombre", ""),
            "icono": ICONO_GRUPO.get(tipo.get("grupo"), "stars"),
            "propuesta": c.contenido["propuesta_valor"],
            "gancho": c.contenido["marketing"]["gancho"],
            "plazo": e["plazo_meses"],
            "gracia": e.get("periodo_gracia_meses") or 0,
            "monto_maximo": float(e["monto_maximo"]) if e.get("monto_maximo") else None,
            "zona": e["zona"],
            "hasta": c.vigente_hasta,
        })
    return lista


@router.get("/", include_in_schema=False)
def inicio(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request, "landing.html", {"inst": cargar_yaml("institucion"), "campanas": campanas_publicas(db)}
    )


@router.get("/chat", include_in_schema=False)
def chat():
    return RedirectResponse("/?chat=1")
