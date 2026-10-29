"""Opciones fijas de la encuesta: valor guardado → texto que ve el usuario."""

SECTORES = {
    "agricola": "Agrícola",
    "comerciante": "Comerciante de mercado",
    "ambulante": "Ambulante",
    "taxista": "Taxista",
}

FRECUENCIAS = {
    "diaria": "Diaria",
    "semanal": "Semanal",
    "quincenal": "Quincenal",
    "mensual": "Mensual",
    "cosecha": "Por cosecha",
}

GARANTIAS = {
    "ninguna": "Ninguna",
    "aval": "Aval",
    "vehiculo": "Vehículo",
    "propiedad": "Documento de propiedad",
    "otra": "Otra",
}

TEMPORADAS = {
    "lluvias": "Lluvias",
    "invierno": "Invierno",
    "verano": "Verano",
    "transicion": "Transición",
    "todo_el_anio": "Todo el año",
}

RIESGOS = {
    "lluvias": "Lluvias o huaicos",
    "heladas": "Heladas",
    "sequia": "Sequía o calor",
    "bajas_ventas": "Bajas ventas",
    "alza_precios": "Alza de precios",
    "salud": "Salud",
    "otro": "Otro",
}

CONTACTOS = {
    "whatsapp": "WhatsApp",
    "llamada": "Llamada",
    "visita": "Visita",
}

# Sugerencias para el campo zona (se puede escribir otra)
ZONAS = [
    "Huánuco (Cercado)", "Amarilis", "Pillco Marca", "Santa María del Valle",
    "Churubamba", "Tomaykichwa", "Ambo", "San Francisco de Cayrán", "Yacus",
]

# Campo de la encuesta → catálogo que lo valida
CATALOGOS = {
    "sector": SECTORES,
    "frecuencia_ingresos": FRECUENCIAS,
    "garantia": GARANTIAS,
    "temporada_necesidad": TEMPORADAS,
    "riesgo_principal": RIESGOS,
    "contacto_preferido": CONTACTOS,
}
