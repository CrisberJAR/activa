# ACTIVA – Diagnóstico Financiero Estacional y Campañas Crediticias (IA + IoT)

Proyecto de titulación SENATI para GRUPO ACTIVA S.A.C. Reglas y alcance en [AGENTS.md](AGENTS.md).

## Requisitos

- Python 3.11 o superior (probado con 3.13)
- Git
- Una cuenta gratuita en [Supabase](https://supabase.com) (base de datos PostgreSQL)

## Puesta en marcha del backend (Windows / PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env      # luego edita .env con tus datos de Supabase
alembic upgrade head        # crea las tablas en Supabase
python -m scripts.seed_usuarios
python -m scripts.seed_encuestas   # 3 bloques y 20 encuestas de ejemplo (ficticias)
python -m scripts.generar_datos_clima --escenario lluvias   # 8 semanas de clima simulado (lluvias | invierno | verano)
uvicorn app.main:app --reload
```

- Página pública (clientes, chat con Uku): http://localhost:8000/
- Web del asesor y del gerente: http://localhost:8000/login
- Documentación de la API: http://localhost:8000/docs
- Prueba de conexión a la base: http://localhost:8000/api/salud

Usuarios de prueba: `asesor@activa.pe / Asesor2026!` y `gerente@activa.pe / Gerente2026!`

Para desarrollo (recarga al guardar cambios), desde la carpeta `activa`: `powershell -ExecutionPolicy Bypass -File .\iniciar_servidor.ps1 -Recargar`

## Antes de una demostración

```powershell
cd backend
python -m scripts.verificar_sistema     # Supabase, migraciones, datos, modelo, Gemini y Firebase
python -m scripts.medir_tiempos         # cronometra análisis y generación de campañas (no guarda nada)
```

## Pruebas

```powershell
cd backend
pytest
```

Las pruebas usan una base SQLite en memoria; no necesitan Supabase ni llaman a Gemini.
`tests/test_integracion.py` recorre el sistema completo de punta a punta.

## App móvil (Flutter)

```powershell
cd mobile
flutter test
flutter build apk --release     # genera build\app\outputs\flutter-apk\app-release.apk
```

Para que el celular se conecte, arranca el backend con `iniciar_servidor.ps1` (muestra la dirección que va en la app).
Para usar otra laptop o el internet compartido del celular: [docs/guia_otra_laptop.md](docs/guia_otra_laptop.md).

## Estructura

- `backend/` – API FastAPI, web del asesor, análisis y ML
- `iot/` – circuito Wokwi (ESP32 + DHT22)
- `mobile/` – app Flutter
- `docs/` – decisiones, mejoras futuras, evidencias
  - [Manual de usuario](docs/manual_usuario.md)
  - [Guion de demostración](docs/guion_demo.md)
  - [Tiempos antes/después](docs/tiempos.md)
  - Capturas en `docs/capturas/`
