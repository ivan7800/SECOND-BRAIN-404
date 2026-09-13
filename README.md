# SECOND BRAIN 404 v2.3.0 — Retrieval Intelligence

Second Brain local-first para Windows con Obsidian, Docker, RAG híbrido, memoria controlada, grafo de conocimiento, Watch Folder y un pipeline de recuperación auditable.

## Novedades v2.3.0

- **Chunking estructural**: Markdown por encabezados, DOCX por títulos/heading, PDF por página y TXT por líneas.
- **Reranker local opcional** sin dependencias pesadas: cobertura de términos, coincidencias en título/localizador, frase y proximidad.
- Pipeline **Weighted RRF + reranker + MMR**.
- **Citas navegables** desde chat y búsqueda al fragmento exacto y al archivo original.
- **Benchmark RAG automático** con Hit@K, MRR y rango medio.
- Nuevos endpoints `/api/source`, `/api/source/raw` y `/api/benchmark`.
- `Knowledge Inspector` ampliado con score base, rerank, RRF, MMR y rankings léxico/semántico.
- `.env.example` completo para instalaciones limpias.

## Pipeline RAG

```text
Pregunta
  ↓
FTS5 lexical ranking ─────┐
                          ├─→ Weighted RRF
Embeddings semantic rank ─┘
            ↓
   reranker local opcional
            ↓
      score mínimo
            ↓
 MMR + límite por documento
            ↓
 contexto estructural y diverso
            ↓
          LLM
            ↓
 citas navegables al origen
```

Si los embeddings no están disponibles, FTS5 sigue funcionando y se mantienen reranking, MMR, filtros y trazabilidad.

## Configuración Retrieval Intelligence

```env
RAG_TOP_K=6
RAG_CANDIDATE_POOL=50
RAG_RRF_K=60
RAG_RERANKER=local
RAG_RERANK_WEIGHT=0.24
RAG_MMR_LAMBDA=0.72
RAG_MIN_SCORE=0.08
RAG_MAX_PER_DOCUMENT=2
```

Para desactivar el reranker:

```env
RAG_RERANKER=none
```

## Benchmark RAG

La release incluye `benchmarks/rag_queries.json`.

Desde la interfaz:

```text
SEARCH → Benchmark RAG
```

Desde Windows:

```text
RUN-RAG-BENCHMARK.bat
```

También por API:

```text
POST /api/benchmark
```

Cuerpo mínimo:

```json
{"top_k": 5}
```

Métricas:

- **Hit@K**: porcentaje de consultas donde aparece una fuente esperada.
- **MRR**: premia que la fuente correcta aparezca en posiciones altas.
- **Mean rank when hit**: rango medio cuando existe acierto.

Umbrales iniciales: `Hit@K >= 0.80` y `MRR >= 0.65`.

## Citas navegables

Cada fuente conserva ruta, área, localizador, score final, score base, rerank, RRF, MMR y rankings disponibles.

Al pulsar **Abrir fuente**, la interfaz consulta:

```text
GET /api/source?path=...&locator=...
```

**Abrir original** utiliza `/api/source/raw`. Las rutas están restringidas a `INDEX_DIRS` y protegidas contra path traversal.

## Arquitectura del vault

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
├── 50_OUTPUT/
└── 90_SYSTEM/
```

`50_OUTPUT` permanece fuera del índice por defecto.

## Instalación Windows

Requisitos: Docker Desktop y Windows 10/11. WSL2 recomendado.

```text
INSTALL-WINDOWS.bat
```

El instalador crea `.env` desde `.env.example` si no existe, valida Compose, construye el contenedor, inicia la aplicación y comprueba `/api/health`.

Abre:

```text
http://localhost:4040
```

### IA local

```text
START-LOCAL-AI.bat
INSTALL-LOCAL-MODELS.bat
```

Modelos recomendados: `all-minilm` para embeddings y `qwen3:4b` para chat local.

## Watch Folder

```env
AUTO_INDEX=true
WATCH_INTERVAL_SECONDS=15
```

Copia documentos a `brain/00_RAW/INBOX/`. La indexación incremental detecta altas, cambios y eliminaciones.

## Memoria controlada

```env
AUTO_MEMORY_SUGGESTIONS=true
```

La IA puede proponer una memoria, pero no pasa a `40_MEMORY` sin aprobación explícita.

## Seguridad

- Bind a `127.0.0.1:4040` por defecto.
- Sin telemetría.
- API keys en variables de entorno.
- Allow-list y validación real de uploads.
- Protección frente a path traversal.
- Fuentes navegables limitadas a áreas indexables.
- CSP y cabeceras de seguridad.
- Defensa frente a prompt injection documental.
- `50_OUTPUT` excluido del índice por defecto.

No expongas la aplicación directamente a Internet sin autenticación, TLS, autorización y rate limiting.

## Proveedores

### Ollama

```env
CHAT_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
OLLAMA_CHAT_MODEL=qwen3:4b
OLLAMA_EMBED_MODEL=all-minilm
```

### OpenAI para chat + embeddings locales

```env
CHAT_PROVIDER=openai
EMBEDDING_PROVIDER=ollama
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6
```

### Gemini para chat + embeddings locales

```env
CHAT_PROVIDER=gemini
EMBEDDING_PROVIDER=ollama
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.7-flash
```

`AI_PROVIDER` sigue aceptándose como fallback para instalaciones antiguas.

## Formatos indexables

- PDF con capa de texto.
- DOCX.
- Markdown UTF-8.
- TXT UTF-8.

Los PDF escaneados requieren OCR externo.

## QA / Release

```text
TEST-RELEASE.bat
```

La v2.3 añade pruebas de chunking estructural, localizadores, reranker, acceso seguro a fuentes y benchmark, manteniendo compatibilidad con RRF/MMR y fallback FTS5 de v2.2.

## Google Drive + Obsidian

```env
BRAIN_HOST_PATH=G:/Mi unidad/SECOND-BRAIN-404
```

Puedes sincronizar `brain/` con Google Drive y abrir la misma carpeta como Vault de Obsidian.

## Estado

**v2.3.0 — Retrieval Intelligence** es compatible con la base SQLite de v2.2 y no requiere migración de esquema.

## Licencia

MIT License. Consulta `LICENSE`.
