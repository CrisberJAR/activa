# ACTIVA 360° – Guía rápida (Cajathon 2026)

**Plataforma inteligente de inclusión y gestión financiera.** Conecta a personas y negocios con productos
financieros mediante IA, evaluación preliminar, seguimiento comercial, alertas de riesgo y gestión preventiva de pagos.

> Los productos y tasas son **configuraciones de demostración**. No son ofertas ni cotizaciones de Caja Trujillo.
> El sistema no aprueba créditos de forma automática ni mueve dinero.

## 1. Poner en marcha (Windows / PowerShell)

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m scripts.respaldo          # 1) copia de seguridad (backend\respaldos\)
alembic upgrade head                # 2) crea las 14 tablas nuevas (auditoría + 4 módulos)
python -m scripts.seed_360          # 3) opcional: datos de demostración (personas ficticias)
uvicorn app.main:app --reload       # 4) http://localhost:8000/login
pytest                              # pruebas automáticas
```

Para quitar los datos de demostración: `python -m scripts.seed_360 --borrar`.

## 2. Usuarios y roles

| Rol | Ve | Usuario de prueba |
| --- | --- | --- |
| Asesor de negocios | Comercial (prospectos, campañas, encuestas, clima IoT) y Negocios (sus expedientes y solicitudes) | `asesor@activa.pe / Asesor2026!` |
| Gerente | Todo; publica campañas, aprueba o deniega solicitudes, registra créditos, revisa reprogramaciones, crea usuarios, auditoría | `gerente@activa.pe / Gerente2026!` |
| Analista de riesgos | Solicitudes enviadas, evaluación preliminar, alertas de seguridad | `analista@activa.pe / Analista2026!` (con `seed_360`) |
| Gestor de recuperaciones | Su cartera asignada, alertas preventivas, pagos, gestiones y compromisos | `gestor@activa.pe / Gestor2026!` (con `seed_360`) |

Cambia las contraseñas antes de publicar: `python -m scripts.cambiar_password`.

## 3. Módulos

### Comercial
- **Prospectos** (`/prospectos`): registro con consentimiento (Ley 29733), segmento, región, necesidad y monto; embudo
  *nuevo → contactado → interesado → solicitud → evaluación → convertido / no convertido*; historial de contactos con próxima acción;
  el gerente asigna asesores. Los interesados del chatbot pasan al embudo con un botón.
- **Mensaje con IA**: Gemini sugiere un WhatsApp usando solo segmento, actividad y necesidad anonimizados; si menciona tasas o
  promete aprobación, se usa una plantilla.
- **Campañas**: lo anterior (IA + Random Forest + IoT) más segmento, región y producto; el asesor puede **enviar a aprobación**
  (estado *pendiente*); solo el gerente publica. Cada campaña muestra prospectos, convertidos y tasa de conversión.
- **Tasa de conversión** = convertidos / (convertidos + no convertidos).

### Negocios
- **Expediente** (`/clientes`): identificación, actividad, ingresos, gastos, deudas declaradas, historial. El asesor ve solo los suyos.
- **Solicitud digital**: el formulario cambia según el tipo de cliente (comerciante: ventas y costos; dependiente: sueldo neto;
  agricultor: ingreso por campaña; transportista: ingreso diario…). Se guarda como borrador.
- **Documentos**: lista de control por tipo de cliente (pendiente, recibido, validado, observado). No se suben archivos.
- **Estados**: borrador → enviada → en evaluación → (observada) → evaluada → **aprobada / denegada (decisión humana del gerente)**.
- **Simulador** (`/simulador`): método francés.

  - Tasa periódica: `i = (1 + TEA)^(1/n) − 1`, con n = 12 (mensual), 24 (quincenal) o 52 (semanal).
  - Cuota: `C = P · i / (1 − (1 + i)^(−N))`. La última cuota ajusta el saldo a cero.
  - Ejemplo verificable: S/ 10 000, TEA 12,6825 % (1 % mensual), 12 meses → cuota S/ 888,49.

### Riesgos
- **Indicadores**: ingreso neto, capacidad disponible (neto − cuotas de otras deudas), cuota estimada mensual, cuota/ingresos,
  deudas/ingresos, cuota/capacidad y completitud del expediente.
- **Semáforo** con explicación: rojo (revisión prioritaria), amarillo (información o revisión adicional), verde (sin alertas).
  Umbrales versionados y justificados en `backend/config/riesgos.yaml`.
- **Inconsistencias**: monto fuera del producto, monto alto frente al ingreso, ingresos que el formulario no sustenta,
  poca antigüedad, teléfono o solicitud duplicados, cambio brusco de ingresos. **Son avisos, no detección de fraude.**
- **Seguridad**: intentos fallidos, bloqueos y accesos denegados (`/riesgos/seguridad`).

### Recuperaciones
- El gerente registra un crédito **ya desembolsado por la entidad** (por ejemplo, desde una solicitud aprobada) y se genera el cronograma.
- Pagos registrados a mano (se aplican a las cuotas más antiguas), días de atraso y tramos (`config/recuperaciones.yaml`).
- **Alertas preventivas**: próximo vencimiento, cuota vencida, compromiso próximo, compromiso incumplido, reprogramación pendiente.
- Gestiones de cobranza, compromisos de pago y pedidos de reprogramación/refinanciamiento (los revisa el gerente).
- Mensajes sugeridos respetuosos; WhatsApp solo si el cliente dio su consentimiento. Reglas de trato visibles para el gestor.

## 4. Seguridad
Roles por módulo · sesión en cookie firmada (8 h, HttpOnly, SameSite=Lax, Secure en producción) · CSRF por Origin/Referer ·
bloqueo tras 5 intentos fallidos (15 min) · validación en el servidor (Pydantic) · auditoría de acciones y accesos denegados ·
expedientes restringidos por rol · sin archivos subidos · a Gemini nunca van nombres, teléfonos, DNI ni montos personales ·
claves solo en variables de entorno.

## 5. Guion de demo (8 minutos)
1. **Asesor**: Panel → Prospectos → registrar un comerciante → registrar contacto (interesado) → «Sugerir mensaje».
2. **Asesor**: «Crear expediente» desde el prospecto → nueva solicitud (formulario de comerciante) → validar documentos →
   «Evaluar ahora» (semáforo explicado) → enviar a evaluación.
3. **Analista**: Riesgos → tomar la solicitud → cerrar evaluación con opinión.
4. **Gerente**: aprobar con comentario → «Registrar crédito desembolsado» → ver cronograma.
5. **Gestor**: Cartera (tramos de atraso) → Alertas preventivas → registrar gestión y compromiso.
6. **Gerente**: Auditoría (todo quedó registrado) · modo oscuro · vista en celular.
7. Cierre: lo anterior de ACTIVA (encuestas, IoT, Random Forest, campañas con IA, chatbot Uku) alimenta el embudo comercial.
