"""Menú lateral de ACTIVA 360°: módulos y opciones visibles según el rol."""

TODOS = ("asesor", "gerente", "analista_riesgos", "gestor_recuperaciones")
COMERCIAL = ("asesor", "gerente")

MENU = [
    {"modulo": None, "opciones": [
        {"titulo": "Panel", "icono": "speedometer2", "url": "/panel", "roles": TODOS},
    ]},
    {"modulo": "Comercial", "opciones": [
        {"titulo": "Prospectos", "icono": "person-plus", "url": "/prospectos", "roles": COMERCIAL},
        {"titulo": "Campañas", "icono": "megaphone", "url": "/campanas", "roles": COMERCIAL},
        {"titulo": "Interesados (chatbot)", "icono": "chat-heart", "url": "/interesados", "roles": COMERCIAL},
        {"titulo": "Encuestas", "icono": "clipboard-check", "url": "/encuestas", "roles": COMERCIAL},
        {"titulo": "Bloques", "icono": "collection", "url": "/bloques", "roles": COMERCIAL},
        {"titulo": "Análisis de bloque", "icono": "graph-up", "url": "/analisis", "roles": COMERCIAL},
        {"titulo": "Clima y estación (IoT)", "icono": "cloud-sun", "url": "/clima", "roles": COMERCIAL},
    ]},
    {"modulo": "Negocios", "opciones": [
        {"titulo": "Clientes", "icono": "folder2-open", "url": "/clientes", "roles": ("asesor", "gerente", "analista_riesgos")},
        {"titulo": "Solicitudes", "icono": "file-earmark-text", "url": "/solicitudes", "roles": ("asesor", "gerente", "analista_riesgos")},
        {"titulo": "Simulador de cuotas", "icono": "calculator", "url": "/simulador", "roles": TODOS},
        {"titulo": "Productos", "icono": "box-seam", "url": "/productos", "roles": TODOS},
    ]},
    {"modulo": "Riesgos", "opciones": [
        {"titulo": "Evaluaciones", "icono": "shield-check", "url": "/riesgos", "roles": ("analista_riesgos", "gerente")},
        {"titulo": "Alertas de seguridad", "icono": "shield-exclamation", "url": "/riesgos/seguridad", "roles": ("analista_riesgos", "gerente")},
    ]},
    {"modulo": "Recuperaciones", "opciones": [
        {"titulo": "Cartera", "icono": "wallet2", "url": "/recuperaciones", "roles": ("gestor_recuperaciones", "gerente")},
        {"titulo": "Alertas preventivas", "icono": "bell", "url": "/recuperaciones/alertas", "roles": ("gestor_recuperaciones", "gerente")},
    ]},
    {"modulo": "Administración", "opciones": [
        {"titulo": "Usuarios", "icono": "people", "url": "/usuarios", "roles": ("gerente",)},
        {"titulo": "Auditoría", "icono": "journal-text", "url": "/auditoria", "roles": ("gerente",)},
        {"titulo": "Modelo de IA", "icono": "cpu", "url": "/analisis/modelo", "roles": COMERCIAL},
    ]},
]


def menu_para(rol: str) -> list[dict]:
    """Módulos con al menos una opción visible para el rol."""
    salida = []
    for grupo in MENU:
        opciones = [o for o in grupo["opciones"] if rol in o["roles"]]
        if opciones:
            salida.append({"modulo": grupo["modulo"], "opciones": opciones})
    return salida
