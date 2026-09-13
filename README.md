# SECOND BRAIN 404 v2.2.0 — RAG Quality & Reliability

Second Brain local-first para Windows con Obsidian, Docker, RAG híbrido, Watch Folder, grafo de conocimiento y memoria persistente controlada.

## Novedades v2.2.0

- **Weighted Reciprocal Rank Fusion (RRF)** para fusionar búsqueda FTS5 y semántica sin mezclar escalas incompatibles.
- **MMR (Maximal Marginal Relevance)** para reducir chunks redundantes y aumentar diversidad de contexto.
- **Límite por documento** para evitar que una sola fuente monopolice la respuesta.
- **Knowledge Inspector** en la búsqueda: muestra RRF, MMR y posiciones léxica/semántica.
- **Filtro por área** (`00_RAW`, `10_WIKI`, `20_PROJECTS`, `40_MEMORY`).
- **Score mínimo configurable** y pool de candidatos configurable.
- **Defensa frente a prompt injection documental**: las fuentes se tratan explícitamente como datos no confiables.
- **Validación de contenido al subir archivos**: PDF por firma, DOCX por estructura ZIP y TXT/MD como texto UTF-8 no binario.
- `/api/inspect` para auditoría del retrieval.
- `/api/health` expone la configuración efectiva del RAG.
- Suite de regresión ampliada para ranking, diversidad, filtros, seguridad y prompt-injection guard.

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

## Pipeline RAG v2.2

```text
Pregunta
  ↓
FTS5 lexical ranking ─────┐
                          ├─→ Weighted RRF
Embeddings semantic rank ─┘
            ↓
      score mínimo
            ↓
 MMR + límite por documento
            ↓
   contexto diverso y trazable
            ↓
          LLM
```

El modo semántico es opcional. Si los embeddings no están disponibles, la búsqueda continúa funcionando con SQLite FTS5 y aplica igualmente diversidad MMR.

## Ajustes RAG

Variables opcionales:

```env
RAG_TOP_K=6
RAG_CANDIDATE_POOL=50
RAG_RRF_K=60
RAG_MMR_LAMBDA=0.72
RAG_MIN_SCORE=0.08
RAG_MAX_PER_DOCUMENT=2
```

Recomendación: mantener los valores por defecto salvo que tengas un corpus grande y hayas medido la calidad con consultas reales.

## Instalación recomendada en Windows

1. Instala y abre Docker Desktop.
2. Descomprime el proyecto.
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

Modelos recomendados:

- `all-minilm` → embeddings.
- `qwen3:4b` → chat local.

## Watch Folder

```env
AUTO_INDEX=true
WATCH_INTERVAL_SECONDS=15
```

Copia un documento a:

```text
brain/00_RAW/INBOX/
```

El watcher detectará altas, cambios y eliminaciones. `Reindexar` sigue disponible para reconstrucción manual.

## Memoria controlada

```env
AUTO_MEMORY_SUGGESTIONS=true
```

```text
Conversación
   ↓
Candidato de memoria
   ↓
MEMORY
   ├── Guardar memoria → 40_MEMORY
   └── Descartar → no persiste
```

Nunca se convierte automáticamente en memoria permanente sin aprobación.

## Knowledge Inspector

La vista SEARCH muestra para cada resultado:

- score final;
- score RRF normalizado;
- score MMR final de diversidad;
- posición semántica;
- posición FTS5;
- documento, área y localizador.

La misma información se puede consultar por API:

```text
POST /api/inspect
```

Ejemplo de cuerpo:

```json
{
  "query": "cómo recuperar BitLocker",
  "top_k": 8,
  "source_areas": ["10_WIKI", "20_PROJECTS"]
}
```

## Seguridad

- Bind a `127.0.0.1:4040` por defecto.
- Sin telemetría.
- API keys en variables de entorno.
- `.env` ignorado por Git.
- Allow-list de extensiones.
- Validación real del contenido subido.
- Protección de rutas.
- Límite de tamaño.
- CSP y cabeceras de seguridad.
- Defensa explícita frente a instrucciones incrustadas en documentos RAG.
- `50_OUTPUT` no se indexa por defecto.
- No publicar directamente en Internet sin autenticación, TLS, autorización y rate limiting.

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

`CHAT_PROVIDER` controla el modelo conversacional y `EMBEDDING_PROVIDER` controla la recuperación semántica. `AI_PROVIDER` continúa aceptándose como fallback por compatibilidad con instalaciones anteriores.

## Formatos indexables

- PDF con capa de texto.
- DOCX.
- Markdown UTF-8.
- TXT UTF-8.

Los PDF escaneados requieren OCR externo.

## Diagnóstico

```text
RUN-DIAGNOSTIC.bat
```

Comprueba Docker CLI, Docker Engine, Docker Compose, WSL, puerto 4040, espacio libre y API de Second Brain.

## Test de release

```text
TEST-RELEASE.bat
```

Valida Compose, construye la imagen y ejecuta `unittest discover`, incluyendo la suite RAG v2.2.

## Google Drive + Obsidian

Puedes mover `brain/` a una carpeta local sincronizada de Google Drive y abrir la misma ruta como Vault en Obsidian.

```env
BRAIN_HOST_PATH=G:/Mi unidad/SECOND-BRAIN-404
```

```text
Google Drive → sincronización
Obsidian     → edición
Second Brain → RAG + memoria + grafo
Ollama       → IA local
```

## Estado de la release

Versión `2.2.0` centrada en calidad, auditabilidad y resiliencia del retrieval. Mantiene compatibilidad con el flujo v2.1 y el fallback FTS5.

## Licencia

MIT License. Consulta `LICENSE`.
