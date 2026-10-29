import 'package:flutter/material.dart';

import 'notificaciones.dart';
import 'pantallas/inicio.dart';
import 'pantallas/login.dart';
import 'sesion.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final sesion = Sesion();
  await sesion.cargar();
  await Notificaciones.iniciar();
  runApp(ActivaApp(sesion: sesion));
}

class ActivaApp extends StatelessWidget {
  final Sesion sesion;

  const ActivaApp({super.key, required this.sesion});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ACTIVA Clima',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF0B5D3B))),
      home: sesion.token == null ? LoginPantalla(sesion: sesion) : InicioPantalla(sesion: sesion),
    );
  }
}
