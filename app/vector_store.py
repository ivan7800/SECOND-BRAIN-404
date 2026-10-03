import struct

try:
    import sqlite_vec
except Exception:  # pragma: no cover - optional runtime capability
    sqlite_vec = None

_DIM_KEY = "vector_dimension"
_MODEL_KEY = "vector_model"
_TABLE = "chunk_vectors"


def serialize_f32(vector):
    return struct.pack(f"{len(vector)}f", *vector)


def load_sqlite_vec(conn):
    if sqlite_vec is None:
        return False
    try:
        conn.execute("SELECT vec_version()")
        return True
    except Exception:
        pass
    try:
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        conn.execute("SELECT vec_version()")
        return True
    except Exception:
        try:
            conn.enable_load_extension(False)
        except Exception:
            pass
        return False


def _meta(conn, key):
    row = conn.execute("SELECT value FROM vector_metadata WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


def _set_meta(conn, key, value):
    conn.execute(
        "INSERT INTO vector_metadata(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, str(value)),
    )


def ensure_vector_table(conn, dimension, model):
    if dimension <= 0 or not load_sqlite_vec(conn):
        return False
    current_dim = _meta(conn, _DIM_KEY)
    current_model = _meta(conn, _MODEL_KEY)
    if current_dim and (int(current_dim) != int(dimension) or current_model != model):
        conn.execute(f"DROP TABLE IF EXISTS {_TABLE}")
        conn.execute("DELETE FROM vector_metadata WHERE key IN (?,?)", (_DIM_KEY, _MODEL_KEY))
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS {_TABLE} USING vec0("
        f"embedding float[{int(dimension)}] distance_metric=cosine)"
    )
    _set_meta(conn, _DIM_KEY, int(dimension))
    _set_meta(conn, _MODEL_KEY, model)
    return True


def upsert_vector(conn, chunk_id, vector, model):
    if not ensure_vector_table(conn, len(vector), model):
        return False
    payload = serialize_f32(vector)
    conn.execute(f"DELETE FROM {_TABLE} WHERE rowid=?", (int(chunk_id),))
    conn.execute(
        f"INSERT INTO {_TABLE}(rowid, embedding) VALUES(?,?)",
        (int(chunk_id), payload),
    )
    return True


def delete_vectors(conn, chunk_ids):
    ids = [int(x) for x in chunk_ids]
    if not ids or not load_sqlite_vec(conn):
        return
    try:
        for chunk_id in ids:
            conn.execute(f"DELETE FROM {_TABLE} WHERE rowid=?", (chunk_id,))
    except Exception:
        pass


def vector_search(conn, query_vector, limit, model):
    if not query_vector or not load_sqlite_vec(conn):
        return {}, "unavailable"
    if _meta(conn, _DIM_KEY) != str(len(query_vector)) or _meta(conn, _MODEL_KEY) != model:
        return {}, "not_ready"
    try:
        rows = conn.execute(
            f"SELECT rowid, distance FROM {_TABLE} "
            "WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
            (serialize_f32(query_vector), int(limit)),
        ).fetchall()
    except Exception:
        return {}, "error"
    scores = {
        int(row[0]): max(0.0, min(1.0, 1.0 - float(row[1])))
        for row in rows
    }
    return scores, "sqlite-vec"


def vector_status(conn):
    available = load_sqlite_vec(conn)
    dimension = _meta(conn, _DIM_KEY)
    model = _meta(conn, _MODEL_KEY)
    count = 0
    if available:
        try:
            count = int(conn.execute(f"SELECT COUNT(*) FROM {_TABLE}").fetchone()[0])
        except Exception:
            pass
    return {
        "available": available,
        "backend": "sqlite-vec" if available else "bruteforce",
        "dimension": int(dimension) if dimension and dimension.isdigit() else None,
        "model": model,
        "indexed_vectors": count,
    }
