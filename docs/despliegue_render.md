# Despliegue en Render (gratis)

El backend y la web pasan a Render. La base sigue en Supabase, y los sensores en Firebase y Wokwi.

## Antes de empezar
- Ten a mano `backend\.env`: de ahí copiarás los valores. **No los pegues en ningún chat.**
- Comprueba que Supabase no esté pausado.

## 1. Crear el servicio
1. Regístrate en https://render.com con **Sign in with GitHub** (cuenta `CrisberJAR`).
2. Autoriza a Render a leer el repositorio privado `activa`.
3. En el panel: **New → Blueprint** y elige `CrisberJAR/activa`. Render lee el archivo `render.yaml`.
4. Revisa que el plan diga **Free**. Render pedirá estos valores; cópialos de `backend\.env`:
   - `DATABASE_URL`
   - `FIREBASE_DB_URL`
   - `FIREBASE_DB_SECRET`
   - `GEMINI_API_KEY`
5. Pulsa **Deploy Blueprint** y espera a que el estado diga **Live** (la primera vez, varios minutos).

`SECRET_KEY` la genera Render, y `COOKIE_SEGURA` ya está activada: no hay que escribirlas.

## 2. Cambiar las contraseñas de prueba
Las contraseñas de prueba están escritas en el repositorio. Cámbialas antes de difundir la dirección pública. Desde tu PC:

```powershell
cd C:\Users\USER\activa\backend
.\.venv\Scripts\python.exe -m scripts.cambiar_password asesor@activa.pe
.\.venv\Scripts\python.exe -m scripts.cambiar_password gerente@activa.pe
```

Como la base es la misma, el cambio vale también en tu PC y en la app. Guarda las nuevas en un lugar seguro.

## 3. Comprobar
Con la dirección que muestra Render (por ejemplo `https://activa.onrender.com`):

- `/api/salud` debe decir `"base_de_datos":"conectada"`.
- `/` muestra la página pública; `/login` permite entrar.
- `/analisis/modelo` muestra las métricas.
- En la app: **Ajustes → Servidor**, escribe la dirección con `https://` y pulsa **Probar conexión**.

## 4. Actualizar
Cada `git push` a `main` vuelve a desplegar el sistema. Si hay migraciones nuevas, se aplican durante la construcción.

## Limitaciones del plan gratuito
| Limitación | Qué hacer |
| --- | --- |
| Se duerme tras 15 minutos sin visitas y tarda hasta unos 2 minutos en despertar | Abre la página unos minutos antes de una demostración |
| La consolidación del clima solo corre mientras está despierto (una vez al despertar y luego cada hora) | Abre `/clima` antes de mostrarlo |
| 750 horas al mes y 512 MB de memoria, según la documentación de Render | Revisa los límites vigentes en su panel |
| Supabase se pausa tras una semana sin uso | Reactívalo en su panel y ejecuta `scripts.verificar_sistema` antes de sustentar |

Si algo falla, revisa **Logs** en el panel de Render. Si la construcción se detiene en `alembic upgrade head`, normalmente `DATABASE_URL` está mal copiada o Supabase está pausado.
