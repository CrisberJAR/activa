# Tiempos antes y después del sistema

Compara cuánto tarda GRUPO ACTIVA en crear una campaña crediticia **con el proceso manual (antes)** y **con el sistema ACTIVA (después)**.

> **Regla:** la columna «Antes» debe venir de la empresa (entrevista o registro de los asesores y la gerencia). No se inventa. Mientras no se tenga el dato, queda `[COMPLETAR]`.

## 1. Tabla comparativa

| Paso | Antes (manual) | Después (sistema ACTIVA) | Cómo se mide el «después» |
| --- | --- | --- | --- |
| Juntar y ordenar las encuestas de una zona | [COMPLETAR] | 0,1 s (se leen del bloque) | `scripts/medir_tiempos.py` |
| Detectar las necesidades más frecuentes | [COMPLETAR] | 3 ms (indicadores y ranking) | `scripts/medir_tiempos.py` |
| Saber qué temporada viene (clima) | [COMPLETAR] | Inmediato (el sensor actualiza cada hora) | Consolidación automática |
| Decidir el tipo de campaña | [COMPLETAR] | 40 ms (Random Forest) | `scripts/medir_tiempos.py` |
| Redactar el resumen del patrón | [COMPLETAR] | 2,4 s (Gemini) | `scripts/medir_tiempos.py` |
| Redactar la campaña: propuesta, speech, objeciones, marketing y WhatsApp | [COMPLETAR] | 3,8 s (Gemini) | `scripts/medir_tiempos.py` |
| **Total: de las encuestas a la propuesta de campaña** | **[COMPLETAR]** | **6,4 s** | `scripts/medir_tiempos.py` |
| Revisión y aprobación del gerente | [COMPLETAR] | Depende del gerente (el sistema le deja todo listo en una pantalla) | — |
| Captar a un cliente interesado | [COMPLETAR] | Al momento: Uku lo registra y aparece en «Interesados» con botón de WhatsApp | Prueba de punta a punta |

**Condiciones de la medición del «después»** (29/10/2026):
- Bloque «Bloque 1 – Mercado Modelo (ejemplo)», con 7 encuestas.
- Gemini `gemini-3.1-flash-lite` (plan gratuito); mediana de 3 repeticiones.
- Laptop del autor, con la base en Supabase (us-east-1).

La primera carga del modelo Random Forest tarda unos 3 s. El servidor la hace al arrancar, así que el usuario no la espera.

Los tiempos de Gemini varían según la carga del servicio. Si Gemini no responde, el sistema usa sus plantillas en menos de 1 s.

Para repetir la medición: `cd backend; .\.venv\Scripts\python.exe -m scripts.medir_tiempos`

## 2. Cómo obtener la columna «Antes»

Haz una entrevista corta (10 minutos) a **un asesor y al gerente**, y anota sus respuestas tal cual. Si dan un rango (por ejemplo, «de 3 a 5 días»), usa el punto medio y anota el rango.

1. Desde que terminan las encuestas de una zona, ¿cuánto tardan en **ordenarlas** (pasarlas a Excel o revisarlas)?
2. ¿Cuánto tardan en **decidir qué necesitan** más los clientes de esa zona?
3. ¿Cómo saben **qué temporada viene** y cuánto tiempo les toma?
4. ¿Cuánto tardan en **decidir el tipo de campaña** (reuniones incluidas)?
5. ¿Cuánto tardan en **redactar la campaña**: propuesta, guion para los asesores, respuestas a objeciones y mensajes de difusión?
6. En total, desde que tienen la información hasta que la campaña sale a la calle, ¿cuántos **días** pasan?
7. ¿Cómo registran hoy a un cliente que **pregunta por un crédito**, y cuánto tarda en llegarle a un asesor?

Guarda la fecha de la entrevista, el cargo de quien respondió (sin nombre si prefiere) y sus respuestas en `docs/entrevista_tiempos.md`. Sirve como evidencia para el jurado.

## 3. Cómo leer el resultado (para la sustentación)

- La mejora no es solo de velocidad. El sistema también:
  - usa **solo las encuestas del bloque**;
  - toma en cuenta **el clima real** del sensor;
  - deja la campaña **completa y uniforme**, con el speech, las objeciones y el WhatsApp.
- La decisión final sigue siendo humana: **solo el gerente publica**.
- La IA no inventa tasas ni promete aprobación: hay un filtro que lo bloquea.
- Fórmula para el informe: **reducción (%) = (antes − después) / antes × 100**.
