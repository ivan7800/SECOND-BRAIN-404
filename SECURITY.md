# Seguridad

Second Brain 404 v2.2.0 está diseñado para uso local.

Controles incluidos:

- Bind a localhost.
- Sin telemetría.
- Claves por variables de entorno.
- Upload con allow-list.
- Validación de contenido después de la subida:
  - firma `%PDF-` para PDF;
  - estructura ZIP/DOCX y `word/document.xml` para DOCX;
  - rechazo de NUL/binario y validación UTF-8 para Markdown/TXT.
- Protección frente a path traversal.
- Tamaño máximo configurable.
- CSP, `X-Frame-Options`, `nosniff` y política de permisos.
- `50_OUTPUT` excluido de indexación por defecto.
- Prompt RAG con separación explícita entre instrucciones del sistema y datos documentales.
- Las fuentes recuperadas se consideran contenido no confiable y no pueden redefinir el rol del asistente.

## Límites del modelo de seguridad

Second Brain 404 no pretende ser un servicio público multiusuario. Si se publica en LAN, VPN o Internet, añade como mínimo:

- autenticación fuerte;
- TLS;
- autorización por usuario/colección;
- rate limiting;
- gestión profesional de secretos;
- logging y alertas;
- aislamiento adicional de archivos y procesos;
- revisión específica de riesgos de prompt injection para tu entorno.
