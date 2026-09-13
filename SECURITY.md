# Seguridad

Second Brain 404 v2.3.0 está diseñado para uso local.

Controles incluidos:

- Bind a localhost por defecto.
- Sin telemetría.
- Claves por variables de entorno.
- Upload con allow-list y validación del contenido real.
- Protección frente a path traversal.
- Tamaño máximo configurable.
- CSP, `X-Frame-Options`, `nosniff` y política de permisos.
- `50_OUTPUT` excluido de indexación por defecto.
- Fuentes navegables restringidas a `INDEX_DIRS`.
- `/api/source/raw` no permite navegar fuera del vault ni abrir áreas no indexables.
- Los documentos RAG se tratan como datos no confiables: sus instrucciones nunca deben modificar el comportamiento del asistente.
- El benchmark de retrieval no envía contenido a servicios externos por sí mismo; utiliza el proveedor de embeddings configurado por el usuario.

## Modelo de amenazas

El sistema reduce riesgos de archivos con extensión falsificada, path traversal y prompt injection documental. No pretende ser un servicio multiusuario ni una aplicación preparada para exposición pública.

Si se publica en una red o Internet, añade autenticación, TLS, autorización, rate limiting, auditoría y gestión profesional de secretos.
