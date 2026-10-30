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
| 2026-10-29 | Necesidades clasificadas por palabras clave (`config/necesidades.yaml`), no por la IA | Resultado repetible, fácil de probar y de explicar; las palabras se ajustan sin tocar código |
| 2026-10-29 | A Gemini solo van cifras agregadas y textos de necesidad anonimizados (sin nombres, teléfonos ni correos) | Ley 29733 y regla del proyecto; el plan gratuito de Gemini puede usar los datos enviados |
| 2026-10-29 | Si no hay clave o Gemini falla, el análisis usa un texto automático de plantilla | El sistema nunca se cae por la IA y las pruebas no dependen de internet |
| 2026-10-29 | Gemini por REST con `httpx` (sin librería de Google), modelo principal `gemini-3.1-flash-lite` y modelos de respaldo (`GEMINI_MODELOS_RESPALDO`) que se prueban si hay saturación (503), falta de cuota (429) o demora | Sin dependencias nuevas; en el plan gratuito los modelos se saturan de forma intermitente y sus nombres cambian seguido |
| 2026-10-29 | La estación y la fuente del texto (gemini/plantilla) se guardan dentro de `indicadores` de `analisis_bloque` | Evita una migración solo para dos datos de contexto |
| 2026-10-29 | 15 tipos de campaña (6 iniciales + 9 del usuario) en `config/tipos_campana.yaml`; `comercio_temporada` queda como mercadería por cambio de estación | Cubre campañas festivas, agrícolas, de rubro, vivienda y salud; el tipo climático conecta con el IoT |
| 2026-10-29 | El mes de registro de la encuesta es una variable del modelo | Las campañas festivas dependen de la época del año; no se agrega ninguna pregunta a la encuesta |
| 2026-10-29 | Pecuario, ventas por internet y compra de vehículo se detectan por el texto de la necesidad, sin nuevos sectores | No se modifica la encuesta de la Fase 1 ya validada |
| 2026-10-29 | Random Forest (100 árboles, `class_weight=balanced`, semilla 42) en un Pipeline con OneHotEncoder, entrenado con 1 500 clientes sintéticos | No hay historial real de campañas; el dataset sintético se declara como limitación |
| 2026-10-29 | Evaluación: 80/20 + validación cruzada de 5 partes + prueba con las 20 encuestas reales etiquetadas a mano | La prueba con datos que el modelo nunca vio es la métrica más honesta |
| 2026-10-29 | No se ajustaron los perfiles para acertar las 4 encuestas reales falladas | Hacerlo sería sobreajustar al conjunto de prueba |
| 2026-10-29 | `modelo.joblib` se guarda en el repositorio y scikit-learn se fija en 1.9.1 | Otra laptop funciona sin reentrenar; el archivo solo carga con la misma versión |
| 2026-10-29 | El modelo se carga una vez en memoria (en segundo plano al arrancar); sin modelo, el análisis sigue sin sugerencia | Predicción en ~30 ms; el sistema nunca se cae por el ML |
| 2026-10-29 | Solo el gerente edita, regenera, publica, retira y elimina campañas; el asesor solo las genera (quedan en borrador) y las consulta | Las decisiones comerciales son responsabilidad de la gerencia (pedido del usuario) |
| 2026-10-29 | Gemini responde en modo JSON y se valida con Pydantic; si el JSON es inválido o el texto menciona tasas o promete aprobación, se pasa al siguiente modelo y, al final, a una plantilla | La IA no inventa tasas ni promete aprobación, y el sistema nunca se queda sin campaña |
| 2026-10-29 | El filtro de reglas solo se aplica al texto de la IA, no a lo que edita el gerente | Fijar condiciones es decisión humana de la gerencia |
| 2026-10-29 | Vigencia = fecha de inicio + duración en semanas; estados visibles: borrador, programada, vigente, finalizada, retirada | El chatbot ofrece solo las campañas publicadas dentro de sus fechas (`/api/campanas/vigentes`) |
| 2026-10-29 | El formulario se prellena con el último análisis del bloque (tipo del Random Forest, necesidad, zonas, plazo, meta) y la temporada del IoT como sugerencia | Menos tiempo para crear una campaña: ese es el problema que resuelve el proyecto |
| 2026-10-29 | La raíz `/` es una landing pública con campañas vigentes y el chat; el login sigue en `/login` | Pedido del usuario: página corporativa que lleve al cliente a la campaña ideal |
| 2026-10-29 | Chat web con aspecto de WhatsApp, no WhatsApp real | La API de WhatsApp Business exige verificación de Meta y puede tener costo |
| 2026-10-29 | Chatbot híbrido: reglas para saludo, oficio y captura de datos; Gemini solo para la oferta y las dudas, en JSON validado | La captura (consentimiento, nombre, teléfono) es predecible y nunca envía datos personales a la IA |
| 2026-10-29 | El backend rechaza respuestas de Gemini con más de una pregunta, con tasas o promesas de aprobación, o con teléfonos; si todos los modelos fallan, usa plantillas | Las reglas del chatbot se cumplen aunque la IA o el cliente intenten saltárselas |
| 2026-10-29 | Límites: 20 mensajes por conversación y 10 conversaciones por día por conexión (`config/chatbot.yaml`); se guarda solo una huella cifrada de la IP | La página es pública; se protege la cuota gratuita de Gemini y la privacidad |
| 2026-10-29 | Consentimiento explícito (Ley 29733) antes de pedir nombre y teléfono; teléfono peruano de 9 dígitos que empieza con 9 | Requisito legal y regla del proyecto |
| 2026-10-29 | Mascota "Uku" (Oso de Anteojos), dibujo SVG propio con animaciones CSS; textos de la empresa en `config/institucion.yaml` con campos [COMPLETAR] | No se inventan datos de la empresa; se editan sin tocar código |
| 2026-10-29 | Fase 7: prueba de punta a punta (`tests/test_integracion.py`) con Gemini simulado caído; verifica además que ningún nombre ni teléfono llega a los prompts | Demuestra que las 6 fases funcionan juntas y que el sistema sigue operando sin Gemini |
| 2026-10-29 | `scripts/verificar_sistema.py` (solo lectura) y `scripts/medir_tiempos.py` (no guarda nada) | Revisión rápida antes de la sustentación y medición real de la columna «después» |
| 2026-10-29 | La columna «antes» de `docs/tiempos.md` queda en [COMPLETAR] hasta entrevistar a la empresa | No se inventan datos; guía de entrevista incluida |
