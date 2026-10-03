import csv
import json
import re
import zipfile
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import Path

from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook
from pptx import Presentation

SUPPORTED = {
    ".md", ".txt", ".pdf", ".docx", ".xlsx", ".pptx",
    ".html", ".htm", ".csv", ".json", ".epub", ".eml",
}

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_DOCX_HEADING_RE = re.compile(r"^(heading|t[ií]tulo|title)\b", re.IGNORECASE)


class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.skip += 1
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.skip:
            self.skip -= 1
        if tag in {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            text = data.strip()
            if text:
                self.parts.append(text + " ")

    def text(self):
        raw = "".join(self.parts)
        lines = [" ".join(line.split()) for line in raw.splitlines()]
        return "\n".join(line for line in lines if line)


def _html_to_text(raw):
    parser = _HTMLTextExtractor()
    parser.feed(raw)
    return parser.text()


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
        locator = (
            f'sección "{heading}" · líneas {start}-{end_line}'
            if heading else f"líneas {start}-{end_line}"
        )
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


def _text_sections(text, max_lines=100, locator_prefix=""):
    lines = text.splitlines()
    result = []
    for start in range(0, len(lines), max_lines):
        part = "\n".join(lines[start:start + max_lines]).strip()
        if part:
            loc = f"líneas {start + 1}-{min(start + max_lines, len(lines))}"
            if locator_prefix:
                loc = f"{locator_prefix} · {loc}"
            result.append({"text": part, "locator": loc, "heading": locator_prefix})
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
        locator = (
            f'sección "{heading}" · párrafos {start}-{end_index}'
            if heading else f"párrafos {start}-{end_index}"
        )
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


def _xlsx_sections(path):
    wb = load_workbook(filename=str(path), read_only=True, data_only=True)
    result = []
    try:
        for ws in wb.worksheets:
            rows = []
            start_row = None
            for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
                values = [str(v).strip() for v in row if v is not None and str(v).strip()]
                if not values:
                    continue
                if start_row is None:
                    start_row = row_idx
                rows.append(" | ".join(values))
                if len(rows) >= 80:
                    result.append({
                        "text": "\n".join(rows),
                        "locator": f'hoja "{ws.title}" · filas {start_row}-{row_idx}',
                        "heading": ws.title,
                    })
                    rows = []
                    start_row = None
            if rows:
                end_row = ws.max_row or start_row or 1
                result.append({
                    "text": "\n".join(rows),
                    "locator": f'hoja "{ws.title}" · filas {start_row}-{end_row}',
                    "heading": ws.title,
                })
    finally:
        wb.close()
    return result


def _pptx_sections(path):
    prs = Presentation(str(path))
    result = []
    for i, slide in enumerate(prs.slides, 1):
        parts = []
        for shape in slide.shapes:
            text = getattr(shape, "text", "")
            if text and text.strip():
                parts.append(text.strip())
        if parts:
            title = parts[0][:120]
            result.append({
                "text": "\n".join(parts),
                "locator": f"diapositiva {i}",
                "heading": title,
            })
    return result


def _csv_sections(path):
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        for i, row in enumerate(reader, 1):
            rows.append(f"fila {i}: " + " | ".join(cell.strip() for cell in row))
    return _text_sections("\n".join(rows), max_lines=100, locator_prefix="CSV")


def _json_sections(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        result = []
        for key, value in data.items():
            text = json.dumps(value, ensure_ascii=False, indent=2)
            result.extend(_text_sections(text, max_lines=100, locator_prefix=f"clave {key}"))
        return result
    return _text_sections(json.dumps(data, ensure_ascii=False, indent=2), locator_prefix="JSON")


def _epub_sections(path):
    result = []
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith((".xhtml", ".html", ".htm"))]
        for name in names:
            raw = archive.read(name).decode("utf-8", errors="replace")
            text = _html_to_text(raw)
            if text:
                label = Path(name).name
                result.extend(_text_sections(text, max_lines=120, locator_prefix=f"EPUB {label}"))
    return result


def _eml_sections(path):
    msg = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    header = [
        f"Asunto: {msg.get('subject', '')}",
        f"De: {msg.get('from', '')}",
        f"Para: {msg.get('to', '')}",
        f"Fecha: {msg.get('date', '')}",
    ]
    bodies = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype not in {"text/plain", "text/html"}:
                continue
            try:
                content = part.get_content()
            except Exception:
                continue
            if ctype == "text/html":
                content = _html_to_text(content)
            if content and content.strip():
                bodies.append(content.strip())
    else:
        try:
            content = msg.get_content()
        except Exception:
            content = ""
        if msg.get_content_type() == "text/html":
            content = _html_to_text(content)
        if content and content.strip():
            bodies.append(content.strip())
    text = "\n".join(header + [""] + bodies)
    return _text_sections(text, max_lines=120, locator_prefix="correo")


def extract_sections(path):
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".md":
        return _markdown_sections(path.read_text(encoding="utf-8", errors="replace"))
    if ext == ".txt":
        return _text_sections(path.read_text(encoding="utf-8", errors="replace"))
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
    if ext == ".xlsx":
        return _xlsx_sections(path)
    if ext == ".pptx":
        return _pptx_sections(path)
    if ext in {".html", ".htm"}:
        text = _html_to_text(path.read_text(encoding="utf-8", errors="replace"))
        return _text_sections(text, max_lines=120, locator_prefix="HTML")
    if ext == ".csv":
        return _csv_sections(path)
    if ext == ".json":
        return _json_sections(path)
    if ext == ".epub":
        return _epub_sections(path)
    if ext == ".eml":
        return _eml_sections(path)
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
                indexed_text = (
                    f"{heading}. {piece}"
                    if heading and not piece.lower().startswith(heading.lower()) else piece
                )
                chunks.append({
                    "text": indexed_text,
                    "locator": section.get("locator", ""),
                    "heading": heading,
                })
            if end >= len(text):
                break
            pos = max(pos + 1, end - overlap)
    return chunks
