from fastapi import APIRouter, Depends, Request

from app.models import Usuario
from app.security import requiere_rol
from app.templating import templates

router = APIRouter()

# Opciones del menú; cada una se activa en la fase indicada
BLOQUES_ASESOR = {"titulo": "Bloques", "descripcion": "Ver los bloques y su estado", "icono": "collection", "url": "/bloques"}
BLOQUES_GERENTE = {"titulo": "Bloques", "descripcion": "Crear, abrir y cerrar bloques de encuestas", "icono": "collection", "url": "/bloques"}

OPCIONES_COMUNES = [
    {"titulo": "Encuestas", "descripcion": "Registrar y editar encuestas socioeconómicas", "icono": "clipboard-check", "url": "/encuestas"},
    {"titulo": "Clima y estación", "descripcion": "Registros diarios y estación actual", "icono": "cloud-sun", "url": "/clima"},
    {"titulo": "Análisis de bloque", "descripcion": "Necesidades detectadas por la IA", "icono": "graph-up", "fase": 5},
    {"titulo": "Generar campaña", "descripcion": "Propuesta de campaña con IA", "icono": "megaphone", "fase": 5},
    {"titulo": "Interesados", "descripcion": "Clientes captados por el chatbot", "icono": "people", "fase": 6},
]

OPCIONES_ASESOR = [BLOQUES_ASESOR] + OPCIONES_COMUNES

OPCIONES_GERENTE = [BLOQUES_GERENTE] + OPCIONES_COMUNES + [
    {"titulo": "Publicar campañas", "descripcion": "Aprobar y publicar campañas vigentes", "icono": "patch-check", "fase": 5},
]


@router.get("/asesor")
def menu_asesor(request: Request, usuario: Usuario = Depends(requiere_rol("asesor", "gerente"))):
    return templates.TemplateResponse(
        request, "menu.html", {"usuario": usuario, "titulo": "Menú del asesor", "opciones": OPCIONES_ASESOR}
    )


@router.get("/gerente")
def menu_gerente(request: Request, usuario: Usuario = Depends(requiere_rol("gerente"))):
    return templates.TemplateResponse(
        request, "menu.html", {"usuario": usuario, "titulo": "Menú del gerente", "opciones": OPCIONES_GERENTE}
    )
