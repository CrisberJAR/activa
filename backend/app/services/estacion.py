"""Lógica del análisis estacional. No usa la base de datos: recibe días y umbrales y devuelve resultados.

Aquí "periodo" son los últimos 7 o 28 días (no confundir con los bloques de encuestas).
"""
from dataclasses import dataclass
from datetime import date, timedelta

from app.catalogos import TEMPORADAS


@dataclass
class Dia:
    """Promedio de un día (de uno o varios sensores)."""

    fecha: date
    temperatura: float
    humedad: float


def clasificar_estacion(temperatura: float, humedad: float, umbrales: dict) -> str:
    u = umbrales["estacion"]
    if humedad >= u["lluvias_humedad_min"]:
        return "lluvias"
    if temperatura <= u["invierno_temp_max"]:
        return "invierno"
    if temperatura >= u["verano_temp_min"]:
        return "verano"
    return "transicion"


def promedio(dias: list[Dia]) -> tuple[float, float]:
    """(temperatura, humedad) promedio de una lista de días."""
    return (
        sum(d.temperatura for d in dias) / len(dias),
        sum(d.humedad for d in dias) / len(dias),
    )


def _en_rango(dias: list[Dia], desde_excl: date, hasta_incl: date) -> list[Dia]:
    return [d for d in dias if desde_excl < d.fecha <= hasta_incl]


def temporada_proxima(cambio_humedad: float, cambio_temperatura: float, alerta_h: bool, alerta_t: bool) -> str | None:
    # La humedad tiene prioridad porque las lluvias son el riesgo principal en Huánuco
    if alerta_h:
        return "lluvias" if cambio_humedad > 0 else "transicion"
    if alerta_t:
        return "verano" if cambio_temperatura > 0 else "invierno"
    return None


def _num(valor: float, unidad: str) -> str:
    # +12,0 % / −3,5 °C (coma decimal, como se escribe en Perú)
    return f"{valor:+.1f}".replace(".", ",").replace("-", "−") + f" {unidad}"


SIGNIFICADO = {
    "lluvias": "se acerca la temporada de lluvias",
    "invierno": "se acerca el invierno y el riesgo de heladas",
    "verano": "se acerca el verano y la temporada seca",
    "transicion": "está terminando la temporada de lluvias",
}


def construir_mensaje(periodo: int, cambio_h: float, cambio_t: float, alerta_h: bool, alerta_t: bool,
                      temporada: str | None) -> str:
    cuando = "Esta semana" if periodo == 7 else f"En los últimos {periodo} días"
    cambios = []
    if alerta_h:
        cambios.append(f"{'un aumento' if cambio_h > 0 else 'una disminución'} de la humedad ({_num(cambio_h, '%')})")
    if alerta_t:
        cambios.append(f"{'un aumento' if cambio_t > 0 else 'una disminución'} de la temperatura ({_num(cambio_t, '°C')})")
    if not cambios:
        return f"{cuando} no se detectaron cambios relevantes en el clima."
    return f"{cuando} se detectó {' y '.join(cambios)}, y eso significa que {SIGNIFICADO[temporada]}."


def comparar_periodos(dias: list[Dia], periodo: int, hoy: date, umbrales: dict) -> dict:
    """Compara los últimos `periodo` días contra los `periodo` días anteriores."""
    actual = _en_rango(dias, hoy - timedelta(days=periodo), hoy)
    anterior = _en_rango(dias, hoy - timedelta(days=2 * periodo), hoy - timedelta(days=periodo))
    resultado = {"periodo": periodo, "suficientes_datos": bool(actual and anterior)}
    if not resultado["suficientes_datos"]:
        resultado.update(alerta=False, temporada_proxima=None,
                         mensaje=f"Faltan datos para comparar los últimos {periodo} días con los anteriores.")
        return resultado

    t_act, h_act = promedio(actual)
    t_ant, h_ant = promedio(anterior)
    cambio_h, cambio_t = h_act - h_ant, t_act - t_ant
    u = umbrales["cambios"]
    alerta_h = abs(cambio_h) >= u["humedad_puntos"]
    alerta_t = abs(cambio_t) >= u["temperatura_grados"]
    temporada = temporada_proxima(cambio_h, cambio_t, alerta_h, alerta_t)
    resultado.update(
        actual={"temperatura": round(t_act, 1), "humedad": round(h_act, 1), "dias": len(actual)},
        anterior={"temperatura": round(t_ant, 1), "humedad": round(h_ant, 1), "dias": len(anterior)},
        cambio_humedad=round(cambio_h, 1),
        cambio_temperatura=round(cambio_t, 1),
        alerta_humedad=alerta_h,
        alerta_temperatura=alerta_t,
        alerta=alerta_h or alerta_t,
        temporada_proxima=temporada,
        mensaje=construir_mensaje(periodo, cambio_h, cambio_t, alerta_h, alerta_t, temporada),
    )
    return resultado


def diagnosticar(dias: list[Dia], hoy: date, umbrales: dict) -> dict:
    """Estación actual (promedio de N días) + cambios por periodo + temporada próxima."""
    n = umbrales["estacion"]["periodo_dias"]
    recientes = _en_rango(dias, hoy - timedelta(days=n), hoy)
    comparaciones = [comparar_periodos(dias, p, hoy, umbrales) for p in umbrales["cambios"]["periodos_dias"]]

    if recientes:
        temp, hum = promedio(recientes)
        estacion = clasificar_estacion(temp, hum, umbrales)
        promedio_actual = {"temperatura": round(temp, 1), "humedad": round(hum, 1), "dias": len(recientes)}
    else:
        estacion, promedio_actual = None, None

    # La alerta del periodo más corto manda (es la más reciente)
    con_alerta = [c for c in comparaciones if c["alerta"]]
    principal = con_alerta[0] if con_alerta else None
    temporada = principal["temporada_proxima"] if principal else estacion
    if estacion is None:
        mensaje = "No hay registros diarios todavía."
    elif principal:
        mensaje = principal["mensaje"]
    else:
        mensaje = f"Sin cambios relevantes: continúa la estación de {TEMPORADAS[estacion].lower()}."

    return {
        "fecha": hoy.isoformat(),
        "estacion_actual": estacion,
        "estacion_nombre": TEMPORADAS.get(estacion) if estacion else None,
        "promedio": promedio_actual,
        "temporada_proxima": temporada,
        "temporada_nombre": TEMPORADAS.get(temporada) if temporada else None,
        "alerta": bool(principal),
        "mensaje": mensaje,
        "comparaciones": comparaciones,
    }
