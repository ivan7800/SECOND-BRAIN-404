from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    brain_root: Path
    chat_provider: str
    embedding_provider: str
    ollama_base_url: str
    ollama_chat_model: str
    ollama_embed_model: str
    openai_api_key: str
    openai_model: str
    gemini_api_key: str
    gemini_model: str
    rag_top_k: int
    rag_candidate_pool: int
    rag_rrf_k: int
    rag_mmr_lambda: float
    rag_min_score: float
    rag_max_per_document: int
    rag_reranker: str
    rag_rerank_weight: float
    chunk_size: int
    chunk_overlap: int
    max_upload_mb: int
    index_dirs: tuple[str, ...]
    auto_index: bool
    watch_interval_seconds: int
    auto_memory_suggestions: bool


def _ival(name, default, lo, hi):
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(lo, min(hi, value))


def _fval(name, default, lo, hi):
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(lo, min(hi, value))


def _bval(name, default):
    raw = os.getenv(name, "true" if default else "false").strip().lower()
    return raw in {"1", "true", "yes", "on", "si", "sí"}


def _choice(name, default, allowed):
    value = os.getenv(name, default).strip().lower()
    return value if value in allowed else default


def get_settings():
    root = Path(os.getenv("BRAIN_ROOT", "./brain")).resolve()
    dirs = tuple(
        x.strip()
        for x in os.getenv(
            "INDEX_DIRS", "00_RAW,10_WIKI,20_PROJECTS,40_MEMORY"
        ).split(",")
        if x.strip()
    )
    return Settings(
        brain_root=root,
        chat_provider=os.getenv("CHAT_PROVIDER", os.getenv("AI_PROVIDER", "ollama")).lower().strip(),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "ollama").lower().strip(),
        ollama_base_url=os.getenv(
            "OLLAMA_BASE_URL", "http://host.docker.internal:11434"
        ).rstrip("/"),
        ollama_chat_model=os.getenv("OLLAMA_CHAT_MODEL", "qwen3:4b"),
        ollama_embed_model=os.getenv("OLLAMA_EMBED_MODEL", "all-minilm"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6"),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.7-flash"),
        rag_top_k=_ival("RAG_TOP_K", 6, 1, 20),
        rag_candidate_pool=_ival("RAG_CANDIDATE_POOL", 50, 10, 250),
        rag_rrf_k=_ival("RAG_RRF_K", 60, 10, 200),
        rag_mmr_lambda=_fval("RAG_MMR_LAMBDA", 0.72, 0.05, 1.0),
        rag_min_score=_fval("RAG_MIN_SCORE", 0.08, 0.0, 1.0),
        rag_max_per_document=_ival("RAG_MAX_PER_DOCUMENT", 2, 1, 10),
        rag_reranker=_choice("RAG_RERANKER", "local", {"local", "none"}),
        rag_rerank_weight=_fval("RAG_RERANK_WEIGHT", 0.24, 0.0, 0.60),
        chunk_size=_ival("CHUNK_SIZE", 1400, 400, 5000),
        chunk_overlap=_ival("CHUNK_OVERLAP", 220, 0, 1000),
        max_upload_mb=_ival("MAX_UPLOAD_MB", 50, 1, 500),
        index_dirs=dirs,
        auto_index=_bval("AUTO_INDEX", True),
        watch_interval_seconds=_ival("WATCH_INTERVAL_SECONDS", 15, 5, 3600),
        auto_memory_suggestions=_bval("AUTO_MEMORY_SUGGESTIONS", True),
    )


def ensure_structure(s):
    folders = [
        "00_RAW/INBOX", "00_RAW/PDFs", "00_RAW/DOCX", "00_RAW/Imagenes", "00_RAW/Notas",
        "10_WIKI/Conceptos", "10_WIKI/Personas", "10_WIKI/Tecnologia", "10_WIKI/Referencias",
        "20_PROJECTS/Software", "20_PROJECTS/Novelas", "20_PROJECTS/Sistemas",
        "30_CONTEXT/Prompts", "30_CONTEXT/Skills", "30_CONTEXT/Templates", "30_CONTEXT/Rules",
        "40_MEMORY/Inbox", "40_MEMORY/Preferences", "40_MEMORY/Goals",
        "40_MEMORY/Projects", "40_MEMORY/People",
        "50_OUTPUT/Documents", "50_OUTPUT/Reports", "50_OUTPUT/Code", "50_OUTPUT/Exports",
        "90_SYSTEM/database", "90_SYSTEM/logs", "90_SYSTEM/backups",
    ]
    for folder in folders:
        (s.brain_root / folder).mkdir(parents=True, exist_ok=True)
