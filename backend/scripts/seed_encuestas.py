"""Crea 3 bloques con 20 encuestas de ejemplo (datos FICTICIOS, no son clientes reales).

Uso (desde backend/, con el entorno activado y después de seed_usuarios):
    python -m scripts.seed_encuestas
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Bloque, Encuesta, Usuario

BLOQUES = [
    {
        "nombre": "Bloque 1 – Mercado Modelo (ejemplo)",
        "descripcion": "Comerciantes y ambulantes del Mercado Modelo de Huánuco. Datos ficticios.",
        "fecha_inicio": date(2026, 9, 7), "fecha_fin": date(2026, 9, 18), "activo": False,
    },
    {
        "nombre": "Bloque 2 – Valle agrícola (ejemplo)",
        "descripcion": "Agricultores de Pillco Marca, Santa María del Valle y Churubamba. Datos ficticios.",
        "fecha_inicio": date(2026, 10, 5), "fecha_fin": date(2026, 10, 16), "activo": True,
    },
    {
        "nombre": "Bloque 3 – Taxistas y ambulantes Amarilis (ejemplo)",
        "descripcion": "Taxistas y vendedores ambulantes de Amarilis. Datos ficticios.",
        "fecha_inicio": date(2026, 10, 19), "fecha_fin": None, "activo": True,
    },
]

# (bloque, nombre, zona, sector, ingreso, años, trabajadores, frecuencia, crédito, garantía,
#  necesidad, monto, plazo, temporada, riesgo, interés, contacto)
ENCUESTAS = [
    (0, "Rosa Quispe Tarazona", "Huánuco (Cercado)", "comerciante", 2800, 8, 1, "diaria", True, "aval",
     "Aumentar mercadería para la campaña navideña", 5000, 6, "verano", "bajas_ventas", True, "whatsapp"),
    (0, "Julio Espinoza Ramos", "Huánuco (Cercado)", "comerciante", 3500, 12, 2, "diaria", False, "propiedad",
     "Techar y cerrar el puesto antes de las lluvias", 4000, 8, "lluvias", "lluvias", True, "llamada"),
    (0, "Elena Huamán Soto", "Huánuco (Cercado)", "comerciante", 1900, 4, 0, "diaria", False, "ninguna",
     "Comprar abarrotes al por mayor para bajar costos", 2500, 6, "todo_el_anio", "alza_precios", True, "whatsapp"),
    (0, "Pedro Rojas Carhuamaca", "Amarilis", "ambulante", 1200, 3, 0, "diaria", False, "ninguna",
     "Comprar toldo y plásticos para vender en temporada de lluvias", 800, 4, "lluvias", "lluvias", True, "whatsapp"),
    (0, "Marleni Ayala Cruz", "Huánuco (Cercado)", "comerciante", 2200, 6, 1, "diaria", True, "aval",
     "Surtir ropa de abrigo para el invierno", 3000, 5, "invierno", "heladas", True, "visita"),
    (0, "Carlos Panduro Velásquez", "Huánuco (Cercado)", "ambulante", 1000, 2, 0, "diaria", False, "ninguna",
     "Comprar una congeladora para vender helados en verano", 1500, 6, "verano", "sequia", False, "llamada"),
    (0, "Nancy Tucto Ponce", "Amarilis", "comerciante", 2600, 10, 1, "diaria", False, "vehiculo",
     "Capital de trabajo para fiestas patrias y feriados", 3500, 6, "transicion", "bajas_ventas", True, "whatsapp"),

    (1, "Teodoro Chávez Albornoz", "Pillco Marca", "agricola", 1800, 15, 3, "cosecha", False, "propiedad",
     "Comprar semillas y abono antes de la siembra de lluvias", 6000, 9, "lluvias", "lluvias", True, "visita"),
    (1, "Marina Laureano Isidro", "Santa María del Valle", "agricola", 1500, 20, 2, "cosecha", True, "propiedad",
     "Reparar el canal de riego dañado por huaicos", 4500, 12, "lluvias", "lluvias", True, "llamada"),
    (1, "Fortunato Mallqui Bravo", "Churubamba", "agricola", 1300, 25, 4, "cosecha", False, "aval",
     "Proteger el cultivo de papa contra las heladas", 3500, 8, "invierno", "heladas", True, "visita"),
    (1, "Gladys Pimentel Ortiz", "Pillco Marca", "agricola", 2100, 9, 2, "cosecha", False, "propiedad",
     "Instalar riego por goteo para la época seca", 7000, 12, "verano", "sequia", True, "whatsapp"),
    (1, "Hilario Torres Mendoza", "Tomaykichwa", "agricola", 1600, 18, 3, "cosecha", True, "propiedad",
     "Contratar peones para la cosecha de maíz", 3000, 6, "transicion", "alza_precios", False, "llamada"),
    (1, "Zenaida Cóndor Rivera", "Santa María del Valle", "agricola", 1400, 12, 1, "cosecha", False, "ninguna",
     "Comprar fertilizante y fumigar antes de las lluvias", 2500, 6, "lluvias", "lluvias", True, "whatsapp"),
    (1, "Abel Santiago Fernández", "Churubamba", "agricola", 1200, 30, 2, "cosecha", False, "aval",
     "Comprar mallas antiheladas para el cultivo", 2000, 6, "invierno", "heladas", True, "visita"),

    (2, "Luis Alvarado Inga", "Amarilis", "taxista", 2400, 6, 0, "diaria", True, "vehiculo",
     "Cambiar llantas y frenos antes de la temporada de lluvias", 3000, 8, "lluvias", "lluvias", True, "whatsapp"),
    (2, "Wilmer Berrospi Cajas", "Amarilis", "taxista", 2000, 4, 0, "diaria", False, "vehiculo",
     "Reparar el motor del mototaxi", 2500, 6, "todo_el_anio", "salud", True, "llamada"),
    (2, "Edwin Gonzales Tello", "Pillco Marca", "taxista", 2700, 9, 0, "diaria", False, "vehiculo",
     "Pagar la conversión del auto a GLP para ahorrar combustible", 4000, 12, "todo_el_anio", "alza_precios", True, "whatsapp"),
    (2, "Yolanda Ambrosio Leandro", "Amarilis", "ambulante", 1100, 5, 0, "diaria", False, "ninguna",
     "Comprar un carrito con techo para vender emoliente en invierno", 1200, 6, "invierno", "heladas", True, "whatsapp"),
    (2, "Raúl Durand Picón", "Amarilis", "ambulante", 950, 2, 0, "diaria", False, "ninguna",
     "Capital para vender gaseosas y raspadillas en verano", 900, 4, "verano", "sequia", False, "llamada"),
    (2, "Sonia Villanueva Ruiz", "Huánuco (Cercado)", "taxista", 2200, 3, 0, "diaria", True, "aval",
     "Comprar parabrisas y plumillas nuevas para las lluvias", 1500, 5, "lluvias", "lluvias", True, "whatsapp"),
]


def main():
    with SessionLocal() as db:
        asesor = db.scalar(select(Usuario).where(Usuario.email == "asesor@activa.pe"))
        gerente = db.scalar(select(Usuario).where(Usuario.email == "gerente@activa.pe"))
        if not asesor or not gerente:
            print("Primero ejecuta: python -m scripts.seed_usuarios")
            return
        bloques = []
        for datos in BLOQUES:
            bloque = db.scalar(select(Bloque).where(Bloque.nombre == datos["nombre"]))
            if bloque:
                print(f"Ya existe: {bloque.nombre} (no se agregan encuestas)")
                bloques.append(None)
                continue
            bloque = Bloque(**datos, creado_por=gerente.id)  # los bloques los crea el gerente
            db.add(bloque)
            db.flush()
            bloques.append(bloque)
            print(f"Creado: {bloque.nombre}")

        creadas = 0
        for i, f in enumerate(ENCUESTAS):
            bloque = bloques[f[0]]
            if bloque is None:
                continue
            db.add(Encuesta(
                bloque_id=bloque.id, asesor_id=asesor.id, nombre=f[1],
                telefono=f"9000000{i:02d}",  # teléfonos ficticios
                zona=f[2], sector=f[3], ingreso_mensual=Decimal(f[4]), anios_negocio=f[5], trabajadores=f[6],
                frecuencia_ingresos=f[7], credito_vigente=f[8], garantia=f[9], necesidad=f[10],
                monto=Decimal(f[11]), plazo_meses=f[12], temporada_necesidad=f[13], riesgo_principal=f[14],
                interes_campana=f[15], contacto_preferido=f[16], consentimiento=True,
            ))
            creadas += 1
        db.commit()
        print(f"Encuestas de ejemplo creadas: {creadas}")


if __name__ == "__main__":
    main()
