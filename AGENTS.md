# AGENTS.md – Proyecto ACTIVA

Instrucciones para cualquier agente de IA (Claude Code, Codex, etc.) que trabaje en este repositorio. Léelas completas antes de tocar código.

## Proyecto

**Sistema de Diagnóstico Financiero Estacional y Recomendación de Campañas Crediticias Basado en IA e IoT – GRUPO ACTIVA S.A.C.** (microfinanzas, Huánuco, Perú). Proyecto de titulación SENATI, una sola persona, 8 semanas. Prioriza siempre la solución más simple que funcione.

Problema: las campañas crediticias se crean de forma lenta, manual y reactiva. Sectores: agrícola, comerciantes de mercado, ambulantes y taxistas.

## Alcance (SOLO estos cinco objetivos)

1. **Web del asesor:** encuestas socioeconómicas agrupadas por BLOQUES y generación de campañas.
2. **IoT:** ESP32 + DHT22 (Wokwi) que envía temperatura y humedad a Firebase Realtime Database.
3. **IA:** (a) análisis de necesidades por bloque, (b) Random Forest (Scikit-Learn) que sugiere el tipo de campaña, (c) generación de campañas con Gemini.
4. **Chatbot:** asesor comercial virtual que ofrece campañas vigentes y capta nombre y teléfono de interesados.
5. **App Flutter:** dashboard IoT (registros diarios, análisis semana/mes, estación actual, temporada próxima, notificación de cambios). Sin encuestas ni créditos.

Cualquier idea fuera de esto va a `docs/mejoras_futuras.md` y **no se implementa**.

## Stack decidido

| Capa | Herramienta |
| --- | --- |
| Backend | Python 3.11+ · FastAPI · SQLAlchemy 2 · Pydantic v2 · APScheduler |
| Base de datos | **PostgreSQL en Supabase** (plan gratuito). **No se usa Docker ni PostgreSQL local.** |
| Migraciones | Alembic |
| Web del asesor | Jinja2 + Bootstrap 5 + JavaScript (servida por FastAPI) |
| ML | Scikit-Learn (Random Forest), pandas, joblib |
| IA generativa | API gratuita de Google Gemini (modelos Flash), solo desde el backend |
| IoT | ESP32 + DHT22 en Wokwi (Arduino C++), Firebase Realtime Database (REST) |
| App móvil | Flutter + fl_chart + flutter_local_notifications |
| Pruebas | pytest (con SQLite en memoria para no depender de Supabase) |

### Supabase: reglas de uso

- Se usa Supabase **solo como PostgreSQL administrado**. La autenticación es propia del backend (usuarios en tabla `usuarios`, contraseñas con bcrypt, sesión por cookie firmada en la web y token JWT para la app). No usar Supabase Auth, Storage ni Edge Functions salvo decisión explícita del usuario.
- Conexión vía `DATABASE_URL` en `.env` (cadena del *Connection pooler* de Supabase, driver `postgresql+psycopg://`, `sslmode=require`).
- Usar siempre el host `aws-0-<region>.pooler.supabase.com` con usuario `postgres.<ref>`. La *Direct connection* (`db.<ref>.supabase.co`) es solo IPv6 y falla en la red del usuario.
- El esquema se crea y modifica **solo con migraciones Alembic**, nunca a mano desde el panel.
- La `service_role key` y la contraseña de la base nunca salen del servidor.
- El proyecto gratuito se pausa tras 1 semana sin uso: si la conexión falla, primero revisar si está pausado en el panel.
- Las pruebas automáticas no tocan Supabase.

## Estructura del repositorio

```
activa/
  AGENTS.md
  README.md
  backend/
    .env.example   (copiar a backend/.env)
    app/
      main.py  config.py  db.py  models.py  schemas.py  security.py  templating.py
      routers/    (auth, bloques, encuestas, clima, campanas, chat)
      services/   (estacion.py, firebase.py, ia.py, ml.py)
      templates/  static/
    alembic/
    config/umbrales.yaml
    ml/        (dataset, entrenamiento, modelo.joblib)
    scripts/   (seed, datos de prueba)
    tests/
    requirements.txt
  iot/       (sketch.ino, diagram.json, libraries.txt)
  mobile/    (proyecto Flutter)
  docs/      (informes, diagramas, capturas, decisiones.md, mejoras_futuras.md)
```

## Reglas de negocio (obligatorias)

- Una encuesta pertenece siempre a un bloque. El análisis usa **solo** las encuestas del bloque elegido.
- Campos de la encuesta: nombre, teléfono, zona, sector, ingreso mensual, años con el negocio, trabajadores, frecuencia de ingresos, crédito vigente, garantía, necesidad (texto libre), monto, plazo deseado, temporada de mayor necesidad, riesgo principal, interés en campaña, contacto preferido y **consentimiento obligatorio** (Ley 29733). Validación en servidor.
- Estación actual (promedio 28 días): humedad ≥ 75 % → Lluvias; si no, temperatura ≤ 12 °C → Invierno; si no, temperatura ≥ 24 °C → Verano; si no → Transición.
- Cambio relevante (bloque actual vs. anterior, 7 o 28 días): humedad ≥ 8 puntos o temperatura ≥ 2,5 °C.
- **Los umbrales viven en `backend/config/umbrales.yaml`**, nunca escritos en el código.
- Campañas: entradas (temporada, público objetivo, riesgo/necesidad, monto máximo opcional, plazo, zona, tipo de cliente, periodo de gracia, duración, presupuesto de difusión, meta). Salida JSON validada con: nombre, propuesta de valor, decisiones para la gerencia, capacitación (speech + objeciones con respuestas), plan de marketing (canales, gancho, mensaje de WhatsApp).
- La IA **no inventa tasas de interés ni promete aprobación**. Una campaña solo es vigente si el **gerente** la publica.
- Chatbot: tono cercano tipo WhatsApp, lenguaje sencillo, UNA pregunta por mensaje, conecta el oficio con el problema de la temporada, pide nombre y teléfono solo si hay interés, deriva a un asesor humano, límite de mensajes por usuario.
- Roles: `asesor` y `gerente`.

## Seguridad y costo

- Costo S/ 0: solo planes gratuitos y software libre. **Avisar antes de usar cualquier servicio que pueda cobrar.**
- Claves (Gemini, Firebase, Supabase) solo en variables de entorno del servidor. Nunca en la web, la app ni el repositorio. `.env` está en `.gitignore`; mantener `.env.example` actualizado.
- Nunca enviar nombres ni teléfonos reales a Gemini: anonimizar antes.

## Forma de trabajar (obligatoria)

1. Una fase a la vez: 0 base y login · 1 bloques y encuestas · 2 IoT Wokwi · 3 registros diarios y análisis estacional · 4 app móvil · 5 IA · 6 chatbot · 7 integración y cierre.
2. Antes de programar una fase: plan corto (archivos, decisiones, riesgos) y **esperar visto bueno**.
3. Código completo y ejecutable, con comandos exactos para correr y probar (Windows / PowerShell).
4. pytest para la lógica crítica y datos de ejemplo para ver resultados sin esperar semanas.
5. Al cerrar la fase: resumen de lo que funciona, cómo verificarlo y qué sigue. **No avanzar sin confirmación.**
6. Si algo no está claro: máximo una pregunta, con una opción por defecto.
7. Registrar decisiones importantes en `docs/decisiones.md`.
8. Explicar en lenguaje simple: el autor debe sustentar ante un jurado.

## Convenciones

- Código, nombres de tablas y variables en español sin tildes (`registros_diarios`, `ingreso_mensual`); comentarios breves en español.
- Comandos de desarrollo:
  - `cd backend; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt`
  - `alembic upgrade head`
  - `uvicorn app.main:app --reload`
  - `pytest`

## Estado actual

- [x] Fase 0 – Base y login: 11 pruebas pasando; conectado a Supabase (región us-east-1, Session pooler), tablas migradas y usuarios de prueba creados. Validada por el usuario (2026-10-28).
- [x] Fase 1 – Bloques y encuestas: 29 pruebas pasando; migración `actualizado_en` aplicada; 3 bloques y 20 encuestas de ejemplo en Supabase. Validada por el usuario (2026-10-28).
  - Varios bloques pueden estar abiertos a la vez (`Bloque.activo` = abierto); el asesor elige el bloque al registrar.
  - Solo el gerente crea, abre y cierra bloques. El asesor ve bloques y todas las encuestas.
  - Encuestas editables solo por quien las registró o por el gerente.
- [x] Fase 2 – IoT en Wokwi: archivos listos (`iot/`, `docs/firebase_reglas.json`, `scripts/ver_firebase.py`). Firebase: `https://activa-729e7-default-rtdb.firebaseio.com`. Circuito funcionando en Wokwi, reglas publicadas (lectura pública → 401), `FIREBASE_DB_SECRET` en `.env`. Validada por el usuario (2026-10-28).
  - El sketch se detiene solo tras 20 envíos (cada 30 s = 10 min), pedido del usuario para cuidar el plan gratuito.
- [x] Fase 3 – Registros diarios y análisis estacional: 62 pruebas pasando. Consolidación horaria (APScheduler) Firebase → `registros_diarios`; página `/clima`; API `/api/clima/{registros,analisis,diagnostico,ultima}` (sesión o JWT). Escenario «lluvias» simulado cargado en Supabase (`sim-huanuco-01`). Reglas con `.indexOn` publicadas. Validada por el usuario (2026-10-28).
  - "Periodo" (7/28 días) ≠ bloque de encuestas. Lógica pura en `services/estacion.py`; claves de estación = claves de `TEMPORADAS` (lluvias, invierno, verano, transicion).
- [x] Fase 4 – App móvil Flutter: app en `mobile/` (paquete `activa_clima`), 12 pruebas Flutter + 63 backend pasando, `flutter analyze` limpio. APK probado en el celular. Validada por el usuario (2026-10-29).
  - Entorno: Flutter 3.47 en `C:\src\flutter`, Android SDK 36; IP LAN de la PC 192.168.18.14 (red "Pública": requiere la regla de firewall que crea `iniciar_servidor.ps1` como admin).
  - La dirección del servidor se cambia en la app (Ajustes). En la sustentación quizá use otra laptop con internet compartido del celular: ver `docs/guia_otra_laptop.md`.
  - Notificación local solo con la app abierta/al volver a primer plano, y solo si el mensaje de alerta es nuevo.
