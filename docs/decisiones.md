# Registro de decisiones

| Fecha | Decisión | Motivo |
| --- | --- | --- |
| 2026-10-28 | PostgreSQL en **Supabase** en lugar de Docker o PostgreSQL local | Costo cero, sin instalar nada extra, mismo motor en desarrollo y en la sustentación |
| 2026-10-28 | Autenticación propia del backend (bcrypt + sesión firmada + JWT), no Supabase Auth | Más simple de explicar; Supabase se usa solo como base de datos |
| 2026-10-28 | Esquema gestionado con migraciones Alembic | Cada cambio de tablas queda versionado y se aplica igual en cualquier base |
| 2026-10-28 | Pruebas automáticas con SQLite en memoria | No dependen de internet ni de que Supabase esté activo |
| 2026-10-28 | Python 3.13 (la guía indicaba 3.11) | Ya estaba instalado y todas las librerías lo soportan |
| 2026-10-28 | Conexión por *Session pooler* de Supabase | La conexión directa es solo IPv6 y no funciona en la red del autor |
| 2026-10-28 | Varios bloques abiertos a la vez; el asesor elige el bloque en cada encuesta | Un asesor trabaja en varios bloques en paralelo (pedido del usuario) |
| 2026-10-28 | Solo el gerente crea, abre y cierra bloques; el asesor solo los consulta | La planificación de las salidas de campo es responsabilidad de la gerencia (pedido del usuario) |
| 2026-10-28 | El ESP32 envía cada 30 s y se detiene solo tras 20 envíos (10 min) | Demo simple sin agotar el plan gratuito de Firebase (pedido del usuario) |
| 2026-10-28 | La hora de cada lectura la pone el servidor de Firebase | No depende del reloj del dispositivo |
| 2026-10-28 | Reglas de Firebase: escritura validada para sensores, lectura solo con secreto del backend | El sketch no lleva claves; los datos no quedan públicos |
| 2026-10-28 | Consolidación automática cada hora (APScheduler) + botón manual del gerente | Sin servicios extra; el gerente puede actualizar antes de una demo |
| 2026-10-28 | Los días se agrupan en hora de Perú (UTC−5) | Una lectura de las 22:00 pertenece a ese día, no al siguiente (UTC) |
| 2026-10-28 | El análisis promedia todos los sensores, con filtro por sensor | Los sensores representan el clima de la zona |
| 2026-10-28 | Si sube la humedad se anuncia Lluvias antes que cualquier cambio de temperatura | Las lluvias son el riesgo climático principal para los clientes de Huánuco |
| 2026-10-28 | Datos de 8 semanas simulados directo en Supabase (sensor `sim-...`) | Probar el análisis sin esperar semanas ni gastar el plan de Firebase; se declara como limitación |
| 2026-10-28 | La dirección del servidor se configura dentro de la app | En la sustentación puede usarse otra laptop y la red compartida del celular |
| 2026-10-28 | Notificación local al abrir la app, al volver a ella y cada 15 min; solo si la alerta es nueva | Cumple la guía sin servicios push ni tareas en segundo plano; no repite avisos |
| 2026-10-28 | La app consume solo la API del backend con token JWT | Las claves de Firebase y Supabase nunca llegan al celular |
| 2026-10-28 | Encuestas editables solo por quien las registró o por el gerente | Corregir errores de campo sin perder el control de quién modifica los datos |
| 2026-10-28 | Validación en el servidor con Pydantic, además del navegador | El navegador se puede saltar; la regla del consentimiento (Ley 29733) debe ser infalible |
