import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../api.dart';
import '../modelos.dart';
import '../widgets.dart';

/// Lectura actual, estación actual, temporada que se acerca y mensaje del diagnóstico.
class HoyPantalla extends StatelessWidget {
  final Api api;
  final VoidCallback alVencerSesion;

  const HoyPantalla({super.key, required this.api, required this.alVencerSesion});

  Future<(Diagnostico, List<Lectura>)> _cargar() async {
    final datos = await Future.wait([api.diagnostico(), api.ultimas()]);
    return (datos[0] as Diagnostico, datos[1] as List<Lectura>);
  }

  @override
  Widget build(BuildContext context) {
    return Cargador<(Diagnostico, List<Lectura>)>(
      cargar: _cargar,
      alVencerSesion: alVencerSesion,
      construir: (context, datos) {
        final (diag, lecturas) = datos;
        final tema = Theme.of(context);
        if (diag.estacionNombre == null) {
          return [const Card(child: ListTile(leading: Icon(Icons.info_outline), title: Text('Todavía no hay registros de clima.')))];
        }
        return [
          Card(
            color: tema.colorScheme.primaryContainer,
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  Text('Estación actual', style: tema.textTheme.labelLarge),
                  const SizedBox(height: 4),
                  Text(diag.estacionNombre!, style: tema.textTheme.displaySmall),
                  if (diag.promedio != null)
                    Text('${diag.promedio!.temperatura} °C · ${diag.promedio!.humedad} % '
                        '(promedio ${diag.promedio!.dias} días)'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          Card(
            color: diag.alerta ? Colors.amber.shade100 : null,
            child: ListTile(
              leading: Icon(diag.alerta ? Icons.warning_amber_rounded : Icons.check_circle_outline,
                  color: diag.alerta ? Colors.orange.shade800 : tema.colorScheme.primary, size: 36),
              title: Text('Temporada que se acerca: ${diag.temporadaNombre ?? '-'}'),
              subtitle: Padding(padding: const EdgeInsets.only(top: 4), child: Text(diag.mensaje)),
            ),
          ),
          const SizedBox(height: 16),
          Text('Lectura en vivo', style: tema.textTheme.titleMedium),
          if (lecturas.isEmpty) const ListTile(title: Text('Sin lecturas de sensores.')),
          for (final l in lecturas)
            Card(
              child: ListTile(
                leading: const Icon(Icons.sensors),
                title: Text('${l.temperatura.toStringAsFixed(1)} °C   ·   ${l.humedad.toStringAsFixed(1)} %'),
                subtitle: Text('${l.sensor}'
                    '${l.hora != null ? '\n${DateFormat('dd/MM/yyyy HH:mm').format(l.hora!)}' : ''}'),
                isThreeLine: l.hora != null,
              ),
            ),
        ];
      },
    );
  }
}
