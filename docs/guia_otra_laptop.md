# Guía: correr ACTIVA en otra laptop (por ejemplo, el día de la sustentación)

Los datos están en la nube (Supabase y Firebase), así que en otra laptop solo se necesita el código, el archivo `.env` y Python.

## 1. Preparar la laptop (una sola vez, con internet)

1. Instalar **Python 3.11 o superior** desde https://www.python.org/downloads/ (marcar *Add python.exe to PATH*).
2. Copiar la carpeta del proyecto `activa` (desde GitHub o por USB). **No hace falta** copiar `backend\.venv` ni `mobile\build`.
3. Copiar el archivo **`backend\.env` por USB**. Nunca subirlo a GitHub ni enviarlo por chat.
4. En PowerShell:
   ```powershell
   cd C:\ruta\a\activa\backend
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
5. Ejecutar **una vez como administrador** (clic derecho en PowerShell → *Ejecutar como administrador*) para crear la regla del firewall:
   ```powershell
   cd C:\ruta\a\activa
   powershell -ExecutionPolicy Bypass -File .\iniciar_servidor.ps1
   ```
   Luego se puede cerrar con `Ctrl + C`.

## 2. El día de la sustentación

1. **Un día antes:** entrar al panel de Supabase y comprobar que el proyecto no esté pausado (se pausa tras 1 semana sin uso). Si está pausado, pulsar *Restore*.
2. En el celular, activar **Compartir internet / Punto de acceso** y conectar la laptop a esa red.
3. En la laptop:
   ```powershell
   cd C:\ruta\a\activa
   powershell -ExecutionPolicy Bypass -File .\iniciar_servidor.ps1
   ```
   El script muestra la dirección, por ejemplo `http://192.168.43.120:8000`.
4. En la app: **Ajustes → Dirección del servidor →** escribir esa dirección → **Probar y guardar**.
5. Comprobar en el navegador de la laptop: http://localhost:8000/login

## 3. Si algo falla

| Problema | Solución |
| --- | --- |
| La app dice "No se pudo conectar" | Revisar que la laptop esté conectada a la red del celular y que la dirección sea la que mostró el script. Ejecutar el script como administrador (regla del firewall). |
| `/api/salud` dice error de base de datos | El proyecto de Supabase está pausado: restaurarlo desde el panel y esperar 2 minutos. |
| "Sesión vencida" en la app | Volver a iniciar sesión (el token dura 7 días). |
| No llegan lecturas nuevas | El sensor de Wokwi se detiene tras 10 minutos: reiniciar la simulación. |
