from datetime import datetime, timezone

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.catalogos import CATALOGOS, REGIONES, ROLES_TEXTO, SEGMENTOS, ZONAS
from app.config import BASE_DIR, HORA_PERU
from app.navegacion import menu_para


def _contexto(request: Request) -> dict:
    # Disponible en todas las plantillas: catálogos y el aviso pendiente (se muestra una sola vez)
    aviso = request.session.pop("aviso", None) if "session" in request.scope else None
    return {
        "cat": CATALOGOS, "zonas": ZONAS, "aviso": aviso, "menu_para": menu_para, "ruta": request.url.path,
        "roles_texto": ROLES_TEXTO, "segmentos": SEGMENTOS, "regiones": REGIONES,
    }


templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates", context_processors=[_contexto])

def fecha_hora(valor: datetime | None) -> str:
    """Muestra una fecha guardada en UTC con la hora de Perú."""
    if valor is None:
        return ""
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(HORA_PERU).strftime("%d/%m/%Y %H:%M")


templates.env.filters["fecha_hora"] = fecha_hora


def soles(valor) -> str:
    """Monto en soles con separador de miles: S/ 12,345.50."""
    if valor is None or valor == "":
        return "—"
    return f"S/ {float(valor):,.2f}"


templates.env.filters["soles"] = soles


def avisar(request: Request, texto: str) -> None:
    """Guarda un mensaje para mostrarlo en la siguiente página."""
    request.session["aviso"] = texto
