# ACTIVA – Estado del proyecto para continuar (actualizado 2026-11-06)

> **Para el usuario:** al entrar, escribe solo: *Lee `docs\CONTINUAR.md` y dime cómo va el proyecto y qué sigue.*

## Novedad 2026-11-06: ACTIVA 360° (Cajathon 2026)
Se construyeron seguidas las fases 8 a 13 (base 360°, Comercial, Negocios, Riesgos, Recuperaciones y cierre), **pendientes de validación del usuario**.
Guía completa: `docs/activa360.md`. Ruta actual del proyecto: `C:\Users\ESTUDIANTE\Documents\HACKATON_CAJA_TRUJILLO\activa`.
Siguiente paso: el usuario prueba con `python -m scripts.seed_360`, valida y decide si se hace `git push` (despliega en Render).
Lo de abajo (fases 0 a 7) sigue vigente.

## Empieza aquí (para la IA)
1. Lee este archivo y `AGENTS.md` completo antes de tocar código.
2. Comprueba el estado real: `git status` y `git log --oneline -n 5`. Si algo no coincide con este archivo, dilo.
3. Resume al usuario en pocas líneas cómo va el proyecto y qué sigue. Pregúntale si ya hizo los pasos pendientes.

**Siguiente paso:** el usuario debe crear el servicio en Render (`docs/despliegue_render.md`) y pasar la dirección pública; luego la IA la comprueba. Después queda cerrar la Fase 7.

**Decisión ya tomada, no reabrir:** las 20 encuestas son ficticias y el usuario no tiene encuestas de campo. Quedan como están y se llaman **«encuestas de validación»**: no escribir que son «reales» ni agregar la etiqueta «de ejemplo». Si el usuario pregunta qué decir al jurado, la respuesta correcta es que son simuladas.

## Proyecto
Tesis SENATI: sistema de diagnóstico estacional (IoT) y campañas crediticias con IA para GRUPO ACTIVA S.A.C. (Huánuco).
Ruta: `C:\Users\USER\activa`. Stack: FastAPI + Supabase (PostgreSQL, **sin Docker**) + Firebase RTDB + Wokwi (ESP32) + Flutter + Gemini.
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
| 5b Random Forest | ✅ validada (2026-10-29) | 15 tipos de campaña; entrenar con `python -m ml.entrenar` (≈10 s); métricas en `/analisis/modelo`. Exactitud 91 % sintética y 80 % (16/20) con 20 encuestas de validación |
| 5c Generador de campañas | ✅ validada (2026-10-29) | `/campanas`: el asesor genera (borrador), solo el gerente edita/publica/retira. Gemini en JSON validado + filtro de tasas y promesas + plantilla. Vigentes en `/api/campanas/vigentes` (para el chatbot) |
| 6 Chatbot y página pública | ✅ validada (2026-10-29) | `/` landing con campañas vigentes y Uku (Oso de Anteojos) que abre el chat; reglas + Gemini; `/interesados` para asesores. Completar datos de contacto en `config/institucion.yaml` |
| 7 Integración y cierre | 🟡 falta validación del usuario | Prueba de punta a punta, `scripts.verificar_sistema`, `scripts.medir_tiempos`, manual, guion de demo, tiempos y capturas. Pendiente del usuario: tiempos «antes», capturas a mano, datos de contacto |

Pruebas: 173 del backend (`cd backend; .\.venv\Scripts\python.exe -m pytest`) y 12 de Flutter (`cd mobile; flutter test`), todas pasan.

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

## Lo que falta
**Del usuario (Fase 7):** entrevista para la columna «Antes» de `docs/tiempos.md`, datos de contacto en `config/institucion.yaml`, publicar una campaña, capturas de `docs/manual_usuario.md` (sección 9), probar `docs/guion_demo.md` completo y validar.

**Despliegue:** `render.yaml` listo. Seguir `docs/despliegue_render.md`: crear el servicio en Render, cambiar las contraseñas de prueba y comprobar.

## Pendientes menores
- **Repositorio:** privado en https://github.com/CrisberJAR/activa (rama `main`). Cada `git push` desplegará en Render cuando exista el servicio.
- Completar los datos de contacto `[COMPLETAR]` en `backend\config\institucion.yaml`.
- Antes de la sustentación, revisar que Supabase no esté pausado (se pausa tras 1 semana sin uso).

## Datos útiles
- Usuarios de prueba: `asesor@activa.pe / Asesor2026!`, `gerente@activa.pe / Gerente2026!` (dejan de valer cuando el usuario las cambie con `scripts.cambiar_password`; las nuevas no se escriben aquí)
- Web: `http://localhost:8000/login` · Documentación de la API: `/docs` · Salud de la base: `/api/salud`
- Firebase: `https://activa-729e7-default-rtdb.firebaseio.com` · Wokwi: proyecto "ACTIVA sensor agricola" en la cuenta del usuario
- Clima simulado: `cd backend; .\.venv\Scripts\python.exe -m scripts.generar_datos_clima --escenario lluvias|invierno|verano`
- Flutter: `C:\src\flutter\bin\flutter.bat` · Python del proyecto: `backend\.venv`
- GitHub: `gh` ya tiene la sesión de `CrisberJAR`; `gh repo create` y `git push` están permitidos en Claude Code
- Decisiones tomadas: `docs\decisiones.md` · Ideas fuera de alcance: `docs\mejoras_futuras.md`
