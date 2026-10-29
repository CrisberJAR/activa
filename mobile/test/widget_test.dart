import 'dart:convert';

import 'package:activa_clima/api.dart';
import 'package:activa_clima/modelos.dart';
import 'package:activa_clima/sesion.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

// Respuesta real de /api/clima/diagnostico con el escenario de lluvias
const diagnosticoJson = '''
{"fecha":"2026-10-28","estacion_actual":"transicion","estacion_nombre":"Transición",
 "promedio":{"temperatura":19.3,"humedad":68.8,"dias":28},"temporada_proxima":"lluvias","temporada_nombre":"Lluvias",
 "alerta":true,"mensaje":"Esta semana se detectó un aumento de la humedad (+10,6 %), y eso significa que se acerca la temporada de lluvias.",
 "comparaciones":[
  {"periodo":7,"suficientes_datos":true,"actual":{"temperatura":18.6,"humedad":80.9,"dias":7},
   "anterior":{"temperatura":19.0,"humedad":70.3,"dias":7},"cambio_humedad":10.6,"cambio_temperatura":-0.4,
   "alerta_humedad":true,"alerta_temperatura":false,"alerta":true,"temporada_proxima":"lluvias","mensaje":"..."},
  {"periodo":28,"suficientes_datos":false,"alerta":false,"temporada_proxima":null,"mensaje":"Faltan datos"}
 ]}
''';

void main() {
  group('Modelos', () {
    test('lee el diagnóstico del backend', () {
      final d = Diagnostico.fromJson(jsonDecode(diagnosticoJson));
      expect(d.estacionNombre, 'Transición');
      expect(d.temporadaNombre, 'Lluvias');
      expect(d.promedio!.humedad, 68.8);
      expect(d.comparaciones.first.cambioHumedad, 10.6);
      expect(d.comparaciones.first.temporadaNombre, 'Lluvias');
      expect(d.comparaciones.last.suficientesDatos, isFalse);
      expect(d.comparaciones.last.actual, isNull);
    });

    test('lee números enteros como decimales', () {
      final r = RegistroDiario.fromJson({
        'fecha': '2026-10-28', 'temperatura': 20, 'humedad': 70, 'temp_min': 15, 'temp_max': 25,
        'humedad_min': 60, 'humedad_max': 80, 'n_lecturas': 6,
      });
      expect(r.temperatura, 20.0);
    });
  });

  group('Cuándo notificar', () {
    final conAlerta = Diagnostico.fromJson(jsonDecode(diagnosticoJson));
    final sinAlerta = Diagnostico(alerta: false, mensaje: 'Sin cambios', comparaciones: []);

    test('notifica una alerta nueva', () => expect(debeNotificar(conAlerta, null), isTrue));
    test('no repite la misma alerta', () => expect(debeNotificar(conAlerta, conAlerta.mensaje), isFalse));
    test('notifica si el mensaje cambió', () => expect(debeNotificar(conAlerta, 'otro aviso'), isTrue));
    test('no notifica sin alerta', () => expect(debeNotificar(sinAlerta, null), isFalse));
  });

  group('Dirección del servidor', () {
    test('agrega http y puerto 8000', () => expect(normalizarServidor('192.168.43.20'), 'http://192.168.43.20:8000'));
    test('quita la barra final', () => expect(normalizarServidor(' http://10.0.0.5:8000/ '), 'http://10.0.0.5:8000'));
    test('respeta https sin puerto', () => expect(normalizarServidor('https://activa.onrender.com'), 'https://activa.onrender.com'));
  });

  group('Api', () {
    test('envía el token y el sensor elegido', () async {
      late http.Request recibida;
      final cliente = MockClient((req) async {
        recibida = req;
        return http.Response(diagnosticoJson, 200, headers: {'content-type': 'application/json; charset=utf-8'});
      });
      final sesion = Sesion()
        ..servidor = 'http://pc:8000'
        ..token = 'abc'
        ..sensor = 'sim-huanuco-01';
      final d = await Api(sesion, cliente: cliente).diagnostico();
      expect(d.alerta, isTrue);
      expect(recibida.headers['Authorization'], 'Bearer abc');
      expect(recibida.url.toString(), 'http://pc:8000/api/clima/diagnostico?sensor=sim-huanuco-01');
    });

    test('401 avisa que la sesión venció', () async {
      final sesion = Sesion()..token = 'viejo';
      final api = Api(sesion, cliente: MockClient((_) async => http.Response('{"detail":"x"}', 401)));
      expect(api.diagnostico(), throwsA(isA<ApiError>().having((e) => e.sesionVencida, 'sesionVencida', isTrue)));
    });

    test('sin conexión da un mensaje entendible', () async {
      final api = Api(Sesion(), cliente: MockClient((_) async => throw http.ClientException('sin red')));
      expect(api.registros(28), throwsA(isA<ApiError>().having((e) => e.mensaje, 'mensaje', contains('No se pudo conectar'))));
    });
  });
}
