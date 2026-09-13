from contextlib import asynccontextmanager
from pathlib import Path
import asyncio
import mimetypes
import threading
import uuid

import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .benchmark import load_cases, run_benchmark
from .config import get_settings, ensure_structure
from .db import Database
from .security import validate_upload, validate_file_content, ensure_inside
from .retrieval import index_all, search, inspect_search, build_rag_prompt
from .sources import resolve_source_path, read_source_fragment
from .llm import generate, LLMError
from .graph import build_graph
from .memory import propose_memory, list_candidates, approve_candidate, reject_candidate
from .watcher import WatchState, watch_loop

VERSION = "2.3.0"
s = get_settings()
ensure_structure(s)
db = Database(s.brain_root / "90_SYSTEM/database/second-brain.db")

jobs = {}
jobs_lock = threading.Lock()
watch_state = WatchState()
project_root = Path(__file__).resolve().parent.parent
benchmark_file = project_root / "benchmarks/rag_queries.json"


@asynccontextmanager
async def lifespan(app):
    task = None
    if s.auto_index:
        task = asyncio.create_task(watch_loop(db, s, watch_state))
    try:
        yield
    finally:
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="Second Brain 404",
    version=VERSION,
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)
    source_areas: list[str] | None = None


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=8000)
    top_k: int | None = Field(default=None, ge=1, le=20)
    source_areas: list[str] | None = None


class BenchmarkCaseRequest(BaseModel):
    id: str | None = Field(default=None, max_length=120)
    query: str = Field(min_length=2, max_length=2000)
    expected_paths: list[str] = Field(min_length=1, max_length=20)
    source_areas: list[str] | None = None


class BenchmarkRequest(BaseModel):
    top_k: int = Field(default=5, ge=1, le=20)
    cases: list[BenchmarkCaseRequest] | None = Field(default=None, max_length=50)


def normalize_source_areas(values):
    if not values:
        return None
    allowed = set(s.index_dirs)
    clean = []
    for value in values[:20]:
        area = str(value).strip()
        if area not in allowed:
            raise HTTPException(400, f"Área de conocimiento no válida: {area}")
        if area not in clean:
            clean.append(area)
    return clean or None


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
        "base-uri 'self'; frame-ancestors 'none'"
    )
    return response


@app.get("/api/health")
async def health():
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            r = await client.get(f"{s.ollama_base_url}/api/version")
            ollama_ok = r.status_code == 200
    except Exception:
        pass

    model = {
        "ollama": s.ollama_chat_model,
        "openai": s.openai_model,
        "gemini": s.gemini_model,
    }.get(s.chat_provider, "")

    return {
        "status": "ok",
        "version": VERSION,
        "provider": s.chat_provider,
        "chat_provider": s.chat_provider,
        "embedding_provider": s.embedding_provider,
        "chat_model": model,
        "embedding_model": s.ollama_embed_model if s.embedding_provider == "ollama" else None,
        "ollama": ollama_ok,
        "auto_index": s.auto_index,
        "watch_interval_seconds": s.watch_interval_seconds,
        "watcher": watch_state.as_dict(),
        "rag": {
            "strategy": "weighted_rrf+optional_local_rerank+mmr",
            "top_k": s.rag_top_k,
            "candidate_pool": s.rag_candidate_pool,
            "rrf_k": s.rag_rrf_k,
            "reranker": s.rag_reranker,
            "rerank_weight": s.rag_rerank_weight,
            "mmr_lambda": s.rag_mmr_lambda,
            "min_score": s.rag_min_score,
            "max_per_document": s.rag_max_per_document,
            "chunking": "structural",
        },
        **db.stats(),
    }


@app.get("/api/documents")
async def documents(limit: int = 100):
    limit = max(1, min(500, limit))
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT path,title,size_bytes,source_area,indexed_at
            FROM documents
            ORDER BY indexed_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return {"items": [dict(r) for r in rows]}


def set_job(job_id, patch):
    with jobs_lock:
        jobs.setdefault(job_id, {}).update(patch)


async def run_index(job_id):
    set_job(job_id, {"status": "running"})

    def progress(data):
        set_job(job_id, {"progress": data})

    try:
        result = await index_all(db, s, progress)
        set_job(job_id, {"status": "done", "result": result})
    except Exception as exc:
        set_job(job_id, {"status": "error", "error": str(exc)})


@app.post("/api/index")
async def start_index(background_tasks: BackgroundTasks):
    job_id = uuid.uuid4().hex[:12]
    set_job(job_id, {"status": "queued", "progress": {}})
    background_tasks.add_task(run_index, job_id)
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/jobs/{job_id}")
async def job_status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Trabajo no encontrado")
        return dict(job)


@app.post("/api/search")
async def api_search(req: SearchRequest):
    areas = normalize_source_areas(req.source_areas)
    return await inspect_search(db, s, req.query, req.top_k, areas)


@app.post("/api/inspect")
async def api_inspect(req: SearchRequest):
    areas = normalize_source_areas(req.source_areas)
    return await inspect_search(db, s, req.query, req.top_k, areas)


@app.get("/api/source")
async def api_source(path: str, locator: str = ""):
    try:
        source = resolve_source_path(s, path)
        text = read_source_fragment(source, locator)
    except FileNotFoundError:
        raise HTTPException(404, "Fuente no encontrada")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {
        "path": str(source.relative_to(s.brain_root)).replace("\\", "/"),
        "locator": locator,
        "text": text,
    }


@app.get("/api/source/raw")
async def api_source_raw(path: str):
    try:
        source = resolve_source_path(s, path)
    except FileNotFoundError:
        raise HTTPException(404, "Fuente no encontrada")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    media_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
    return FileResponse(source, media_type=media_type)


@app.post("/api/benchmark")
async def api_benchmark(req: BenchmarkRequest):
    if req.cases:
        cases = []
        for case in req.cases:
            areas = normalize_source_areas(case.source_areas)
            cases.append({
                "id": case.id,
                "query": case.query,
                "expected_paths": case.expected_paths,
                "source_areas": areas,
            })
    else:
        try:
            cases = load_cases(benchmark_file)
        except (OSError, ValueError) as exc:
            raise HTTPException(500, f"Benchmark no disponible: {exc}")
    return await run_benchmark(db, s, cases, req.top_k)


async def create_memory_candidate(question, answer):
    try:
        await propose_memory(db, s, question, answer)
    except Exception:
        pass


@app.post("/api/chat")
async def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    areas = normalize_source_areas(req.source_areas)
    sources = await search(db, s, req.question, req.top_k, areas)
    if not sources:
        return {
            "answer": "No he encontrado contexto suficiente. Indexa documentos, cambia el filtro de área o reformula la pregunta.",
            "sources": [],
        }

    try:
        answer = await generate(build_rag_prompt(req.question, sources), s)
    except LLMError as exc:
        raise HTTPException(503, str(exc))

    if s.auto_memory_suggestions:
        background_tasks.add_task(create_memory_candidate, req.question, answer)

    public_sources = [
        {
            "ref": f"S{i}",
            "path": x["path"],
            "title": x["title"],
            "source_area": x["source_area"],
            "locator": x["locator"],
            "score": x["score"],
            "base_score": x.get("base_score"),
            "rerank": x.get("rerank"),
            "rrf": x.get("rrf"),
            "mmr": x.get("mmr"),
            "semantic": x.get("semantic"),
            "lexical_rank": x.get("lexical_rank"),
            "semantic_rank": x.get("semantic_rank"),
            "preview": x["text"][:500],
        }
        for i, x in enumerate(sources, 1)
    ]
    return {"answer": answer, "sources": public_sources}


@app.get("/api/graph")
async def graph():
    return build_graph(s.brain_root)


@app.get("/api/memory/candidates")
async def memory_candidates(status: str = "pending", limit: int = 50):
    if status not in {"pending", "approved", "rejected"}:
        raise HTTPException(400, "Estado no válido")
    return {"items": list_candidates(db, status, limit)}


@app.post("/api/memory/candidates/{candidate_id}/approve")
async def memory_approve(candidate_id: int):
    try:
        path = await approve_candidate(db, s, candidate_id)
        return {"ok": True, "path": path}
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@app.post("/api/memory/candidates/{candidate_id}/reject")
async def memory_reject(candidate_id: int):
    try:
        reject_candidate(db, candidate_id)
        return {"ok": True}
    except KeyError as exc:
        raise HTTPException(404, str(exc))
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    try:
        name = validate_upload(file.filename or "documento")
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    target_dir = s.brain_root / "00_RAW/INBOX"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = ensure_inside(s.brain_root, target_dir / name)
    if target.exists():
        stem, suffix = target.stem, target.suffix
        n = 2
        while target.exists():
            target = target_dir / f"{stem}-{n}{suffix}"
            n += 1

    max_bytes = s.max_upload_mb * 1024 * 1024
    written = 0
    try:
        with target.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    out.close()
                    target.unlink(missing_ok=True)
                    raise HTTPException(413, f"El archivo supera {s.max_upload_mb} MB")
                out.write(chunk)
    finally:
        await file.close()

    try:
        validate_file_content(target)
    except ValueError as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(415, str(exc))

    return {
        "ok": True,
        "path": str(target.relative_to(s.brain_root)).replace("\\", "/"),
        "size_bytes": written,
        "message": "Archivo validado y guardado en 00_RAW/INBOX. El Watch Folder lo indexará automáticamente.",
    }


web_root = project_root / "web"
app.mount("/assets", StaticFiles(directory=web_root / "assets"), name="assets")


@app.get("/")
async def root():
    return FileResponse(web_root / "index.html")
