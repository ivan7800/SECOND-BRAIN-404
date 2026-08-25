import json
import re
from datetime import datetime
from pathlib import Path

from .llm import generate, LLMError
from .retrieval import index_one

def _extract_json(text):
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        text = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start:end+1]
    return json.loads(text)

async def propose_memory(db, s, question, answer):
    if not s.auto_memory_suggestions:
        return None

    prompt = f"""
Analiza esta interacción y decide si contiene una memoria DURADERA que sería útil en futuras sesiones.

Solo son válidos:
- preferencias estables del usuario,
- decisiones de proyecto,
- objetivos persistentes,
- restricciones que deban recordarse,
- hechos de proyecto confirmados.

No guardes:
- información temporal,
- respuestas meramente informativas,
- datos sensibles,
- inferencias no confirmadas,
- contenido que ya sea solo una cita de una fuente.

Devuelve SOLO JSON válido:
{{"save": true|false, "title": "...", "category": "preference|project|goal|rule|general", "content": "..."}}

Si no merece memoria: {{"save": false, "title": "", "category": "general", "content": ""}}

PREGUNTA DEL USUARIO:
{question}

RESPUESTA:
{answer[:6000]}
""".strip()

    try:
        raw = await generate(prompt, s)
        data = _extract_json(raw)
    except Exception:
        return None

    if not data.get("save"):
        return None

    title = str(data.get("title", "")).strip()[:120]
    content = str(data.get("content", "")).strip()[:4000]
    category = str(data.get("category", "general")).strip().lower()
    if category not in {"preference", "project", "goal", "rule", "general"}:
        category = "general"

    if not title or not content:
        return None

    with db.connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO memory_candidates(
                title,content,category,source_question,source_answer
            ) VALUES(?,?,?,?,?)
            """,
            (title, content, category, question[:3000], answer[:5000]),
        )
        return cur.lastrowid

def list_candidates(db, status="pending", limit=50):
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT id,created_at,status,title,content,category,saved_path
            FROM memory_candidates
            WHERE status=?
            ORDER BY id DESC
            LIMIT ?
            """,
            (status, max(1, min(200, limit))),
        ).fetchall()
    return [dict(r) for r in rows]

def _slug(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9áéíóúüñ -]+", "", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text[:70] or "memoria"

async def approve_candidate(db, s, candidate_id):
    with db.connect() as conn:
        row = conn.execute(
            """
            SELECT id,status,title,content,category,created_at
            FROM memory_candidates WHERE id=?
            """,
            (candidate_id,),
        ).fetchone()
        if not row:
            raise KeyError("Candidato no encontrado")
        if row["status"] != "pending":
            raise ValueError("El candidato ya fue procesado")

    folder_map = {
        "preference": "Preferences",
        "project": "Projects",
        "goal": "Goals",
        "rule": "Inbox",
        "general": "Inbox",
    }
    folder = s.brain_root / "40_MEMORY" / folder_map.get(row["category"], "Inbox")
    folder.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = folder / f"{stamp}-{_slug(row['title'])}.md"
    n = 2
    while path.exists():
        path = folder / f"{stamp}-{_slug(row['title'])}-{n}.md"
        n += 1

    body = (
        f"# {row['title']}\n\n"
        f"- Categoría: {row['category']}\n"
        f"- Guardado: {datetime.now().isoformat(timespec='seconds')}\n"
        f"- Estado: confirmado por el usuario\n\n"
        f"{row['content']}\n"
    )
    path.write_text(body, encoding="utf-8")

    with db.connect() as conn:
        conn.execute(
            """
            UPDATE memory_candidates
            SET status='approved', saved_path=?
            WHERE id=?
            """,
            (str(path.relative_to(s.brain_root)).replace("\\", "/"), candidate_id),
        )

    try:
        await index_one(db, s, path)
    except Exception:
        pass

    return str(path.relative_to(s.brain_root)).replace("\\", "/")

def reject_candidate(db, candidate_id):
    with db.connect() as conn:
        row = conn.execute(
            "SELECT status FROM memory_candidates WHERE id=?", (candidate_id,)
        ).fetchone()
        if not row:
            raise KeyError("Candidato no encontrado")
        if row["status"] != "pending":
            raise ValueError("El candidato ya fue procesado")
        conn.execute(
            "UPDATE memory_candidates SET status='rejected' WHERE id=?",
            (candidate_id,),
        )
