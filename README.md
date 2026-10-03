# SECOND BRAIN 404 v3.0.0 — Knowledge Intelligence

> Tu base de conocimiento privada con IA: deja documentos en una carpeta, indexa y pregunta sobre todo lo que sabes con recuperación híbrida, fuentes navegables y un pipeline RAG auditable.

[![QA](https://github.com/ivan7800/SECOND-BRAIN-404/actions/workflows/qa.yml/badge.svg)](https://github.com/ivan7800/SECOND-BRAIN-404/actions/workflows/qa.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D4)
![License](https://img.shields.io/badge/license-MIT-green)

SECOND BRAIN 404 es un **Second Brain local-first para Windows** con Obsidian, Docker, SQLite/FTS5, búsqueda vectorial local, RAG híbrido, memoria controlada, grafo de conocimiento, Watch Folder y herramientas de diagnóstico del retrieval.

La aplicación escucha en `127.0.0.1` por defecto, no incluye telemetría y puede trabajar completamente en local con Ollama.

## Qué aporta v3.0

- **sqlite-vec** como motor vectorial embebido dentro de la misma base SQLite.
- Fallback automático a búsqueda semántica brute-force y, si no hay embeddings, a **FTS5**.
- Pipeline **FTS5 + vector search + Weighted RRF + reranker + MMR**.
- **RAG Debugger** con candidatos, rankings, backend semántico y latencias por etapa.
- **Citation Verifier** que comprueba referencias `[S1]`, `[S2]` y evidencia léxica asociada.
- Migración automática de embeddings almacenados por v2.x al índice sqlite-vec.
- Ingesta ampliada: **PDF, DOCX, XLSX, PPTX, Markdown, TXT, HTML, CSV, JSON, EPUB y EML**.
- Fuentes navegables para todos los formatos indexables.
- QA automática en **Linux + Windows**, auditoría de dependencias y build Docker.
- Compatibilidad con el vault, memoria y base SQLite de v2.x.

## Pipeline RAG v3

```text
Pregunta
   │
   ├──────────────→ FTS5 lexical ranking ────────┐
   │                                              │
   └→ embedding → sqlite-vec / brute-force ──────┤
                                                  ↓
                                           Weighted RRF
                                                  ↓
                                       reranker local opcional
                                                  ↓
                                             score mínimo
                                                  ↓
                                      MMR + límite/documento
                                                  ↓
                                     contexto diverso + trazable
                                                  ↓
                                                 LLM
                                                  ↓
                                      Citation Verifier + fuentes
```

El diseño evita un punto único de fallo:

1. si sqlite-vec está disponible, se usa búsqueda vectorial local;
2. si el índice vectorial no está listo, se usa el embedding JSON existente;
3. si los embeddings no están disponibles, FTS5 continúa funcionando;
4. reranker, MMR, filtros y trazabilidad siguen disponibles cuando corresponda.

## RAG Debugger

La vista **SEARCH** muestra el recorrido de cada consulta:

```text
lexical candidates    35
semantic candidates   50
fused candidates      67
post threshold        24
selected                6
semantic backend      sqlite-vec
lexical latency       3.2 ms
embedding latency    42.8 ms
semantic latency      1.9 ms
total retrieval      51.6 ms
```

Cada resultado conserva además:

- score final;
- score base;
- RRF;
- rerank;
- MMR;
- ranking FTS;
- ranking semántico;
- ruta y área;
- localizador exacto del fragmento.

## Citation Verifier

Después de generar la respuesta se comprueban las referencias `[Sx]` y el solapamiento entre la afirmación y la evidencia citada.

La API devuelve:

```json
{
  "confidence": "high",
  "claims_checked": 4,
  "supported_claims": 4,
  "unsupported_claims": 0,
  "invalid_references": [],
  "sources_referenced": 3
}
```

El verificador es una **capa heurística de control**, no una prueba lógica de verdad ni un modelo de entailment. Su función es detectar citas ausentes, referencias inexistentes y respuestas débilmente ancladas a las fuentes.

## Formatos indexables

| Formato | Segmentación / localizador |
|---|---|
| Markdown | encabezados + líneas |
| TXT | bloques de líneas |
| PDF | página |
| DOCX | headings + párrafos |
| XLSX | hoja + filas |
| PPTX | diapositiva |
| HTML/HTM | texto estructurado |
| CSV | filas |
| JSON | claves / bloques |
| EPUB | documento interno HTML/XHTML |
| EML | cabeceras + cuerpo del correo |

Los **PDF escaneados sin capa de texto siguen requiriendo OCR externo**. No se simula OCR ni se afirma haber extraído texto cuando el PDF no lo contiene.

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
    ├── database/
    ├── logs/
    └── backups/
```

Por defecto sólo se indexan:

```env
INDEX_DIRS=00_RAW,10_WIKI,20_PROJECTS,40_MEMORY
```

`50_OUTPUT` permanece fuera del índice para evitar que respuestas generadas vuelvan a entrar automáticamente en el RAG.

## Instalación Windows

### Requisitos

- Windows 10/11.
- Docker Desktop.
- WSL2 recomendado.
- Ollama si quieres IA 100 % local.

### Instalación

```text
INSTALL-WINDOWS.bat
```

El instalador prepara `.env`, valida Docker Compose, construye el contenedor, inicia el servicio y comprueba `/api/health`.

Después abre:

```text
http://localhost:4040
```

### Modelos locales

```text
START-LOCAL-AI.bat
INSTALL-LOCAL-MODELS.bat
```

Configuración local recomendada:

```env
CHAT_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
OLLAMA_CHAT_MODEL=qwen3:4b
OLLAMA_EMBED_MODEL=all-minilm
```

## Configuración RAG v3

```env
RAG_TOP_K=6
RAG_CANDIDATE_POOL=50
RAG_RRF_K=60
RAG_RERANKER=local
RAG_RERANK_WEIGHT=0.24
RAG_VECTOR_BACKEND=auto
RAG_MMR_LAMBDA=0.72
RAG_MIN_SCORE=0.08
RAG_MAX_PER_DOCUMENT=2
CITATION_MIN_OVERLAP=0.08
```

`RAG_VECTOR_BACKEND` acepta:

- `auto`: sqlite-vec cuando está disponible y fallback seguro en caso contrario;
- `sqlite-vec`: prioriza el índice vectorial;
- `bruteforce`: usa los embeddings almacenados sin KNN sqlite-vec.

Para desactivar el reranker:

```env
RAG_RERANKER=none
```

## Migración desde v2.x

No necesitas borrar el vault ni la base de datos.

Al abrir una base existente, v3 detecta los embeddings JSON de v2.x y reconstruye el índice sqlite-vec automáticamente cuando la extensión está disponible.

Los documentos, chunks, memorias y FTS5 existentes se conservan.

Si cambias deliberadamente de modelo de embeddings, ejecuta **Reindexar** para regenerar los vectores con el nuevo modelo.

## Watch Folder

```env
AUTO_INDEX=true
WATCH_INTERVAL_SECONDS=15
```

Copia documentos en:

```text
brain/00_RAW/INBOX/
```

El watcher detecta altas, cambios y eliminaciones sin reconstruir toda la biblioteca en cada ciclo.

## Memoria controlada

```env
AUTO_MEMORY_SUGGESTIONS=true
```

La IA puede proponer una memoria, pero una propuesta no entra en `40_MEMORY` hasta que el usuario la aprueba explícitamente desde la interfaz.

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

Por API:

```text
POST /api/benchmark
```

Cuerpo mínimo:

```json
{"top_k": 5}
```

Métricas principales:

- **Hit@K**;
- **MRR**;
- **Mean rank when hit**.

Umbrales iniciales de release:

```text
Hit@K >= 0.80
MRR   >= 0.65
```

## Citas y fuentes navegables

Desde el chat o SEARCH puedes abrir el fragmento que sustentó un resultado:

```text
GET /api/source?path=...&locator=...
```

Y el original:

```text
GET /api/source/raw?path=...
```

Las rutas están restringidas a `INDEX_DIRS` y protegidas contra path traversal.

## Proveedores de chat

### Ollama

```env
CHAT_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
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

`AI_PROVIDER` sigue aceptándose como fallback de compatibilidad para instalaciones antiguas.

## Seguridad

- Bind Docker a `127.0.0.1:4040` por defecto.
- Sin telemetría integrada.
- API keys mediante variables de entorno.
- Allow-list de extensiones.
- Validación de contenido y estructura de archivos.
- Límite de tamaño de uploads.
- Protección frente a path traversal.
- Fuentes limitadas a áreas indexables.
- CSP, `X-Frame-Options`, `nosniff`, `Referrer-Policy` y `Permissions-Policy`.
- Defensa explícita frente a prompt injection documental.
- `50_OUTPUT` excluido del índice por defecto.
- Contenedor con `no-new-privileges` en Docker Compose.

**No expongas directamente la aplicación a Internet** sin añadir autenticación, autorización, TLS y rate limiting.

## QA

Local:

```text
TEST-RELEASE.bat
```

GitHub Actions ejecuta en cada push/PR:

```text
Python 3.12 / Ubuntu
Python 3.12 / Windows
compileall
unittest
pip-audit
Docker build
```

Los tests cubren, entre otras cosas:

- configuración y compatibilidad v2.x;
- seguridad de rutas y uploads;
- fallback FTS5 sin embeddings;
- chunking estructural;
- reranker y MMR;
- benchmark RAG;
- XLSX/PPTX/HTML/CSV/JSON/EML;
- RAG trace;
- Citation Verifier;
- round-trip de sqlite-vec cuando la extensión está disponible.

## Google Drive + Obsidian

Puedes apuntar el vault a una carpeta sincronizada:

```env
BRAIN_HOST_PATH=G:/Mi unidad/SECOND-BRAIN-404
```

Y abrir esa misma carpeta como Vault de Obsidian.

## Documentación técnica

- `ARCHITECTURE.md`: componentes, flujo de datos y decisiones de diseño.
- `SECURITY.md`: modelo de seguridad y reporte de vulnerabilidades.
- `CHANGELOG.md`: historial de versiones.
- `.env.example`: configuración reproducible.

## Estado

**v3.0.0 — Knowledge Intelligence** mantiene la filosofía local-first y hace evolucionar v2.3 sin reescribir su arquitectura estable.

El objetivo de v3 no es acumular funciones: es que búsqueda, evidencia, depuración y mantenimiento sean más rápidos, medibles y confiables.

## Licencia

MIT License. Consulta `LICENSE`.
