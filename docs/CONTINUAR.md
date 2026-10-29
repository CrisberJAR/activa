# ACTIVA – Estado del proyecto para continuar (actualizado 2026-10-28)

> Pégale este archivo a la IA al empezar. Las reglas completas están en `C:\Users\USER\activa\AGENTS.md`: léelo antes de tocar código.

## Proyecto
Tesis SENATI: sistema de diagnóstico estacional (IoT) y campañas crediticias con IA para GRUPO ACTIVA S.A.C. (Huánuco).
Ruta: `C:\Users\USER\activa`. Stack: FastAPI + Supabase (PostgreSQL, **sin Docker**) + Firebase RTDB + Wokwi (ESP32) + Flutter + Gemini (pendiente).
Forma de trabajo: **una fase a la vez**, plan corto → visto bueno del usuario → código + pruebas → validación. Decir siempre qué instalar, dónde registrarse y qué datos debe pasar el usuario (las claves van en `backend\.env`, nunca por el chat).

## Hecho
| Fase | Estado | Resumen |
|---|---|---|
| 0 Base y login | ✅ validada | Roles asesor/gerente, Supabase conectado por *Session pooler* (us-east-1), migraciones Alembic |
| 1 Bloques y encuestas | ✅ validada | Solo el gerente crea, abre y cierra bloques (puede haber varios abiertos). El asesor ve todo y edita solo sus encuestas. Hay 3 bloques y 20 encuestas de ejemplo |
| 2 IoT Wokwi → Firebase | ✅ validada | ESP32 + DHT22 en el pin 15; envía cada 30 s y se detiene tras 20 envíos. Reglas de Firebase cerradas (con `.indexOn`) |
| 3 Análisis estacional | ✅ validada | Consolidación horaria Firebase → `registros_diarios`; página `/clima`; API `/api/clima/*`. Escenario «lluvias» simulado en el sensor `sim-huanuco-01` |
| 4 App Flutter | ✅ validada (2026-10-29) | Pantallas Hoy / Registros / Análisis / Ajustes, notificación local, servidor configurable. APK en `docs\apk\ACTIVA-Clima.apk` |
| 5a Análisis por bloque | ✅ validada (2026-10-29) | `/analisis`: indicadores, ranking de necesidades (palabras clave en `config/necesidades.yaml`) y texto del patrón con Gemini (principal `gemini-3.1-flash-lite` + respaldos; si todos fallan, plantilla). Probar clave: `python -m scripts.probar_gemini` |
| 5b Random Forest | ✅ validada (2026-10-29) | 15 tipos de campaña; entrenar con `python -m ml.entrenar` (≈10 s); métricas en `/analisis/modelo`. Exactitud 91 % sintética y 80 % (16/20) con encuestas reales |

Pruebas: 63 del backend (`cd backend; .\.venv\Scripts\python.exe -m pytest`) y 12 de Flutter (`cd mobile; flutter test`), todas pasan.

## Cómo probar la app (Fase 4, ya validada; útil para repetir la demo)
1. **Firewall (una vez):** abrir PowerShell **como administrador** y ejecutar:
   `New-NetFirewallRule -DisplayName "ACTIVA backend 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Any`
2. **Arrancar el backend:** `cd C:\Users\USER\activa; powershell -ExecutionPolicy Bypass -File .\iniciar_servidor.ps1` (muestra la IP que va en la app; normalmente `http://192.168.18.14:8000`).
3. **Instalar** `docs\apk\ACTIVA-Clima.apk` en el celular, conectado al mismo Wi-Fi (ALHIS 5G).
4. En la app: **Probar conexión** → entrar con `asesor@activa.pe / Asesor2026!` → Ajustes → elegir el sensor `sim-huanuco-01`.
5. Verificar:
   - las 3 pestañas muestran lo mismo que `http://localhost:8000/clima` con el mismo sensor;
   - llega la notificación (si no, usar Ajustes → Probar notificación).
6. Opcional: ensayar con el internet compartido del celular (ver `docs\guia_otra_laptop.md`).
7. Tomar capturas para el Capítulo IV.
8. Si funciona, avisar a la IA para **cerrar la Fase 4** y pasar a la Fase 5.

## Lo que falta después
- **Fase 5 – IA** (en 3 entregas, validando cada una):
  - (a) análisis por bloque, que usa **solo** las encuestas de ese bloque: ranking de necesidades, indicadores y texto del patrón con Gemini;
  - (b) Random Forest con encuestas reales más datos sintéticos declarados como tales, con sus métricas;
  - (c) generador de campañas con salida JSON en 5 secciones; la temporada detectada se ofrece como sugerencia y **solo el gerente publica**.
  - El usuario deberá sacar una clave gratis de Gemini en https://aistudio.google.com y ponerla en `.env` como `GEMINI_API_KEY`.
  - No enviar nombres ni teléfonos a Gemini, y que la IA no invente tasas ni prometa aprobación.
- **Fase 6 – Chatbot:** widget web público; usa la estación vigente y las campañas publicadas; una pregunta por mensaje; guarda al interesado (nombre y teléfono); tiene límite de mensajes y deriva a un asesor humano.
- **Fase 7 – Cierre:** prueba de punta a punta, manual de usuario, capturas y tabla de tiempos antes/después.

## Pendientes menores
- **Commit en git:** el repositorio existe pero **todavía no hay ningún commit**. El usuario no lo ha pedido; preguntarle. Subir a GitHub (privado) cuando tenga el repositorio.
- Antes de la sustentación, revisar que Supabase no esté pausado (se pausa tras 1 semana sin uso).

## Datos útiles
- Usuarios de prueba: `asesor@activa.pe / Asesor2026!`, `gerente@activa.pe / Gerente2026!`
- Web: `http://localhost:8000/login` · Documentación de la API: `/docs` · Salud de la base: `/api/salud`
- Firebase: `https://activa-729e7-default-rtdb.firebaseio.com` · Wokwi: proyecto "ACTIVA sensor agricola" en la cuenta del usuario
- Clima simulado: `cd backend; .\.venv\Scripts\python.exe -m scripts.generar_datos_clima --escenario lluvias|invierno|verano`
- Flutter: `C:\src\flutter\bin\flutter.bat` · Python del proyecto: `backend\.venv`
- Decisiones tomadas: `docs\decisiones.md` · Ideas fuera de alcance: `docs\mejoras_futuras.md`
