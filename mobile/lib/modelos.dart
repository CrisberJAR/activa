// Datos que llegan del backend (/api/clima/...).

const nombresTemporada = {
  'lluvias': 'Lluvias',
  'invierno': 'Invierno',
  'verano': 'Verano',
  'transicion': 'Transición',
};

double _num(dynamic v) => (v as num).toDouble();

class Lectura {
  final String sensor;
  final String? sector;
  final double temperatura;
  final double humedad;
  final DateTime? hora;

  Lectura({required this.sensor, this.sector, required this.temperatura, required this.humedad, this.hora});

  factory Lectura.fromJson(Map<String, dynamic> j) => Lectura(
        sensor: j['sensor'] as String,
        sector: j['sector'] as String?,
        temperatura: _num(j['temperatura']),
        humedad: _num(j['humedad']),
        hora: j['hora'] == null ? null : DateTime.parse(j['hora'] as String).toLocal(),
      );
}

class RegistroDiario {
  final String fecha; // AAAA-MM-DD
  final double temperatura;
  final double humedad;
  final double tempMin;
  final double tempMax;
  final double humedadMin;
  final double humedadMax;
  final int lecturas;

  RegistroDiario({
    required this.fecha,
    required this.temperatura,
    required this.humedad,
    required this.tempMin,
    required this.tempMax,
    required this.humedadMin,
    required this.humedadMax,
    required this.lecturas,
  });

  factory RegistroDiario.fromJson(Map<String, dynamic> j) => RegistroDiario(
        fecha: j['fecha'] as String,
        temperatura: _num(j['temperatura']),
        humedad: _num(j['humedad']),
        tempMin: _num(j['temp_min']),
        tempMax: _num(j['temp_max']),
        humedadMin: _num(j['humedad_min']),
        humedadMax: _num(j['humedad_max']),
        lecturas: j['n_lecturas'] as int,
      );
}

class Promedio {
  final double temperatura;
  final double humedad;
  final int dias;

  Promedio(this.temperatura, this.humedad, this.dias);

  factory Promedio.fromJson(Map<String, dynamic> j) =>
      Promedio(_num(j['temperatura']), _num(j['humedad']), j['dias'] as int);
}

/// Comparación de los últimos N días contra los N anteriores.
class Comparacion {
  final int periodo;
  final bool suficientesDatos;
  final Promedio? actual;
  final Promedio? anterior;
  final double? cambioHumedad;
  final double? cambioTemperatura;
  final bool alertaHumedad;
  final bool alertaTemperatura;
  final bool alerta;
  final String? temporadaProxima;
  final String mensaje;

  Comparacion({
    required this.periodo,
    required this.suficientesDatos,
    this.actual,
    this.anterior,
    this.cambioHumedad,
    this.cambioTemperatura,
    this.alertaHumedad = false,
    this.alertaTemperatura = false,
    required this.alerta,
    this.temporadaProxima,
    required this.mensaje,
  });

  String? get temporadaNombre => nombresTemporada[temporadaProxima];

  factory Comparacion.fromJson(Map<String, dynamic> j) => Comparacion(
        periodo: j['periodo'] as int,
        suficientesDatos: j['suficientes_datos'] as bool,
        actual: j['actual'] == null ? null : Promedio.fromJson(j['actual']),
        anterior: j['anterior'] == null ? null : Promedio.fromJson(j['anterior']),
        cambioHumedad: j['cambio_humedad'] == null ? null : _num(j['cambio_humedad']),
        cambioTemperatura: j['cambio_temperatura'] == null ? null : _num(j['cambio_temperatura']),
        alertaHumedad: j['alerta_humedad'] as bool? ?? false,
        alertaTemperatura: j['alerta_temperatura'] as bool? ?? false,
        alerta: j['alerta'] as bool,
        temporadaProxima: j['temporada_proxima'] as String?,
        mensaje: j['mensaje'] as String,
      );
}

class Diagnostico {
  final String? estacionNombre;
  final Promedio? promedio;
  final String? temporadaNombre;
  final bool alerta;
  final String mensaje;
  final List<Comparacion> comparaciones;

  Diagnostico({
    this.estacionNombre,
    this.promedio,
    this.temporadaNombre,
    required this.alerta,
    required this.mensaje,
    required this.comparaciones,
  });

  factory Diagnostico.fromJson(Map<String, dynamic> j) => Diagnostico(
        estacionNombre: j['estacion_nombre'] as String?,
        promedio: j['promedio'] == null ? null : Promedio.fromJson(j['promedio']),
        temporadaNombre: j['temporada_nombre'] as String?,
        alerta: j['alerta'] as bool,
        mensaje: j['mensaje'] as String,
        comparaciones: [for (final c in j['comparaciones'] as List) Comparacion.fromJson(c)],
      );
}

class Sensor {
  final String codigo;
  final String sector;

  Sensor(this.codigo, this.sector);

  factory Sensor.fromJson(Map<String, dynamic> j) => Sensor(j['codigo'] as String, j['sector'] as String);
}

/// Se notifica solo si hay alerta y el mensaje es distinto al último notificado (no repetir avisos).
bool debeNotificar(Diagnostico d, String? ultimoMensajeNotificado) =>
    d.alerta && d.mensaje != ultimoMensajeNotificado;
