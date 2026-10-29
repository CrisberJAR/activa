import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'modelos.dart';
import 'sesion.dart';

class ApiError implements Exception {
  final String mensaje;
  final bool sesionVencida;

  ApiError(this.mensaje, {this.sesionVencida = false});

  @override
  String toString() => mensaje;
}

/// Conexión con el backend FastAPI. La app nunca habla con Firebase directamente.
class Api {
  final Sesion sesion;
  final http.Client _cliente;
  static const _espera = Duration(seconds: 15);

  Api(this.sesion, {http.Client? cliente}) : _cliente = cliente ?? http.Client();

  Uri _uri(String ruta, [Map<String, String>? parametros]) {
    final q = {...?parametros};
    if (sesion.sensor != null) q['sensor'] = sesion.sensor!;
    return Uri.parse('${sesion.servidor}$ruta').replace(queryParameters: q.isEmpty ? null : q);
  }

  static String _sinConexion(String servidor) =>
      'No se pudo conectar con $servidor.\nRevisa que el servidor esté encendido, '
      'que el celular esté en la misma red y la dirección en Ajustes.';

  static String _detalle(http.Response r) {
    try {
      return (jsonDecode(utf8.decode(r.bodyBytes)) as Map)['detail'].toString();
    } catch (_) {
      return 'El servidor respondió con error ${r.statusCode}';
    }
  }

  Future<dynamic> _get(String ruta, [Map<String, String>? parametros]) async {
    final http.Response r;
    try {
      r = await _cliente
          .get(_uri(ruta, parametros), headers: {'Authorization': 'Bearer ${sesion.token}'})
          .timeout(_espera);
    } on TimeoutException {
      throw ApiError(_sinConexion(sesion.servidor));
    } catch (_) {
      throw ApiError(_sinConexion(sesion.servidor));
    }
    if (r.statusCode == 401) {
      throw ApiError('Tu sesión venció. Vuelve a iniciar sesión.', sesionVencida: true);
    }
    if (r.statusCode != 200) throw ApiError(_detalle(r));
    return jsonDecode(utf8.decode(r.bodyBytes));
  }

  /// Devuelve null si el servidor responde y su base de datos está conectada; si no, el problema.
  static Future<String?> probarConexion(String servidor, {http.Client? cliente}) async {
    final url = normalizarServidor(servidor);
    try {
      final r = await (cliente ?? http.Client()).get(Uri.parse('$url/api/salud')).timeout(_espera);
      if (r.statusCode == 200) return null;
      return 'El servidor responde, pero la base de datos no está conectada (${r.statusCode}).';
    } catch (_) {
      return _sinConexion(url);
    }
  }

  /// Inicia sesión y devuelve (token, nombre).
  Future<(String, String)> iniciarSesion(String email, String password) async {
    final http.Response r;
    try {
      r = await _cliente.post(
        Uri.parse('${sesion.servidor}/api/auth/token'),
        body: {'username': email.trim(), 'password': password},
      ).timeout(_espera);
    } catch (_) {
      throw ApiError(_sinConexion(sesion.servidor));
    }
    if (r.statusCode == 401) throw ApiError('Correo o contraseña incorrectos');
    if (r.statusCode != 200) throw ApiError(_detalle(r));
    final token = (jsonDecode(r.body) as Map)['access_token'] as String;
    sesion.token = token;
    final yo = await _get('/api/auth/yo') as Map;
    return (token, yo['nombre'] as String);
  }

  Future<Diagnostico> diagnostico() async =>
      Diagnostico.fromJson(await _get('/api/clima/diagnostico') as Map<String, dynamic>);

  Future<List<Lectura>> ultimas() async =>
      [for (final j in await _get('/api/clima/ultima') as List) Lectura.fromJson(j)];

  Future<List<RegistroDiario>> registros(int dias) async =>
      [for (final j in await _get('/api/clima/registros', {'dias': '$dias'}) as List) RegistroDiario.fromJson(j)];

  Future<Comparacion> analisis(int periodo) async =>
      Comparacion.fromJson(await _get('/api/clima/analisis', {'periodo': '$periodo'}) as Map<String, dynamic>);

  Future<List<Sensor>> sensores() async =>
      [for (final j in await _get('/api/clima/sensores') as List) Sensor.fromJson(j)];
}
