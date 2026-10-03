# Changelog

## 3.0.0 — Knowledge Intelligence
- Añadido backend vectorial local con `sqlite-vec` y distancia coseno.
- Migración automática de embeddings JSON de v2.x al índice vectorial de v3.
- Fallback resiliente `sqlite-vec → brute-force → FTS5` según disponibilidad.
- Pipeline actualizado a `FTS5 + vector search + Weighted RRF + reranker + MMR`.
- Añadido RAG Debugger con candidatos por etapa, backend semántico y latencias.
- Añadido Citation Verifier para referencias `[Sx]`, referencias inválidas y soporte léxico.
- Chat devuelve `citation_report` y `retrieval_trace` además de las fuentes.
- Ingesta ampliada a XLSX, PPTX, HTML/HTM, CSV, JSON, EPUB y EML.
- Navegación de fuentes ampliada a todos los formatos indexables.
- Validación de uploads reforzada para contenedores Office/EPUB, JSON y EML.
- Configuración nueva: `RAG_VECTOR_BACKEND` y `CITATION_MIN_OVERLAP`.
- Interfaz renovada como `Knowledge Intelligence v3.0` y `RAG Debugger`.
- Añadida suite de tests específica de v3, incluido round-trip sqlite-vec cuando está disponible.
- Añadido GitHub Actions QA para Windows/Linux, `pip-audit` y Docker build.
- README reescrito para instalación, migración, seguridad, formatos y arquitectura v3.

## 2.3.0 — Retrieval Intelligence
- Chunking estructural para Markdown, DOCX y PDF con localizadores preservados.
- Reranker local opcional basado en cobertura, título, frase y proximidad.
- Pipeline `Weighted RRF + optional rerank + MMR`.
- Citas navegables desde chat y búsqueda.
- Nuevos endpoints `/api/source` y `/api/source/raw`.
- Benchmark RAG reproducible con Hit@K, MRR y rango medio.
- Nuevo endpoint `/api/benchmark` y botón `Benchmark RAG` en SEARCH.
- Añadido `benchmarks/rag_queries.json` como smoke benchmark inicial.
- Añadido `RUN-RAG-BENCHMARK.bat`.
- Añadido `.env.example` completo para instalaciones limpias.
- Health API expone reranker, peso y chunking efectivo.
- Suite v2.3 añadida; mantiene compatibilidad con tests v2.1/v2.2.

## 2.2.0 — RAG Quality & Reliability
- Weighted Reciprocal Rank Fusion (RRF).
- MMR para reducir redundancia.
- Límite por documento.
- Knowledge Inspector.
- Filtro por áreas.
- Score mínimo y pool de candidatos configurables.
- Defensa frente a prompt injection documental.
- Validación de contenido de uploads.
- `/api/inspect` y diagnóstico RAG en `/api/health`.

## 2.1.0
- Release final de la rama 2.1.
- Separados `CHAT_PROVIDER` y `EMBEDDING_PROVIDER`, manteniendo compatibilidad con `AI_PROVIDER`.
- Embeddings configurables como `ollama` o `none`, con fallback léxico FTS5.
- Exclusión mutua de indexación para evitar carreras entre watcher, reindexado manual y memoria aprobada.
- Diagnóstico Windows, licencia MIT y suite de tests ampliada.

## 2.0.0
- Docker, Obsidian vault, SQLite FTS5, RAG, embeddings Ollama.
- Chat Ollama/OpenAI/Gemini, upload, fuentes e interfaz responsive.
