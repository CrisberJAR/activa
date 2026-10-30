# Manual de usuario – Sistema ACTIVA

Sistema de diagnóstico estacional y campañas crediticias con IA e IoT de GRUPO ACTIVA S.A.C.

## 1. ¿Quién usa qué?

| Persona | Dónde entra | Qué hace |
| --- | --- | --- |
| **Cliente** | Página pública `http://<servidor>:8000/` | Conoce la empresa, ve las campañas vigentes y conversa con Uku |
| **Asesor** | Web interna `/login` | Registra encuestas, analiza bloques, genera borradores de campaña y atiende a los interesados |
| **Gerente** | Web interna `/login` | Todo lo del asesor, y además crea bloques y edita, publica o retira campañas |
| **Asesor o gerente (en campo)** | App móvil «ACTIVA Clima» | Ve el clima del sensor, la estación actual y la temporada próxima |

> Las capturas de pantalla están en `docs/capturas/` (ver la lista al final).

## 2. Cómo funciona el sistema en una frase

El sensor mide el clima → el asesor registra encuestas por bloque → la IA detecta las necesidades y sugiere el tipo de campaña → Gemini redacta la campaña → **el gerente la publica** → Uku la ofrece en la web y capta a los interesados → el asesor los llama por WhatsApp.

## 3. Ingresar al sistema

1. Abre `http://<servidor>:8000/` y pulsa **Acceso asesores** (o ve directo a `/login`).
2. Escribe tu correo y contraseña.
3. Verás el menú de tu rol (asesor o gerente).

Para salir, usa **Salir** en la barra superior.

## 4. Manual del gerente

### 4.1 Crear y cerrar bloques de encuestas
Un **bloque** es un grupo de encuestas que se analizan juntas (por ejemplo, «Valle de Pillco Marca – octubre»).

1. Menú → **Bloques**.
2. Escribe el nombre y la fecha de inicio y pulsa **Crear bloque**. Queda **abierto**.
3. Mientras está abierto, los asesores pueden registrar encuestas en él. Pueden estar abiertos varios bloques a la vez.
4. Cuando termine el trabajo de campo, pulsa **Cerrar**. Ya no se registran más encuestas en ese bloque.

### 4.2 Revisar y publicar campañas
Las campañas que generan los asesores quedan en **borrador**. Solo el gerente decide.

1. Menú → **Publicar campañas** (lista de borradores).
2. Abre una campaña y revisa sus 5 partes: datos de entrada, propuesta de valor, decisiones para la gerencia, capacitación (speech y objeciones) y plan de marketing (incluye el mensaje de WhatsApp).
3. Si quieres cambiar algo:
   - **Editar**: corriges los textos a mano.
   - **Regenerar**: Gemini vuelve a redactarla con los mismos datos.
4. Pulsa **Publicar**. La campaña queda:
   - **Programada**, si su fecha de inicio es futura.
   - **Vigente**, desde la fecha de inicio y durante las semanas indicadas.
5. Solo las campañas **vigentes** aparecen en la página pública y las ofrece Uku.
6. **Retirar** la quita de la web antes de tiempo. **Eliminar** la borra por completo.

> La IA nunca escribe tasas de interés ni promete aprobación. Si un texto lo hace, el sistema lo bloquea.

## 5. Manual del asesor

### 5.1 Registrar una encuesta
1. Menú → **Encuestas** → **Nueva encuesta**.
2. Elige el **bloque** (solo aparecen los abiertos).
3. Llena los datos del cliente: negocio, ingresos, necesidad, monto, plazo, temporada de mayor necesidad y riesgo principal.
4. Marca el **consentimiento** (Ley 29733). Sin él, la encuesta no se guarda.
5. Pulsa **Guardar**. Si falta algo, el sistema te indica qué campo corregir.

Puedes editar tus propias encuestas. Las de otros asesores solo puedes verlas.

### 5.2 Ver el clima
Menú → **Clima y estación**. Muestra:
- los registros diarios del sensor;
- los promedios de 7 y 28 días;
- la **estación actual** (Lluvias, Invierno, Verano o Transición);
- la **temporada próxima** y una alerta si el clima cambió de forma relevante.

### 5.3 Analizar un bloque
1. Menú → **Análisis de bloque** → elige el bloque → **Analizar**.
2. Verás:
   - **Indicadores**: número de encuestas, sectores, ingreso y monto promedio, % interesados.
   - **Ranking de necesidades**: qué piden más los clientes de ese bloque.
   - **Texto del patrón**, redactado por Gemini sin nombres ni teléfonos. Si Gemini no responde, aparece un texto automático.
   - **Tipo de campaña sugerido** por el Random Forest, con su porcentaje de confianza.
3. Pulsa **Generar campaña con esta sugerencia**.

### 5.4 Generar una campaña
1. El formulario ya viene lleno con la sugerencia del análisis y la temporada del sensor. Revisa y ajusta:
   - el público objetivo y la zona;
   - el plazo, el monto máximo y el periodo de gracia;
   - la fecha de inicio y la duración;
   - el presupuesto de difusión y la meta de créditos.
2. Pulsa **Generar campaña**. En unos segundos Gemini redacta la campaña.
3. Queda en **borrador**: avisa al gerente para que la revise y la publique.

### 5.5 Atender a los interesados
Cuando un cliente deja sus datos con Uku, aparece en Menú → **Interesados**.

1. Revisa: nombre, teléfono, oficio, campaña consultada y fecha.
2. El botón **Chat** muestra la conversación completa.
3. El botón **WhatsApp** abre una conversación con el cliente, con un saludo ya escrito.
4. Después de contactarlo, pulsa **Marcar atendido**. Pasa a la pestaña «Atendidos». Con **Reabrir** vuelve a pendientes.

## 6. Para el cliente: conversar con Uku

1. Entra a la página de Grupo Activa.
2. Pulsa el **oso de anteojos** (abajo a la derecha) o **Conversa con Uku**. En una campaña, el botón **Me interesa** abre el chat sobre esa campaña.
3. Uku pregunta a qué te dedicas. Elige un botón o escríbelo.
4. Te cuenta la campaña que mejor encaja con tu oficio y la temporada. Puedes decir **Sí, me interesa**, **Tengo una duda** o **No, gracias**.
5. Si te interesa, primero pide tu **permiso** para guardar tus datos (Ley 29733). Luego te pide tu **nombre** y tu **celular** (9 dígitos).
6. Listo: un asesor te contactará. Uku nunca da tasas ni promete aprobación: eso lo ve el asesor en la evaluación.

Límites: 20 mensajes por conversación y 10 conversaciones al día por conexión.

## 7. App móvil «ACTIVA Clima»

1. Instala `docs/apk/ACTIVA-Clima.apk` en el celular Android.
2. Abre la app → **Ajustes** → escribe la dirección del servidor (la que muestra `iniciar_servidor.ps1`) → **Probar conexión**.
3. Ingresa con tu usuario de la web.
4. Pestañas:
   - **Hoy**: última lectura del sensor, estación actual y temporada próxima.
   - **Registros**: promedios diarios.
   - **Análisis**: gráficos de la semana o del mes.
5. Si el clima cambia de forma relevante, la app muestra una **notificación**.

## 8. Problemas frecuentes

| Problema | Solución |
| --- | --- |
| La web no abre o dice error de base de datos | El proyecto gratuito de Supabase se pausa tras 1 semana sin uso: entra al panel de Supabase y pulsa **Restore**. |
| El análisis o la campaña dicen «texto automático» o «plantilla» | Gemini no respondió (saturado o sin cuota). El sistema sigue funcionando; puedes **Regenerar** más tarde. |
| Uku dice que no hay campaña para mi oficio | No hay campañas vigentes de ese tipo: el gerente debe publicar una. |
| La app no conecta | El celular y la PC deben estar en la misma red, y debe existir la regla del firewall (ver `docs/guia_otra_laptop.md`). |
| No sé si todo está listo para una demostración | Ejecuta `python -m scripts.verificar_sistema` desde `backend/`. |

## 9. Lista de capturas (`docs/capturas/`)

**Tomadas automáticamente:**
- `01_pagina_publica.png`: portada.
- `02_pagina_publica_completa.png`: página completa.
- `03_chat_uku.png`: chat abierto.
- `04_login.png`.

> Las capturas 01 a 03 se tomaron sin campañas vigentes. Vuelve a tomarlas cuando el gerente publique una.

**Por tomar a mano** (inicia sesión, pulsa `Win + Shift + S` y guarda con estos nombres):

| N.º | Archivo | Pantalla |
| --- | --- | --- |
| 05 | `05_menu_gerente.png` | Menú del gerente |
| 06 | `06_bloques.png` | Bloques (gerente) |
| 07 | `07_encuesta_nueva.png` | Formulario de encuesta con el consentimiento |
| 08 | `08_clima.png` | Clima y estación con la alerta |
| 09 | `09_analisis.png` | Análisis de un bloque (ranking y texto de Gemini) |
| 10 | `10_modelo.png` | Métricas del Random Forest (`/analisis/modelo`) |
| 11 | `11_campana_borrador.png` | Detalle de una campaña en borrador |
| 12 | `12_campana_publicada.png` | La misma campaña publicada (vigente) |
| 13 | `13_landing_campana.png` | La campaña vigente en la página pública |
| 14 | `14_chat_completo.png` | Conversación con Uku hasta dejar los datos |
| 15 | `15_interesados.png` | Panel de interesados con el botón de WhatsApp |
| 16 | `16_app_hoy.png` | App: pestaña Hoy (desde el celular) |
| 17 | `17_app_analisis.png` | App: pestaña Análisis |
| 18 | `18_notificacion.png` | Notificación de cambio de clima en el celular |
| 19 | `19_wokwi.png` | Circuito ESP32 + DHT22 funcionando en Wokwi |
| 20 | `20_firebase.png` | Datos llegando a Firebase Realtime Database |
