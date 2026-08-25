import asyncio
import hashlib
import json
import re

_INDEX_LOCK = asyncio.Lock()

from .extractors import SUPPORTED, extract_sections, chunk_sections
from .embeddings import embed, cosine, EmbeddingError

def _embedding_model_name(s):
    if s.embedding_provider == "ollama":
        return s.ollama_embed_model
    return s.embedding_provider

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def iter_indexable_paths(s):
    for dirname in s.index_dirs:
        folder = s.brain_root / dirname
        if folder.exists():
            for path in folder.rglob("*"):
                if path.is_file() and path.suffix.lower() in SUPPORTED:
                    yield path

async def _embed_batched(texts, s, batch_size=16):
    out = []
    for i in range(0, len(texts), batch_size):
        out.extend(await embed(texts[i:i+batch_size], s))
    return out

async def index_all(db, s, progress=None):
    async with _INDEX_LOCK:
        return await _index_all_unlocked(db, s, progress)

async def _index_all_unlocked(db, s, progress=None):
    paths = sorted(iter_indexable_paths(s))
    result = {
        "total": len(paths),
        "indexed": 0,
        "skipped": 0,
        "failed": 0,
        "embeddings_failed": 0,
        "removed": 0,
    }

    for n, path in enumerate(paths, 1):
        if progress:
            progress({
                "phase": "indexing",
                "current": n,
                "total": len(paths),
                "file": str(path.relative_to(s.brain_root)),
            })
        try:
            changed, embed_failed = await _index_one_unlocked(db, s, path)
            result["indexed" if changed else "skipped"] += 1
            if embed_failed:
                result["embeddings_failed"] += 1
        except Exception:
            result["failed"] += 1

    result["removed"] = reconcile_missing(db, s)

    if progress:
        progress({"phase": "done", **result})
    return result

async def index_changed(db, s):
    async with _INDEX_LOCK:
        return await _index_changed_unlocked(db, s)

async def _index_changed_unlocked(db, s):
    changed_paths = []
    with db.connect() as conn:
        known = {
            row["path"]: (int(row["size_bytes"]), float(row["modified_at"]))
            for row in conn.execute(
                "SELECT path,size_bytes,modified_at FROM documents"
            ).fetchall()
        }

    current = set()
    for path in iter_indexable_paths(s):
        rel = str(path.relative_to(s.brain_root)).replace("\\", "/")
        current.add(rel)
        stat = path.stat()
        old = known.get(rel)
        if old is None or old[0] != stat.st_size or abs(old[1] - stat.st_mtime) > 0.001:
            changed_paths.append(path)

    result = {"changed": 0, "failed": 0, "embeddings_failed": 0, "removed": 0}
    for path in changed_paths:
        try:
            changed, embed_failed = await _index_one_unlocked(db, s, path)
            if changed:
                result["changed"] += 1
            if embed_failed:
                result["embeddings_failed"] += 1
        except Exception:
            result["failed"] += 1

    result["removed"] = reconcile_missing(db, s, current=current)
    return result

def reconcile_missing(db, s, current=None):
    if current is None:
        current = {
            str(p.relative_to(s.brain_root)).replace("\\", "/")
            for p in iter_indexable_paths(s)
        }
    removed = 0
    with db.connect() as conn:
        rows = conn.execute("SELECT id,path FROM documents").fetchall()
        for row in rows:
            if row["path"] in current:
                continue
            chunk_ids = conn.execute(
                "SELECT id FROM chunks WHERE document_id=?", (row["id"],)
            ).fetchall()
            for item in chunk_ids:
                conn.execute("DELETE FROM chunks_fts WHERE chunk_id=?", (item["id"],))
            conn.execute("DELETE FROM documents WHERE id=?", (row["id"],))
            removed += 1
    return removed

async def index_one(db, s, path):
    async with _INDEX_LOCK:
        return await _index_one_unlocked(db, s, path)

async def _index_one_unlocked(db, s, path):
    rel = str(path.relative_to(s.brain_root)).replace("\\", "/")
    digest = sha256_file(path)
    stat = path.stat()

    with db.connect() as conn:
        row = conn.execute(
            "SELECT id,sha256 FROM documents WHERE path=?", (rel,)
        ).fetchone()
        if row and row["sha256"] == digest:
            missing = conn.execute(
                "SELECT id,text FROM chunks WHERE document_id=? AND embedding_json IS NULL",
                (row["id"],),
            ).fetchall()
            if not missing:
                return False, False
            try:
                vectors = await _embed_batched([r["text"] for r in missing], s)
                for r, vec in zip(missing, vectors):
                    conn.execute(
                        "UPDATE chunks SET embedding_json=?,embedding_model=? WHERE id=?",
                        (json.dumps(vec), _embedding_model_name(s), r["id"]),
                    )
                return False, False
            except EmbeddingError:
                return False, True

    sections = await asyncio.to_thread(extract_sections, path)
    chunks = chunk_sections(sections, s.chunk_size, s.chunk_overlap)
    if not chunks:
        raise ValueError("Documento sin texto extraíble")

    vectors = None
    embed_failed = False
    try:
        vectors = await _embed_batched([c["text"] for c in chunks], s)
    except EmbeddingError:
        embed_failed = True

    source_area = path.relative_to(s.brain_root).parts[0]

    with db.connect() as conn:
        old = conn.execute(
            "SELECT id FROM documents WHERE path=?", (rel,)
        ).fetchone()
        if old:
            ids = conn.execute(
                "SELECT id FROM chunks WHERE document_id=?", (old["id"],)
            ).fetchall()
            for item in ids:
                conn.execute("DELETE FROM chunks_fts WHERE chunk_id=?", (item["id"],))
            conn.execute("DELETE FROM documents WHERE id=?", (old["id"],))

        cur = conn.execute(
            """
            INSERT INTO documents(path,title,sha256,size_bytes,modified_at,source_area)
            VALUES(?,?,?,?,?,?)
            """,
            (rel, path.name, digest, stat.st_size, stat.st_mtime, source_area),
        )
        doc_id = cur.lastrowid

        for i, chunk in enumerate(chunks):
            vec_json = json.dumps(vectors[i]) if vectors else None
            cur2 = conn.execute(
                """
                INSERT INTO chunks(
                    document_id,chunk_index,locator,text,embedding_json,embedding_model
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    doc_id,
                    i,
                    chunk["locator"],
                    chunk["text"],
                    vec_json,
                    _embedding_model_name(s) if vectors else None,
                ),
            )
            conn.execute(
                "INSERT INTO chunks_fts(chunk_id,text) VALUES(?,?)",
                (cur2.lastrowid, chunk["text"]),
            )

    return True, embed_failed

def _fts_query(text):
    tokens = re.findall(r"[\wÀ-ÿ]{2,}", text, flags=re.UNICODE)
    return " OR ".join(f'"{t}"' for t in tokens[:12])

async def search(db, s, query, top_k=None):
    top_k = top_k or s.rag_top_k
    lexical = {}

    with db.connect() as conn:
        fts = _fts_query(query)
        if fts:
            try:
                rows = conn.execute(
                    """
                    SELECT CAST(chunk_id AS INTEGER) chunk_id, bm25(chunks_fts) rank
                    FROM chunks_fts
                    WHERE chunks_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (fts, max(top_k * 5, 20)),
                ).fetchall()
                for row in rows:
                    lexical[int(row["chunk_id"])] = (
                        1.0 / (1.0 + abs(float(row["rank"])))
                    )
            except Exception:
                pass

        rows = conn.execute(
            """
            SELECT
                c.id,c.text,c.locator,c.embedding_json,
                d.path,d.title,d.source_area
            FROM chunks c
            JOIN documents d ON d.id=c.document_id
            """
        ).fetchall()

    semantic = {}
    try:
        qvec = (await embed([query], s))[0]
        for row in rows:
            if row["embedding_json"]:
                try:
                    semantic[int(row["id"])] = max(
                        0.0, cosine(qvec, json.loads(row["embedding_json"]))
                    )
                except Exception:
                    pass
    except EmbeddingError:
        pass

    scored = []
    has_semantic = bool(semantic)

    for row in rows:
        cid = int(row["id"])
        lex = lexical.get(cid, 0.0)
        sem = semantic.get(cid, 0.0)
        score = (
            sem * 0.78 + min(1.0, lex * 8.0) * 0.22
            if has_semantic
            else min(1.0, lex * 8.0)
        )
        if score <= 0:
            continue
        scored.append({
            "chunk_id": cid,
            "score": round(score, 4),
            "semantic": round(sem, 4),
            "lexical": round(lex, 4),
            "path": row["path"],
            "title": row["title"],
            "source_area": row["source_area"],
            "locator": row["locator"],
            "text": row["text"],
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]

def build_rag_prompt(question, sources):
    context = []
    for i, src in enumerate(sources, 1):
        context.append(
            f"[S{i}] {src['path']} — {src['locator']}\n{src['text']}"
        )
    joined = "\n\n".join(context) if context else "(Sin contexto recuperado.)"

    return f"""
Responde en español usando SOLO el contexto recuperado.
Si no es suficiente, indícalo.
No inventes datos.
Cita afirmaciones mediante [S1], [S2], etc.
Usa una referencia solo si realmente respalda la afirmación.

PREGUNTA:
{question}

CONTEXTO:
{joined}

RESPUESTA:
""".strip()
