"""Datos de DEMOSTRACIÓN para ACTIVA 360° (personas ficticias), para ver los 4 módulos sin esperar semanas.

Crea: usuarios analista y gestor, prospectos en todo el embudo, expedientes, solicitudes en varios
estados (con evaluación preliminar) y créditos en seguimiento con pagos, atrasos y compromisos.
Todo lo de demostración usa DNI que empiezan con 9000 y prospectos con origen "demo".

Uso (desde backend/, con el entorno activado):
    python -m scripts.seed_360            # crea los datos (si ya existen, no duplica)
    python -m scripts.seed_360 --borrar   # elimina solo los datos de demostración
"""
import argparse
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select

from app.config import hoy_peru
from app.db import SessionLocal
from app.models import (CompromisoPago, ContactoProspecto, Credito, Cliente, DocumentoSolicitud, EvaluacionRiesgo,
                        GestionCobranza, MovimientoSolicitud, Pago, Prospecto, Reprogramacion, Solicitud, Usuario)
from app.security import cifrar_password
from app.services import negocios, riesgos
from app.services import recuperaciones as rec

USUARIOS_DEMO = [
    {"nombre": "Rocío Analista", "email": "analista@activa.pe", "password": "Analista2026!", "rol": "analista_riesgos"},
    {"nombre": "Julio Gestor", "email": "gestor@activa.pe", "password": "Gestor2026!", "rol": "gestor_recuperaciones"},
]

# nombre, segmento, actividad, región, monto, estado
PROSPECTOS = [
    ("Marina Flores (demo)", "comerciante", "Venta de frutas en mercado", "la_libertad", 3000, "nuevo"),
    ("Óscar Huamán (demo)", "transportista", "Mototaxi", "piura", 4500, "nuevo"),
    ("Lucía Ramos (demo)", "emprendedor", "Repostería por pedido", "lima", 2500, "contactado"),
    ("Hugo Condori (demo)", "agricultor", "Cultivo de papa", "huanuco", 6000, "contactado"),
    ("Elena Vargas (demo)", "dependiente", "Auxiliar administrativa", "lambayeque", 5000, "interesado"),
    ("Raúl Medina (demo)", "independiente", "Gasfitero", "arequipa", 3500, "interesado"),
    ("Sonia Paredes (demo)", "persona_natural", "Ama de casa con ingresos de alquiler", "cusco", 2000, "no_convertido"),
    ("Iván Salazar (demo)", "comerciante", "Bodega", "junin", 8000, "convertido"),
]

# dni, nombres, celular, segmento, ocupación, región, ingresos, gastos, antigüedad, cuotas otras, perfil, producto, monto, plazo, estado final
CLIENTES = [
    ("90000001", "Iván Salazar (demo)", "961000001", "comerciante", "Bodega", "junin", 5200, 2100, 60, 250,
     {"giro": "Abarrotes", "ventas_mensuales": 14000, "costo_ventas": 10500}, "capital_trabajo", 8000, 12, "aprobada"),
    ("90000002", "Carmen Rojas (demo)", "961000002", "dependiente", "Docente", "la_libertad", 3200, 1400, 48, 400,
     {"empleador": "Colegio privado", "sueldo_neto": 3200, "descuentos_planilla": 0}, "personal", 6000, 24, "evaluada"),
    ("90000003", "Pedro Ccori (demo)", "961000003", "transportista", "Taxi", "cusco", 2600, 1900, 18, 500,
     {"tipo_vehiculo": "Taxi sedán", "ingreso_diario": 100, "dias_trabajo_mes": 26}, "activo_fijo", 25000, 36, "en_evaluacion"),
    ("90000004", "Rosa Ticona (demo)", "961000004", "agricultor", "Cultivo de quinua", "puno", 2200, 900, 120, 0,
     {"cultivo": "Quinua", "ingreso_por_campana": 9000, "campanas_por_anio": 2}, "capital_trabajo", 4000, 8, "enviada"),
    ("90000005", "Jorge Lazo (demo)", "961000005", "independiente", "Electricista", "arequipa", 2800, 1300, 4, 200,
     {"servicio": "Instalaciones eléctricas", "ingreso_mes_bajo": 1800, "ingreso_mes_alto": 3600}, "independientes", 3000, 12, "observada"),
    ("90000006", "Ana Quispe (demo)", "961000006", "emprendedor", "Venta de ropa por redes", "lima", 2400, 1200, 10, 0,
     {"etapa": "crecimiento", "ventas_mensuales": 6000, "costo_ventas": 3600}, "emprendimiento", 5000, 12, "borrador"),
]

RUTA = ["borrador", "enviada", "en_evaluacion", "evaluada", "aprobada"]


def _usuario(db, email):
    return db.scalar(select(Usuario).where(Usuario.email == email))


def crear(db) -> None:
    nuevos = []
    for u in USUARIOS_DEMO:
        if not _usuario(db, u["email"]):
            db.add(Usuario(nombre=u["nombre"], email=u["email"], rol=u["rol"], password_hash=cifrar_password(u["password"])))
            nuevos.append(u)
    db.commit()
    # Se informa solo después de guardar, para no anunciar usuarios que no se crearon
    for u in nuevos:
        print(f"Usuario demo creado: {u['email']} / {u['password']} ({u['rol']})")
    asesor = _usuario(db, "asesor@activa.pe") or db.scalar(select(Usuario).where(Usuario.rol == "asesor"))
    gerente = _usuario(db, "gerente@activa.pe") or db.scalar(select(Usuario).where(Usuario.rol == "gerente"))
    analista = _usuario(db, "analista@activa.pe")
    gestor = _usuario(db, "gestor@activa.pe")
    if not asesor or not gerente:
        raise SystemExit("Primero crea los usuarios base: python -m scripts.seed_usuarios")
    if db.scalar(select(Cliente).where(Cliente.dni == "90000001")):
        print("Los datos de demostración ya existen. Usa --borrar para quitarlos.")
        return
    hoy = hoy_peru()

    # --- Comercial: prospectos en todo el embudo ---
    prospectos = {}
    for i, (nombre, seg, act, reg, monto, estado) in enumerate(PROSPECTOS):
        p = Prospecto(nombre=nombre, telefono=f"96200000{i}", segmento=seg, actividad=act,
                      necesidad=f"Financiamiento para {act.lower()}", region=reg, monto_solicitado=Decimal(monto),
                      contacto_preferido="whatsapp", consentimiento=True, estado=estado, origen="demo",
                      asesor_id=asesor.id if i % 3 else None, creado_por=asesor.id,
                      proxima_accion=hoy - timedelta(days=i % 3) if estado in ("contactado", "interesado") else None)
        db.add(p)
        db.flush()
        if estado != "nuevo":
            db.add(ContactoProspecto(prospecto_id=p.id, usuario_id=asesor.id, canal="whatsapp",
                                     resultado="Primer contacto por WhatsApp", estado_nuevo=estado))
        prospectos[nombre] = p

    # --- Negocios y riesgos: expedientes y solicitudes ---
    clientes = {}
    for (dni, nombres, tel, seg, ocup, reg, ing, gas, ant, otras, perfil, prod, monto, plazo, final) in CLIENTES:
        c = Cliente(dni=dni, nombres=nombres, telefono=tel, segmento=seg, ocupacion=ocup, region=reg,
                    ingresos_mensuales=Decimal(ing), gastos_mensuales=Decimal(gas), antiguedad_meses=ant,
                    cuotas_otras_deudas=Decimal(otras), saldo_otras_deudas=Decimal(otras * 8), consentimiento=True,
                    asesor_id=asesor.id, creado_por=asesor.id,
                    prospecto_id=prospectos[nombres].id if nombres in prospectos else None)
        db.add(c)
        db.flush()
        clientes[dni] = c
        s = Solicitud(cliente_id=c.id, asesor_id=asesor.id, producto=prod, monto=Decimal(monto), plazo_meses=plazo,
                      frecuencia="mensual", destino=f"Destino declarado para {ocup.lower()}", datos_perfil=perfil, estado="borrador")
        s.documentos = [DocumentoSolicitud(tipo=t, estado="validado" if final not in ("borrador", "observada") else "pendiente")
                        for t in negocios.documentos_requeridos(seg)]
        db.add(s)
        db.flush()
        db.add(MovimientoSolicitud(solicitud_id=s.id, usuario_id=asesor.id, estado_nuevo="borrador", comentario="Solicitud creada"))
        ruta = RUTA[: RUTA.index(final) + 1] if final in RUTA else ["borrador", "enviada", "en_evaluacion", "observada"]
        for anterior, nuevo in zip(ruta, ruta[1:]):
            quien = {"enviada": asesor, "en_evaluacion": analista or gerente, "evaluada": analista or gerente,
                     "observada": analista or gerente, "aprobada": gerente}[nuevo]
            comentario = {"evaluada": "Capacidad suficiente según lo declarado.", "aprobada": "Aprobada por el comité (demo).",
                          "observada": "Falta sustento de ingresos y antigüedad menor a 6 meses."}.get(nuevo)
            db.add(MovimientoSolicitud(solicitud_id=s.id, usuario_id=quien.id, estado_anterior=anterior,
                                       estado_nuevo=nuevo, comentario=comentario))
            s.estado = nuevo
        db.flush()
        db.refresh(s)
        if s.estado != "borrador":
            ev = riesgos.guardar_evaluacion(db, s, (analista or gerente).id)
            if s.estado in ("evaluada", "aprobada"):
                ev.opinion, ev.opinion_por = "Indicadores dentro de lo configurado (demo).", (analista or gerente).id

    # --- Recuperaciones: créditos con distintos comportamientos de pago ---
    casos = [  # dni, monto, plazo, días desde desembolso, cuotas pagadas
        ("90000001", 8000, 12, 100, 3),   # al día
        ("90000002", 5000, 10, 130, 2),   # atraso moderado
        ("90000003", 12000, 18, 200, 3),  # atraso alto
        ("90000004", 3000, 6, 28, 0),     # vence en pocos días
    ]
    for dni, monto, plazo, dias, pagadas in casos:
        c = clientes[dni]
        cr = Credito(cliente_id=c.id, producto="capital_trabajo", monto=Decimal(monto), tea=Decimal("45"),
                     plazo_meses=plazo, frecuencia="mensual", fecha_desembolso=hoy - timedelta(days=dias),
                     gestor_id=gestor.id if gestor else None, registrado_por=gerente.id)
        rec.generar_cuotas(cr)
        db.add(cr)
        db.flush()
        if pagadas:
            total = sum((cu.monto for cu in cr.cuotas[:pagadas]), Decimal("0"))
            rec.aplicar_pago(cr, total, hoy - timedelta(days=5))
            db.add(Pago(credito_id=cr.id, fecha=hoy - timedelta(days=5), monto=total, registrado_por=gerente.id,
                        observacion="Pagos acumulados (demo)"))
        if dni == "90000002":
            db.add(GestionCobranza(credito_id=cr.id, usuario_id=(gestor or gerente).id, canal="llamada", resultado="compromiso",
                                   observacion="Se comprometió a pagar al cobrar su sueldo"))
            db.add(CompromisoPago(credito_id=cr.id, fecha=hoy + timedelta(days=2), monto=cr.cuotas[pagadas].monto,
                                  creado_por=(gestor or gerente).id))
        if dni == "90000003":
            db.add(CompromisoPago(credito_id=cr.id, fecha=hoy - timedelta(days=3), monto=Decimal("500"),
                                  creado_por=(gestor or gerente).id, estado="incumplido"))
            db.add(Reprogramacion(credito_id=cr.id, tipo="reprogramacion", motivo="El vehículo estuvo en reparación un mes",
                                  solicitada_por=(gestor or gerente).id))
    db.commit()
    print("Datos de demostración creados: 8 prospectos, 6 expedientes con solicitudes y 4 créditos en seguimiento.")


def borrar(db) -> None:
    clientes = [c.id for c in db.scalars(select(Cliente).where(Cliente.dni.like("9000%")))]
    creditos = [c.id for c in db.scalars(select(Credito).where(Credito.cliente_id.in_(clientes)))]
    solicitudes = [s.id for s in db.scalars(select(Solicitud).where(Solicitud.cliente_id.in_(clientes)))]
    prospectos = [p.id for p in db.scalars(select(Prospecto).where(Prospecto.origen == "demo"))]
    for modelo in (Pago, GestionCobranza, CompromisoPago, Reprogramacion):
        db.execute(delete(modelo).where(modelo.credito_id.in_(creditos)))
    from app.models import Cuota
    db.execute(delete(Cuota).where(Cuota.credito_id.in_(creditos)))
    db.execute(delete(Credito).where(Credito.id.in_(creditos)))
    for modelo in (DocumentoSolicitud, MovimientoSolicitud, EvaluacionRiesgo):
        db.execute(delete(modelo).where(modelo.solicitud_id.in_(solicitudes)))
    db.execute(delete(Solicitud).where(Solicitud.id.in_(solicitudes)))
    db.execute(delete(Cliente).where(Cliente.id.in_(clientes)))
    db.execute(delete(ContactoProspecto).where(ContactoProspecto.prospecto_id.in_(prospectos)))
    db.execute(delete(Prospecto).where(Prospecto.id.in_(prospectos)))
    db.commit()
    print(f"Eliminados: {len(prospectos)} prospectos, {len(clientes)} expedientes, {len(solicitudes)} solicitudes, {len(creditos)} créditos.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--borrar", action="store_true", help="elimina solo los datos de demostración")
    args = parser.parse_args()
    with SessionLocal() as db:
        borrar(db) if args.borrar else crear(db)


if __name__ == "__main__":
    main()
