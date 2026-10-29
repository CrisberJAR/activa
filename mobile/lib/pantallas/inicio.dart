import 'dart:async';

import 'package:flutter/material.dart';

import '../api.dart';
import '../modelos.dart';
import '../notificaciones.dart';
import '../sesion.dart';
import 'ajustes.dart';
import 'analisis.dart';
import 'hoy.dart';
import 'login.dart';
import 'registros.dart';

/// Pantalla principal con las pestañas Hoy, Registros y Análisis.
/// También revisa el diagnóstico para notificar cambios de clima.
class InicioPantalla extends StatefulWidget {
  final Sesion sesion;

  const InicioPantalla({super.key, required this.sesion});

  @override
  State<InicioPantalla> createState() => _InicioPantallaState();
}

class _InicioPantallaState extends State<InicioPantalla> with WidgetsBindingObserver {
  late final api = Api(widget.sesion);
  int _pestana = 0;
  int _version = 0; // cambia al volver de Ajustes para recargar los datos
  Timer? _revision;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _revisarAlertas();
    _revision = Timer.periodic(const Duration(minutes: 15), (_) => _revisarAlertas());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _revision?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _revisarAlertas();
  }

  Future<void> _revisarAlertas() async {
    try {
      final d = await api.diagnostico();
      if (debeNotificar(d, widget.sesion.ultimoAviso)) {
        await Notificaciones.mostrar('Cambio de clima: se acerca ${d.temporadaNombre ?? ''}', d.mensaje);
        await widget.sesion.guardarUltimoAviso(d.mensaje);
      }
    } catch (_) {
      // Sin conexión: se vuelve a intentar en la siguiente revisión
    }
  }

  Future<void> _cerrarSesion() async {
    await widget.sesion.cerrar();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => LoginPantalla(sesion: widget.sesion)),
      (_) => false,
    );
  }

  Future<void> _abrirAjustes() async {
    final cerrar = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => AjustesPantalla(sesion: widget.sesion, api: api)),
    );
    if (cerrar == true) return _cerrarSesion();
    setState(() => _version++);
  }

  @override
  Widget build(BuildContext context) {
    final clave = ValueKey('${widget.sesion.sensor}-$_version');
    final pestanas = [
      HoyPantalla(key: clave, api: api, alVencerSesion: _cerrarSesion),
      RegistrosPantalla(key: clave, api: api, alVencerSesion: _cerrarSesion),
      AnalisisPantalla(key: clave, api: api, alVencerSesion: _cerrarSesion),
    ];
    return Scaffold(
      appBar: AppBar(
        title: const Text('ACTIVA Clima'),
        actions: [IconButton(icon: const Icon(Icons.settings), tooltip: 'Ajustes', onPressed: _abrirAjustes)],
        bottom: widget.sesion.sensor == null
            ? null
            : PreferredSize(
                preferredSize: const Size.fromHeight(20),
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text('Sensor: ${widget.sesion.sensor}', style: Theme.of(context).textTheme.bodySmall),
                ),
              ),
      ),
      body: IndexedStack(index: _pestana, children: pestanas),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _pestana,
        onDestinationSelected: (i) => setState(() => _pestana = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.wb_sunny_outlined), selectedIcon: Icon(Icons.wb_sunny), label: 'Hoy'),
          NavigationDestination(icon: Icon(Icons.list_alt), label: 'Registros'),
          NavigationDestination(icon: Icon(Icons.analytics_outlined), selectedIcon: Icon(Icons.analytics), label: 'Análisis'),
        ],
      ),
    );
  }
}
