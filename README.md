# SECOND BRAIN 404 v2.1.0 — Final

Second Brain local-first para Windows con Obsidian, Docker, RAG, Watch Folder, grafo de conocimiento y memoria persistente controlada.

## Novedades v2.1.0

- **Watch Folder automático**: detecta archivos nuevos/modificados cada 15 s.
- **Indexación incremental real**: usa tamaño + `mtime` y SHA-256 solo cuando hace falta.
- **Eliminación reconciliada**: si borras una fuente, se elimina del índice.
- **Memoria automática controlada**:
  - después de una conversación puede generar una propuesta;
  - la propuesta queda pendiente;
  - solo se persiste cuando pulsas **Guardar memoria**;
  - puedes descartarla.
- **Grafo de conocimiento** con enlaces Obsidian `[[WikiLink]]`.
- **Panel MEMORY** y **panel GRAPH**.
- **00_RAW/INBOX** para arrastrar documentos sin pulsar Reindexar.
- **Instalador Windows**.
- **Diagnóstico Windows**.
- **Release test** con Docker.
- Estado del watcher visible en `/api/health`.

## Arquitectura

```text
brain/
├── 00_RAW/
│   ├── INBOX/
│   ├── PDFs/
│   ├── DOCX/
│   ├── Imagenes/
│   └── Notas/
├── 10_WIKI/
├── 20_PROJECTS/
├── 30_CONTEXT/
├── 40_MEMORY/
│   ├── Inbox/
│   ├── Preferences/
│   ├── Goals/
│   ├── Projects/
│   └── People/
├── 50_OUTPUT/
└── 90_SYSTEM/
```

## Instalación recomendada en Windows

1. Instala y abre Docker Desktop.
2. Descomprime el ZIP.
3. Ejecuta:

```text
INSTALL-WINDOWS.bat
```

4. Abre:

```text
http://localhost:4040
```

### Para activar IA local

Ejecuta:

```text
START-LOCAL-AI.bat
```

y después, solo la primera vez:

```text
INSTALL-LOCAL-MODELS.bat
```

Se descargarán:

- `all-minilm` → embeddings.
- `qwen3:4b` → chat local.

## Diagnóstico

Si algo falla:

```text
RUN-DIAGNOSTIC.bat
```

Comprueba:

- Docker CLI.
- Docker Engine.
- Docker Compose.
- configuración Compose.
- WSL.
- puerto 4040.
- espacio libre.
- API de Second Brain.

## Test de release

Con Docker Desktop iniciado:

```text
TEST-RELEASE.bat
```

Valida Compose, construye la imagen y ejecuta los tests.

## Watch Folder

En `.env`:

```env
AUTO_INDEX=true
WATCH_INTERVAL_SECONDS=15
```

Puedes copiar un documento directamente a:

```text
brain/00_RAW/INBOX/
```

No necesitas pulsar Reindexar: el watcher lo detectará.

`Reindexar` sigue existiendo para una reconstrucción manual completa.

## Memoria controlada

En `.env`:

```env
AUTO_MEMORY_SUGGESTIONS=true
```

Flujo:

```text
Conversación
   ↓
¿hay decisión/preferencia/objetivo duradero?
   ↓
Candidato de memoria
   ↓
MEMORY
   ├── Guardar memoria → 40_MEMORY
   └── Descartar → no persiste
```

Nunca se convierte automáticamente en memoria permanente sin aprobación.

## Grafo

El panel GRAPH analiza Markdown en:

- `10_WIKI`
- `20_PROJECTS`
- `30_CONTEXT`
- `40_MEMORY`

y conecta notas mediante enlaces como:

```md
[[Docker]]
[[Proyecto Second Brain]]
[[BitLocker]]
```

## Google Drive + Obsidian

Puedes mover `brain/` a tu carpeta local sincronizada de Google Drive.

Ejemplo `.env`:

```env
BRAIN_HOST_PATH=G:/Mi unidad/SECOND-BRAIN-404
```

Después abre esa misma carpeta como Vault en Obsidian.

Resultado:

```text
Google Drive → sincronización
Obsidian     → edición
Second Brain → RAG + memoria + grafo
Ollama       → IA local
```

## Seguridad

- `127.0.0.1:4040` por defecto.
- Sin telemetría.
- API keys solo en `.env`.
- `.env` ignorado por Git.
- Upload con allow-list.
- Protección de rutas.
- Límite de tamaño.
- CSP y cabeceras de seguridad.
- `50_OUTPUT` no se indexa por defecto.
- No publicar directamente a Internet sin autenticación/TLS.

## Proveedores

### Ollama

```env
CHAT_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
OLLAMA_CHAT_MODEL=qwen3:4b
OLLAMA_EMBED_MODEL=all-minilm
```

### OpenAI

```env
CHAT_PROVIDER=openai
EMBEDDING_PROVIDER=ollama
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6
```

### Gemini

```env
CHAT_PROVIDER=gemini
EMBEDDING_PROVIDER=ollama
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.7-flash
```

## Formatos indexables

- PDF con capa de texto.
- DOCX.
- Markdown.
- TXT.

Los PDF escaneados requieren OCR externo.

## Estado de la release

Versión `2.1.0` preparada para publicación en GitHub y uso local. Incluye validaciones estáticas, tests unitarios, diagnóstico de entorno y degradación a FTS5 cuando los embeddings no están disponibles.

La comprobación de Docker Desktop debe realizarse también en el PC destino.

## Chat y embeddings independientes

`CHAT_PROVIDER` controla el modelo conversacional y `EMBEDDING_PROVIDER` controla la búsqueda semántica. Actualmente los embeddings soportan `ollama` o `none`. Si se usa `none` o Ollama no está disponible, el buscador sigue funcionando mediante SQLite FTS5.

Por compatibilidad con instalaciones anteriores, `AI_PROVIDER` continúa siendo aceptado como fallback si `CHAT_PROVIDER` no está definido.

## Licencia

MIT License. Consulta `LICENSE`.
