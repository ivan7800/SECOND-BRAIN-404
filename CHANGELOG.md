# Changelog

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
