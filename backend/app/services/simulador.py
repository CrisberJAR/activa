"""Simulador de cuotas referenciales (método francés: cuota fija).

Fórmulas verificables:
    tasa periódica  i = (1 + TEA)^(1/n) - 1        n = periodos por año (12, 24 o 52)
    cuota           C = P · i / (1 - (1 + i)^-N)   N = número de cuotas
Con i = 0 la cuota es P / N. La última cuota se ajusta para que el saldo quede en cero.

No incluye comisiones ni seguros (no hay tarifario oficial): el resultado es REFERENCIAL
y no es una cotización de ninguna entidad.
"""
import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

FRECUENCIAS = {
    "mensual": {"nombre": "Mensual", "por_anio": 12},
    "quincenal": {"nombre": "Quincenal", "por_anio": 24},
    "semanal": {"nombre": "Semanal", "por_anio": 52},
}

CENTIMO = Decimal("0.01")


def _redondear(x) -> Decimal:
    return Decimal(str(x)).quantize(CENTIMO, rounding=ROUND_HALF_UP)


def numero_cuotas(plazo_meses: int, frecuencia: str) -> int:
    if frecuencia == "mensual":
        return plazo_meses
    if frecuencia == "quincenal":
        return plazo_meses * 2
    return round(plazo_meses * 52 / 12)


def tasa_periodica(tea_porcentaje: float, frecuencia: str) -> float:
    n = FRECUENCIAS[frecuencia]["por_anio"]
    return (1 + tea_porcentaje / 100) ** (1 / n) - 1


def sumar_meses(f: date, meses: int) -> date:
    mes = f.month - 1 + meses
    anio = f.year + mes // 12
    mes = mes % 12 + 1
    return date(anio, mes, min(f.day, calendar.monthrange(anio, mes)[1]))


def fecha_cuota(inicio: date, k: int, frecuencia: str) -> date:
    """Fecha de vencimiento de la cuota k (1, 2, …) contando desde el desembolso."""
    if frecuencia == "mensual":
        return sumar_meses(inicio, k)
    return inicio + timedelta(days=(15 if frecuencia == "quincenal" else 7) * k)


def simular(monto, tea: float, plazo_meses: int, frecuencia: str, inicio: date | None = None) -> dict:
    """Devuelve cuota, totales y cronograma. Lanza ValueError si los datos no son válidos."""
    if frecuencia not in FRECUENCIAS:
        raise ValueError("Frecuencia no válida")
    monto = Decimal(str(monto))
    if monto <= 0:
        raise ValueError("El monto debe ser mayor que cero")
    if not 0 <= tea <= 300:
        raise ValueError("La TEA debe estar entre 0 % y 300 %")
    if not 1 <= plazo_meses <= 120:
        raise ValueError("El plazo debe estar entre 1 y 120 meses")
    inicio = inicio or date.today()
    n = numero_cuotas(plazo_meses, frecuencia)
    i = tasa_periodica(tea, frecuencia)
    cuota_exacta = float(monto) / n if i == 0 else float(monto) * i / (1 - (1 + i) ** -n)
    cuota = _redondear(cuota_exacta)

    saldo = monto
    cronograma = []
    for k in range(1, n + 1):
        interes = _redondear(float(saldo) * i)
        capital = cuota - interes
        if k == n:  # la última cuota cierra el saldo exacto
            capital = saldo
        monto_cuota = capital + interes
        saldo = saldo - capital
        cronograma.append({
            "numero": k,
            "fecha": fecha_cuota(inicio, k, frecuencia),
            "capital": capital,
            "interes": interes,
            "cuota": monto_cuota,
            "saldo": saldo,
        })
    total = sum((c["cuota"] for c in cronograma), Decimal("0"))
    return {
        "monto": monto,
        "tea": tea,
        "plazo_meses": plazo_meses,
        "frecuencia": frecuencia,
        "n_cuotas": n,
        "tasa_periodica": round(i * 100, 4),  # en %
        "cuota": cuota,
        "total_pagar": total,
        "total_intereses": total - monto,
        "cronograma": cronograma,
    }


def cuota_estimada(monto, tea: float, plazo_meses: int, frecuencia: str) -> Decimal:
    """Cuota llevada a su equivalente MENSUAL (para compararla con ingresos mensuales)."""
    r = simular(monto, tea, plazo_meses, frecuencia)
    por_mes = Decimal(FRECUENCIAS[frecuencia]["por_anio"]) / Decimal(12)
    return _redondear(r["cuota"] * por_mes)
