import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import 'api.dart';

/// Carga datos del backend y muestra: cargando, error (con reintentar) o el contenido.
/// El contenido se actualiza deslizando hacia abajo.
class Cargador<T> extends StatefulWidget {
  final Future<T> Function() cargar;
  final List<Widget> Function(BuildContext context, T datos) construir;
  final VoidCallback alVencerSesion;

  const Cargador({super.key, required this.cargar, required this.construir, required this.alVencerSesion});

  @override
  State<Cargador<T>> createState() => _CargadorState<T>();
}

class _CargadorState<T> extends State<Cargador<T>> {
  late Future<T> _futuro = widget.cargar();

  Future<void> _refrescar() async {
    setState(() => _futuro = widget.cargar());
    try {
      await _futuro;
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<T>(
      future: _futuro,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final List<Widget> hijos;
        if (snap.hasError) {
          final error = snap.error;
          if (error is ApiError && error.sesionVencida) {
            WidgetsBinding.instance.addPostFrameCallback((_) => widget.alVencerSesion());
          }
          hijos = [
            const SizedBox(height: 48),
            Icon(Icons.cloud_off, size: 56, color: Theme.of(context).colorScheme.error),
            const SizedBox(height: 12),
            Text('$error', textAlign: TextAlign.center),
            const SizedBox(height: 12),
            Center(child: FilledButton.tonal(onPressed: _refrescar, child: const Text('Reintentar'))),
          ];
        } else {
          hijos = widget.construir(context, snap.data as T);
        }
        return RefreshIndicator(
          onRefresh: _refrescar,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(16),
            children: hijos,
          ),
        );
      },
    );
  }
}

/// Gráfico de línea simple de una serie diaria.
class GraficoLinea extends StatelessWidget {
  final String titulo;
  final List<String> fechas; // AAAA-MM-DD
  final List<double> valores;
  final Color color;

  const GraficoLinea({super.key, required this.titulo, required this.fechas, required this.valores, required this.color});

  @override
  Widget build(BuildContext context) {
    final intervalo = (valores.length / 4).ceilToDouble().clamp(1, double.infinity).toDouble();
    return Card(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(8, 16, 16, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(left: 8, bottom: 12),
              child: Text(titulo, style: Theme.of(context).textTheme.titleSmall),
            ),
            SizedBox(
              height: 180,
              child: LineChart(
                LineChartData(
                  gridData: const FlGridData(drawVerticalLine: false),
                  borderData: FlBorderData(show: false),
                  titlesData: FlTitlesData(
                    topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    leftTitles: const AxisTitles(sideTitles: SideTitles(showTitles: true, reservedSize: 36)),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 24,
                        interval: intervalo,
                        getTitlesWidget: (valor, meta) {
                          final i = valor.toInt();
                          if (i != valor || i < 0 || i >= fechas.length) return const SizedBox.shrink();
                          final f = fechas[i];
                          return SideTitleWidget(
                            meta: meta,
                            child: Text('${f.substring(8)}/${f.substring(5, 7)}', style: const TextStyle(fontSize: 10)),
                          );
                        },
                      ),
                    ),
                  ),
                  lineBarsData: [
                    LineChartBarData(
                      spots: [for (var i = 0; i < valores.length; i++) FlSpot(i.toDouble(), valores[i])],
                      isCurved: true,
                      color: color,
                      barWidth: 2.5,
                      dotData: const FlDotData(show: false),
                      belowBarData: BarAreaData(show: true, color: color.withValues(alpha: .12)),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

String conSigno(double v) => '${v >= 0 ? '+' : ''}${v.toStringAsFixed(1)}';
