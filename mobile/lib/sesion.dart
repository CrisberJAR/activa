import 'package:shared_preferences/shared_preferences.dart';

/// Dirección del backend por defecto (la PC en la red local). Se cambia en Ajustes.
const servidorPorDefecto = 'http://192.168.18.14:8000';

/// Acepta "192.168.1.5", "192.168.1.5:8000/" o "http://..." y lo deja como "http://192.168.1.5:8000".
String normalizarServidor(String texto) {
  var url = texto.trim();
  if (!url.startsWith('http://') && !url.startsWith('https://')) url = 'http://$url';
  var uri = Uri.parse(url);
  if (uri.scheme == 'http' && !uri.hasPort) uri = uri.replace(port: 8000);
  url = uri.toString();
  while (url.endsWith('/')) {
    url = url.substring(0, url.length - 1);
  }
  return url;
}

/// Datos que la app recuerda entre usos: servidor, token, sensor elegido y último aviso.
class Sesion {
  late SharedPreferences _prefs;

  String servidor = servidorPorDefecto;
  String? token;
  String? nombre;
  String? sensor; // null = todos los sensores
  String? ultimoAviso;

  Future<void> cargar() async {
    _prefs = await SharedPreferences.getInstance();
    servidor = _prefs.getString('servidor') ?? servidorPorDefecto;
    token = _prefs.getString('token');
    nombre = _prefs.getString('nombre');
    sensor = _prefs.getString('sensor');
    ultimoAviso = _prefs.getString('ultimo_aviso');
  }

  Future<void> _guardar(String clave, String? valor) =>
      valor == null ? _prefs.remove(clave) : _prefs.setString(clave, valor);

  Future<void> guardarServidor(String url) async {
    servidor = normalizarServidor(url);
    await _guardar('servidor', servidor);
  }

  Future<void> iniciar(String nuevoToken, String nuevoNombre) async {
    token = nuevoToken;
    nombre = nuevoNombre;
    await _guardar('token', token);
    await _guardar('nombre', nombre);
  }

  Future<void> cerrar() async {
    token = null;
    nombre = null;
    await _guardar('token', null);
    await _guardar('nombre', null);
  }

  Future<void> guardarSensor(String? codigo) async {
    sensor = codigo;
    await _guardar('sensor', codigo);
  }

  Future<void> guardarUltimoAviso(String? mensaje) async {
    ultimoAviso = mensaje;
    await _guardar('ultimo_aviso', mensaje);
  }
}
