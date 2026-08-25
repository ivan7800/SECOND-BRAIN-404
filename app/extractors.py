from pypdf import PdfReader
from docx import Document

SUPPORTED = {".md", ".txt", ".pdf", ".docx"}

def extract_sections(path):
    ext = path.suffix.lower()
    if ext in {".md", ".txt"}:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        result = []
        for start in range(0, len(lines), 120):
            part = "\n".join(lines[start:start+120]).strip()
            if part:
                result.append({"text": part, "locator": f"líneas {start+1}-{min(start+120, len(lines))}"})
        return result

    if ext == ".pdf":
        reader = PdfReader(str(path))
        return [
            {"text": (page.extract_text() or "").strip(), "locator": f"página {i}"}
            for i, page in enumerate(reader.pages, 1)
            if (page.extract_text() or "").strip()
        ]

    if ext == ".docx":
        doc = Document(str(path))
        ps = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        result = []
        for start in range(0, len(ps), 30):
            part = "\n\n".join(ps[start:start+30])
            result.append({"text": part, "locator": f"párrafos {start+1}-{min(start+30, len(ps))}"})
        return result

    raise ValueError(f"Formato no soportado: {ext}")

def chunk_sections(sections, chunk_size, overlap):
    if overlap >= chunk_size:
        overlap = chunk_size // 5
    chunks = []
    for section in sections:
        text = " ".join(section["text"].split())
        pos = 0
        while pos < len(text):
            end = min(len(text), pos + chunk_size)
            if end < len(text):
                window = text[pos:end]
                cut = max(window.rfind(". "), window.rfind("; "))
                if cut > chunk_size * 0.55:
                    end = pos + cut + 1
            piece = text[pos:end].strip()
            if piece:
                chunks.append({"text": piece, "locator": section.get("locator", "")})
            if end >= len(text):
                break
            pos = max(pos + 1, end - overlap)
    return chunks
