import 'package:flutter/material.dart';

import '../api.dart';
import '../modelos.dart';
import '../notificaciones.dart';
import '../sesion.dart';

/// Servidor, sensor elegido, prueba de notificación y cierre de sesión.
/// Devuelve true al cerrar si el usuario eligió "Cerrar sesión".
class AjustesPantalla extends StatefulWidget {
  final Sesion sesion;
  final Api api;

  const AjustesPantalla({super.key, required this.sesion, required this.api});

  @override
  State<AjustesPantalla> createState() => _AjustesPantallaState();
}

class _AjustesPantallaState extends State<AjustesPantalla> {
  late final _servidor = TextEditingController(text: widget.sesion.servidor);
  late final Future<List<Sensor>> _sensores = widget.api.sensores();
  String? _estado;

  void _avisar(String texto) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(texto)));

  Future<void> _guardarServidor() async {
    setState(() => _estado = 'Probando…');
    final problema = await Api.probarConexion(_servidor.text);
    if (!mounted) return;
    if (problema != null) {
      setState(() => _estado = problema);
      return;
    }
    await widget.sesion.guardarServidor(_servidor.text);
    setState(() {
      _servidor.text = widget.sesion.servidor;
      _estado = 'Conexión correcta ✔ Servidor guardado.';
    });
  }

  Future<void> _probarNotificacion() async {
    try {
      final d = await widget.api.diagnostico();
      await Notificaciones.mostrar('Cambio de clima: se acerca ${d.temporadaNombre ?? ''}', d.mensaje);
      await widget.sesion.guardarUltimoAviso(d.mensaje);
    } on ApiError catch (e) {
      _avisar(e.mensaje);
    }
  }

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Ajustes')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (widget.sesion.nombre != null)
            ListTile(leading: const Icon(Icons.person), title: Text(widget.sesion.nombre!)),
          const Divider(),
          Text('Servidor', style: tema.textTheme.titleMedium),
          const SizedBox(height: 8),
          TextField(
            controller: _servidor,
            keyboardType: TextInputType.url,
            decoration: const InputDecoration(
              labelText: 'Dirección del servidor',
              hintText: '192.168.18.14:8000',
              helperText: 'La que muestra iniciar_servidor.ps1 en la laptop',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 8),
          FilledButton.tonal(onPressed: _guardarServidor, child: const Text('Probar y guardar')),
          if (_estado != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_estado!)),
          const Divider(height: 32),
          Text('Sensor', style: tema.textTheme.titleMedium),
          FutureBuilder<List<Sensor>>(
            future: _sensores,
            builder: (context, snap) {
              if (snap.hasError) return Text('${snap.error}');
              if (!snap.hasData) return const LinearProgressIndicator();
              final opciones = <String?>[null, ...snap.data!.map((s) => s.codigo)];
              return RadioGroup<String?>(
                groupValue: widget.sesion.sensor,
                onChanged: (valor) async {
                  await widget.sesion.guardarSensor(valor);
                  setState(() {});
                },
                child: Column(
                  children: [
                    for (final codigo in opciones)
                      RadioListTile<String?>(
                        value: codigo,
                        title: Text(codigo ?? 'Todos los sensores (promedio)'),
                      ),
                  ],
                ),
              );
            },
          ),
          const Divider(height: 32),
          ListTile(
            leading: const Icon(Icons.notifications_active),
            title: const Text('Probar notificación'),
            subtitle: const Text('Muestra ahora el aviso del diagnóstico actual'),
            onTap: _probarNotificacion,
          ),
          ListTile(
            leading: Icon(Icons.logout, color: tema.colorScheme.error),
            title: const Text('Cerrar sesión'),
            onTap: () => Navigator.of(context).pop(true),
          ),
        ],
      ),
    );
  }
}
