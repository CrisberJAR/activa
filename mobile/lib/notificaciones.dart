import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Notificaciones locales (sin servicios push externos).
class Notificaciones {
  static final _plugin = FlutterLocalNotificationsPlugin();

  static Future<void> iniciar() async {
    await _plugin.initialize(
      settings: const InitializationSettings(android: AndroidInitializationSettings('@mipmap/ic_launcher')),
    );
    // Android 13+ pide permiso para mostrar notificaciones
    await _plugin
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();
  }

  static Future<void> mostrar(String titulo, String mensaje) => _plugin.show(
        id: 1,
        title: titulo,
        body: mensaje,
        notificationDetails: NotificationDetails(
          android: AndroidNotificationDetails(
            'cambios_clima',
            'Cambios de clima',
            channelDescription: 'Avisos cuando se detecta un cambio de estación',
            importance: Importance.high,
            priority: Priority.high,
            styleInformation: BigTextStyleInformation(mensaje),
          ),
        ),
      );
}
