import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from .security import ensure_inside


_LINE_RE = re.compile(r"líneas\s+(\d+)-(\d+)", re.IGNORECASE)
_PARA_RE = re.compile(r"párrafos\s+(\d+)-(\d+)", re.IGNORECASE)
_PAGE_RE = re.compile(r"página\s+(\d+)", re.IGNORECASE)


def resolve_source_path(settings, relative_path):
    rel = str(relative_path or "").replace("\\", "/").lstrip("/")
    if not rel:
        raise ValueError("Ruta de fuente vacía")
    first = rel.split("/", 1)[0]
    if first not in set(settings.index_dirs):
        raise ValueError("La fuente no pertenece a un área indexable")
    path = ensure_inside(settings.brain_root, settings.brain_root / rel)
    if not path.is_file():
        raise FileNotFoundError(rel)
    return path


def read_source_fragment(path, locator, max_chars=12000):
    ext = path.suffix.lower()
    locator = locator or ""

    if ext in {".md", ".txt"}:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        match = _LINE_RE.search(locator)
        if match:
            start, end = int(match.group(1)), int(match.group(2))
            text = "\n".join(lines[max(0, start - 1):max(start, end)])
        else:
            text = "\n".join(lines[:200])
        return text[:max_chars]

    if ext == ".pdf":
        reader = PdfReader(str(path))
        match = _PAGE_RE.search(locator)
        page_number = int(match.group(1)) if match else 1
        page_number = max(1, min(page_number, len(reader.pages)))
        return ((reader.pages[page_number - 1].extract_text() or "").strip())[:max_chars]

    if ext == ".docx":
        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs]
        match = _PARA_RE.search(locator)
        if match:
            start, end = int(match.group(1)), int(match.group(2))
            text = "\n\n".join(paragraphs[max(0, start - 1):max(start, end)])
        else:
            text = "\n\n".join(paragraphs[:100])
        return text[:max_chars]

    raise ValueError(f"Formato no soportado: {ext}")
