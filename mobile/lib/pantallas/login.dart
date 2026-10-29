import 'package:flutter/material.dart';

import '../api.dart';
import '../sesion.dart';
import 'inicio.dart';

class LoginPantalla extends StatefulWidget {
  final Sesion sesion;

  const LoginPantalla({super.key, required this.sesion});

  @override
  State<LoginPantalla> createState() => _LoginPantallaState();
}

class _LoginPantallaState extends State<LoginPantalla> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  late final _servidor = TextEditingController(text: widget.sesion.servidor);
  bool _cargando = false;
  String? _error;
  String? _estadoConexion;

  Future<void> _probar() async {
    setState(() => _estadoConexion = 'Probando…');
    final problema = await Api.probarConexion(_servidor.text);
    if (mounted) setState(() => _estadoConexion = problema ?? 'Conexión correcta ✔');
  }

  Future<void> _ingresar() async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      await widget.sesion.guardarServidor(_servidor.text);
      final (token, nombre) = await Api(widget.sesion).iniciarSesion(_email.text, _password.text);
      await widget.sesion.iniciar(token, nombre);
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => InicioPantalla(sesion: widget.sesion)),
      );
    } on ApiError catch (e) {
      setState(() => _error = e.mensaje);
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final tema = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            const SizedBox(height: 32),
            Icon(Icons.cloud_sync, size: 64, color: tema.colorScheme.primary),
            const SizedBox(height: 8),
            Text('ACTIVA Clima', textAlign: TextAlign.center, style: tema.textTheme.headlineSmall),
            Text('Diagnóstico estacional IoT', textAlign: TextAlign.center, style: tema.textTheme.bodyMedium),
            const SizedBox(height: 32),
            TextField(
              controller: _email,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(labelText: 'Correo', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _password,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Contraseña', border: OutlineInputBorder()),
              onSubmitted: (_) => _ingresar(),
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!, style: TextStyle(color: tema.colorScheme.error)),
            ],
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _cargando ? null : _ingresar,
              child: _cargando
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Ingresar'),
            ),
            const SizedBox(height: 16),
            ExpansionTile(
              title: const Text('Servidor'),
              subtitle: Text(widget.sesion.servidor, style: tema.textTheme.bodySmall),
              childrenPadding: const EdgeInsets.only(bottom: 8),
              children: [
                TextField(
                  controller: _servidor,
                  keyboardType: TextInputType.url,
                  decoration: const InputDecoration(
                    labelText: 'Dirección del servidor',
                    hintText: '192.168.18.14:8000',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    OutlinedButton(onPressed: _probar, child: const Text('Probar conexión')),
                    const SizedBox(width: 12),
                    if (_estadoConexion != null) Expanded(child: Text(_estadoConexion!, style: tema.textTheme.bodySmall)),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
