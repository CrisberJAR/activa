# Guion de demostración (10 minutos) – Sustentación

## Un día antes
1. En el panel de Supabase, confirma que el proyecto **no está pausado**.
2. `cd C:\Users\USER\activa\backend; .\.venv\Scripts\python.exe -m scripts.verificar_sistema`
   Todo debe salir `[OK]`. Los `[AVISO]` se aceptan, pero léelos.
3. Si los datos de clima tienen más de 2 días:
   `.\.venv\Scripts\python.exe -m scripts.generar_datos_clima --escenario lluvias`
4. Deja **una campaña vigente** publicada, para que Uku tenga qué ofrecer, y **un bloque con encuestas** listo para analizar.
5. Carga el celular y deja instalada la app con la dirección del servidor probada.
6. Ten a mano las capturas de `docs/capturas/`, por si falla internet.

## El día de la sustentación (antes de entrar)
1. `cd C:\Users\USER\activa; powershell -ExecutionPolicy Bypass -File .\iniciar_servidor.ps1`
2. Abre dos ventanas del navegador:
   - Ventana normal con el **gerente** iniciado (`gerente@activa.pe`).
   - Ventana privada en la **página pública** `http://localhost:8000/`.
3. Abre Wokwi con el circuito, sin iniciar todavía.

## Guion

| Min | Qué muestras | Qué dices (idea) |
| --- | --- | --- |
| 0–1 | Página pública | «Este es el problema: las campañas se hacían de forma lenta, manual y reactiva. Así las ve hoy el cliente». |
| 1–2 | Wokwi ▶ y luego `/clima` | «El sensor ESP32 con DHT22 envía temperatura y humedad a Firebase. El sistema consolida un promedio diario y detecta la estación y la temporada que viene». |
| 2–3 | App en el celular | «El asesor en campo ve lo mismo en su celular y recibe un aviso si cambia el clima». |
| 3–4 | `/encuestas/nueva` | «El asesor registra la encuesta dentro de un bloque. El consentimiento de la Ley 29733 es obligatorio». |
| 4–5 | `/analisis` → Analizar | «La IA usa solo las encuestas de este bloque: ranking de necesidades, texto con Gemini sin datos personales y el tipo de campaña que sugiere el Random Forest». |
| 5–6 | `/analisis/modelo` | «El modelo tiene 91 % de exactitud en la prueba y 80 % con 20 encuestas de validación que no vio al entrenar». |
| 6–7 | Generar campaña | «En unos 6 segundos queda la campaña completa. Queda en borrador: la IA no inventa tasas ni promete aprobación». |
| 7–8 | Publicar (gerente) y recargar la página pública | «Solo el gerente decide. Al publicarla, aparece para los clientes». |
| 8–9 | Chat con Uku (ventana privada) | «Uku pregunta el oficio, ofrece la campaña según la temporada, pide permiso y solo entonces el nombre y el celular». |
| 9–10 | `/interesados` → WhatsApp → Marcar atendido | «El asesor recibe al interesado y lo contacta por WhatsApp. Antes tomaba [COMPLETAR días]; ahora toma segundos (ver `docs/tiempos.md`)». |

## Si algo falla
- **Gemini no responde:** di que el sistema tiene **modelos de respaldo y plantillas**, y sigue. Es parte del diseño.
- **No hay internet:** muestra las capturas y la prueba automática (`pytest`, 173 pruebas, incluida la de punta a punta).
- **Supabase pausado:** entra al panel → **Restore** (tarda unos 2 minutos).

## Preguntas probables del jurado
- **¿Por qué datos sintéticos en el Random Forest?** Todavía no hay un historial real de campañas. Se declaran como sintéticos y el modelo se valida aparte con 20 encuestas etiquetadas a mano que no vio al entrenar (80 %). Reentrenar con campañas reales es una mejora futura.
- **¿Qué pasa con los datos personales?**
  - No se envían a Gemini: se anonimizan antes.
  - Hay consentimiento en la encuesta y en el chat.
  - De la IP solo se guarda una huella cifrada.
- **¿Cuánto cuesta?** S/ 0. Supabase, Firebase y Gemini en planes gratuitos; el resto es software libre.
- **¿Puede la IA prometer créditos?** No. Un filtro bloquea tasas y promesas, y todo pasa por la revisión del gerente.
