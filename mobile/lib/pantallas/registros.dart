import 'package:flutter/material.dart';

import '../api.dart';
import '../modelos.dart';
import '../widgets.dart';

/// Registros diarios de las últimas 4 semanas: gráficos y lista día por día.
class RegistrosPantalla extends StatelessWidget {
  final Api api;
  final VoidCallback alVencerSesion;

  const RegistrosPantalla({super.key, required this.api, required this.alVencerSesion});

  @override
  Widget build(BuildContext context) {
    return Cargador<List<RegistroDiario>>(
      cargar: () => api.registros(28),
      alVencerSesion: alVencerSesion,
      construir: (context, registros) {
        if (registros.isEmpty) {
          return [const Card(child: ListTile(leading: Icon(Icons.info_outline), title: Text('Sin registros diarios.')))];
        }
        final fechas = [for (final r in registros) r.fecha];
        return [
          GraficoLinea(
            titulo: 'Temperatura promedio (°C)',
            fechas: fechas,
            valores: [for (final r in registros) r.temperatura],
            color: Colors.deepOrange,
          ),
          GraficoLinea(
            titulo: 'Humedad promedio (%)',
            fechas: fechas,
            valores: [for (final r in registros) r.humedad],
            color: Colors.blue,
          ),
          const SizedBox(height: 8),
          for (final r in registros.reversed)
            Card(
              child: ListTile(
                dense: true,
                title: Text('${r.fecha.substring(8)}/${r.fecha.substring(5, 7)}/${r.fecha.substring(0, 4)}'),
                subtitle: Text('Temp. ${r.tempMin.toStringAsFixed(1)} – ${r.tempMax.toStringAsFixed(1)} °C · '
                    'Hum. ${r.humedadMin.toStringAsFixed(0)} – ${r.humedadMax.toStringAsFixed(0)} %'),
                trailing: Text('${r.temperatura.toStringAsFixed(1)} °C\n${r.humedad.toStringAsFixed(1)} %',
                    textAlign: TextAlign.right),
              ),
            ),
        ];
      },
    );
  }
}
