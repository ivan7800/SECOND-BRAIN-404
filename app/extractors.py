import re

from pypdf import PdfReader
from docx import Document

SUPPORTED = {".md", ".txt", ".pdf", ".docx"}

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_DOCX_HEADING_RE = re.compile(r"^(heading|t[ií]tulo|title)\b", re.IGNORECASE)


def _markdown_sections(text):
    lines = text.splitlines()
    if not lines:
        return []

    result = []
    start = 1
    heading = None
    buffer = []

    def flush(end_line):
        nonlocal buffer, start, heading
        part = "\n".join(buffer).strip()
        if not part:
            buffer = []
            return
        if heading:
            locator = f'sección "{heading}" · líneas {start}-{end_line}'
        else:
            locator = f"líneas {start}-{end_line}"
        result.append({"text": part, "locator": locator, "heading": heading or ""})
        buffer = []

    for idx, line in enumerate(lines, 1):
        match = _HEADING_RE.match(line)
        if match:
            flush(idx - 1)
            heading = match.group(2).strip()
            start = idx
            buffer = [line]
        else:
            if not buffer:
                start = idx
            buffer.append(line)
    flush(len(lines))
    return result


def _text_sections(text, max_lines=100):
    lines = text.splitlines()
    result = []
    for start in range(0, len(lines), max_lines):
        part = "\n".join(lines[start:start + max_lines]).strip()
        if part:
            result.append({
                "text": part,
                "locator": f"líneas {start + 1}-{min(start + max_lines, len(lines))}",
                "heading": "",
            })
    return result


def _docx_sections(path):
    doc = Document(str(path))
    paragraphs = [(i, p) for i, p in enumerate(doc.paragraphs, 1) if p.text.strip()]
    if not paragraphs:
        return []

    result = []
    start = paragraphs[0][0]
    heading = None
    buffer = []
    last_index = start

    def flush(end_index):
        nonlocal buffer, start, heading
        part = "\n\n".join(buffer).strip()
        if not part:
            buffer = []
            return
        if heading:
            locator = f'sección "{heading}" · párrafos {start}-{end_index}'
        else:
            locator = f"párrafos {start}-{end_index}"
        result.append({"text": part, "locator": locator, "heading": heading or ""})
        buffer = []

    for index, paragraph in paragraphs:
        style_name = getattr(paragraph.style, "name", "") or ""
        is_heading = bool(_DOCX_HEADING_RE.match(style_name.strip()))
        if is_heading:
            flush(last_index)
            heading = paragraph.text.strip()
            start = index
            buffer = [paragraph.text.strip()]
        else:
            if not buffer:
                start = index
            buffer.append(paragraph.text.strip())
        last_index = index
    flush(last_index)
    return result


def extract_sections(path):
    ext = path.suffix.lower()
    if ext == ".md":
        text = path.read_text(encoding="utf-8", errors="replace")
        return _markdown_sections(text)

    if ext == ".txt":
        text = path.read_text(encoding="utf-8", errors="replace")
        return _text_sections(text)

    if ext == ".pdf":
        reader = PdfReader(str(path))
        result = []
        for i, page in enumerate(reader.pages, 1):
            text = (page.extract_text() or "").strip()
            if text:
                result.append({"text": text, "locator": f"página {i}", "heading": f"Página {i}"})
        return result

    if ext == ".docx":
        return _docx_sections(path)

    raise ValueError(f"Formato no soportado: {ext}")


def chunk_sections(sections, chunk_size, overlap):
    if overlap >= chunk_size:
        overlap = chunk_size // 5
    chunks = []
    for section in sections:
        text = " ".join(section["text"].split())
        heading = (section.get("heading") or "").strip()
        pos = 0
        while pos < len(text):
            end = min(len(text), pos + chunk_size)
            if end < len(text):
                window = text[pos:end]
                cut = max(window.rfind(". "), window.rfind("; "), window.rfind(": "))
                if cut > chunk_size * 0.55:
                    end = pos + cut + 1
            piece = text[pos:end].strip()
            if piece:
                if heading and not piece.lower().startswith(heading.lower()):
                    indexed_text = f"{heading}. {piece}"
                else:
                    indexed_text = piece
                chunks.append({
                    "text": indexed_text,
                    "locator": section.get("locator", ""),
                    "heading": heading,
                })
            if end >= len(text):
                break
            pos = max(pos + 1, end - overlap)
    return chunks
