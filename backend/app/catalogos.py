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

# Tipo de cliente al que apunta una campaña
TIPOS_CLIENTE = {
    "ambos": "Nuevos y recurrentes",
    "nuevo": "Clientes nuevos",
    "recurrente": "Clientes recurrentes",
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


# ---------- ACTIVA 360° ----------

ROLES_TEXTO = {
    "asesor": "Asesor de negocios",
    "gerente": "Gerente",
    "analista_riesgos": "Analista de riesgos",
    "gestor_recuperaciones": "Gestor de recuperaciones",
}

# Tipo de cliente (segmento) para prospectos, expedientes y campañas
SEGMENTOS = {
    "comerciante": "Comerciante",
    "emprendedor": "Emprendedor",
    "independiente": "Trabajador independiente",
    "dependiente": "Trabajador dependiente",
    "agricultor": "Agricultor",
    "transportista": "Transportista",
    "persona_natural": "Persona natural",
}

# Departamentos del Perú (alcance nacional) y el Callao
REGIONES = {
    "amazonas": "Amazonas", "ancash": "Áncash", "apurimac": "Apurímac", "arequipa": "Arequipa",
    "ayacucho": "Ayacucho", "cajamarca": "Cajamarca", "callao": "Callao", "cusco": "Cusco",
    "huancavelica": "Huancavelica", "huanuco": "Huánuco", "ica": "Ica", "junin": "Junín",
    "la_libertad": "La Libertad", "lambayeque": "Lambayeque", "lima": "Lima", "loreto": "Loreto",
    "madre_de_dios": "Madre de Dios", "moquegua": "Moquegua", "pasco": "Pasco", "piura": "Piura",
    "puno": "Puno", "san_martin": "San Martín", "tacna": "Tacna", "tumbes": "Tumbes", "ucayali": "Ucayali",
}

CANALES = {
    "whatsapp": "WhatsApp",
    "llamada": "Llamada",
    "visita": "Visita",
    "agencia": "En agencia",
}
