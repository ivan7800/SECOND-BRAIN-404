# Changelog

## 2.1.0
- Release final de la rama 2.1.
- Separados `CHAT_PROVIDER` y `EMBEDDING_PROVIDER`, manteniendo compatibilidad con `AI_PROVIDER`.
- Embeddings configurables como `ollama` o `none`, con fallback léxico FTS5.
- Exclusión mutua de indexación para evitar carreras entre watcher, reindexado manual y memoria aprobada.
- Diagnóstico Windows distingue Second Brain 404 de un proceso ajeno en el puerto 4040.
- Ollama fijado a una versión concreta en Compose para mayor reproducibilidad.
- `SECURITY.md` actualizado a v2.1.0.
- Añadida licencia MIT.
- Suite de tests ampliada.
- Health API informa por separado de proveedor de chat y embeddings.

## 2.1.0-rc1
- Watch Folder automático.
- Indexación incremental por mtime/tamaño.
- Reconciliación de documentos eliminados.
- Memoria automática con aprobación humana.
- Panel MEMORY.
- Grafo Obsidian por WikiLinks.
- Panel GRAPH.
- 00_RAW/INBOX.
- Instalador Windows.
- Diagnóstico PowerShell.
- TEST-RELEASE.bat.
- Health ampliado.
- Tests de grafo.

## 2.0.0
- Docker.
- Obsidian vault.
- SQLite FTS5.
- RAG.
- Embeddings Ollama.
- Chat Ollama/OpenAI/Gemini.
- Upload.
- Fuentes.
- Interfaz responsive.
- Lanzadores Windows.
