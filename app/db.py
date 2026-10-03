import json
import sqlite3
from contextlib import contextmanager

from .vector_store import load_sqlite_vec, upsert_vector, vector_status

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    modified_at REAL NOT NULL,
    source_area TEXT NOT NULL,
    indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    locator TEXT NOT NULL DEFAULT '',
    text TEXT NOT NULL,
    embedding_json TEXT,
    embedding_model TEXT,
    UNIQUE(document_id, chunk_index)
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    chunk_id UNINDEXED,
    text,
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TABLE IF NOT EXISTS vector_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memory_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending','approved','rejected')),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    source_question TEXT NOT NULL DEFAULT '',
    source_answer TEXT NOT NULL DEFAULT '',
    saved_path TEXT
);

CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_model ON chunks(embedding_model);
CREATE INDEX IF NOT EXISTS idx_memory_status ON memory_candidates(status, created_at);
"""


class Database:
    def __init__(self, path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)
        self.vector_sync = self._sync_existing_vectors()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        load_sqlite_vec(conn)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _sync_existing_vectors(self):
        """Migra embeddings JSON de v2.x al índice sqlite-vec sin romper el fallback."""
        with self.connect() as conn:
            if not load_sqlite_vec(conn):
                return {"available": False, "synced": 0, "skipped": True}
            model_row = conn.execute(
                """
                SELECT embedding_model, COUNT(*) AS n
                FROM chunks
                WHERE embedding_json IS NOT NULL AND embedding_model IS NOT NULL
                GROUP BY embedding_model
                ORDER BY n DESC
                LIMIT 1
                """
            ).fetchone()
            if not model_row:
                return {"available": True, "synced": 0, "skipped": True}
            model = model_row["embedding_model"]
            rows = conn.execute(
                "SELECT id,embedding_json FROM chunks WHERE embedding_json IS NOT NULL AND embedding_model=?",
                (model,),
            ).fetchall()
            status = vector_status(conn)
            if status.get("model") == model and status.get("indexed_vectors") == len(rows):
                return {"available": True, "synced": 0, "skipped": True, "model": model}
            synced = 0
            failed = 0
            for row in rows:
                try:
                    vector = json.loads(row["embedding_json"])
                    if upsert_vector(conn, row["id"], vector, model):
                        synced += 1
                except Exception:
                    failed += 1
            return {
                "available": True,
                "synced": synced,
                "failed": failed,
                "skipped": False,
                "model": model,
            }

    def stats(self):
        with self.connect() as conn:
            docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            vectors = conn.execute(
                "SELECT COUNT(*) FROM chunks WHERE embedding_json IS NOT NULL"
            ).fetchone()[0]
            pending = conn.execute(
                "SELECT COUNT(*) FROM memory_candidates WHERE status='pending'"
            ).fetchone()[0]
        return {
            "documents": docs,
            "chunks": chunks,
            "vectors": vectors,
            "memory_pending": pending,
        }
