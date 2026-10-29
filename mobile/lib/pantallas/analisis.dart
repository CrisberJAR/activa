import 'package:flutter/material.dart';

import '../api.dart';
import '../modelos.dart';
import '../widgets.dart';

/// Compara la última semana (o mes) contra la anterior y muestra la temporada probable.
class AnalisisPantalla extends StatefulWidget {
  final Api api;
  final VoidCallback alVencerSesion;

  const AnalisisPantalla({super.key, required this.api, required this.alVencerSesion});

  @override
  State<AnalisisPantalla> createState() => _AnalisisPantallaState();
}

class _AnalisisPantallaState extends State<AnalisisPantalla> {
  int _periodo = 7;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
          child: SegmentedButton<int>(
            segments: const [
              ButtonSegment(value: 7, label: Text('Semana'), icon: Icon(Icons.view_week)),
              ButtonSegment(value: 28, label: Text('Mes'), icon: Icon(Icons.calendar_month)),
            ],
            selected: {_periodo},
            onSelectionChanged: (s) => setState(() => _periodo = s.first),
          ),
        ),
        Expanded(
          child: Cargador<Comparacion>(
            key: ValueKey(_periodo),
            cargar: () => widget.api.analisis(_periodo),
            alVencerSesion: widget.alVencerSesion,
            construir: (context, c) => _contenido(context, c),
          ),
        ),
      ],
    );
  }

  List<Widget> _contenido(BuildContext context, Comparacion c) {
    final tema = Theme.of(context);
    if (!c.suficientesDatos) {
      return [Card(child: ListTile(leading: const Icon(Icons.info_outline), title: Text(c.mensaje)))];
    }
    final nombre = _periodo == 7 ? 'semana' : 'mes';
    TextStyle? resaltar(bool alerta) =>
        alerta ? TextStyle(color: tema.colorScheme.error, fontWeight: FontWeight.bold) : null;
    return [
      Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: DataTable(
            columnSpacing: 20,
            columns: [
              const DataColumn(label: Text('')),
              DataColumn(label: Text('Este $nombre')),
              DataColumn(label: Text('Anterior')),
              const DataColumn(label: Text('Cambio')),
            ],
            rows: [
              DataRow(cells: [
                const DataCell(Text('Temp.')),
                DataCell(Text('${c.actual!.temperatura} °C')),
                DataCell(Text('${c.anterior!.temperatura} °C')),
                DataCell(Text('${conSigno(c.cambioTemperatura!)} °C', style: resaltar(c.alertaTemperatura))),
              ]),
              DataRow(cells: [
                const DataCell(Text('Humedad')),
                DataCell(Text('${c.actual!.humedad} %')),
                DataCell(Text('${c.anterior!.humedad} %')),
                DataCell(Text('${conSigno(c.cambioHumedad!)} %', style: resaltar(c.alertaHumedad))),
              ]),
            ],
          ),
        ),
      ),
      const SizedBox(height: 8),
      Card(
        color: c.alerta ? Colors.amber.shade100 : null,
        child: ListTile(
          leading: Icon(c.alerta ? Icons.warning_amber_rounded : Icons.check_circle_outline, size: 36,
              color: c.alerta ? Colors.orange.shade800 : tema.colorScheme.primary),
          title: Text(c.alerta ? 'Temporada probable: ${c.temporadaNombre}' : 'Sin cambio de temporada'),
          subtitle: Padding(padding: const EdgeInsets.only(top: 4), child: Text(c.mensaje)),
        ),
      ),
    ];
  }
}
