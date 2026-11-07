# Mejoras futuras (fuera del alcance actual)

Ideas que surgen durante el desarrollo y que NO se implementan para respetar los cinco objetivos.

- Eliminar encuestas (con registro de quién y por qué), por ahora solo se editan.
- Asignar asesores específicos a cada bloque (hoy cualquier asesor registra en cualquier bloque abierto).
- Historial de cambios de cada encuesta (quién cambió qué campo).
- Revisar el diagnóstico con la app cerrada (tareas en segundo plano o notificaciones push con Firebase Cloud Messaging).
- Publicar el backend en la nube de forma permanente para no depender de una laptop encendida.

- **Reentrenar el Random Forest con campañas reales**: guardar qué campaña tomó cada cliente y reemplazar el dataset sintético por ese historial.

- **Chatbot en WhatsApp real** (API de WhatsApp Business de Meta): requiere cuenta verificada y puede tener costo.

## ACTIVA 360° (pendiente, fuera de lo construido)

- **Subir documentos** (DNI, recibos) a un almacenamiento seguro (p. ej. Supabase Storage con acceso firmado): hoy es lista de control.
- **Tarifario oficial**: reemplazar los productos de demostración por los de la entidad (tasas, comisiones, seguros, TCEA).
- **Reprogramación automática del cronograma** al aprobar una reprogramación (hoy se registra la decisión y los términos se cargan en el sistema oficial).
- **Integración con el core bancario y centrales de riesgo** (SBS, Equifax/Sentinel) con convenio y autorización del cliente.
- **Avisos externos automáticos** (SMS/WhatsApp Business) con consentimiento: pueden tener costo.
- **Sectores y segmentos editables desde la web** por el gerente (hoy en `catalogos.py`).
- **Reentrenar el Random Forest** con los segmentos nacionales y el historial real de conversiones.
- **Chatbot Uku nacional**: oficios y textos para todas las regiones.
- **Doble factor de autenticación** para gerentes.

