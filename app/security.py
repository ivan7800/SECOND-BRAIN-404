from pathlib import Path
import re

ALLOWED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx"}

def safe_filename(name):
    name = Path(name).name
    stem = re.sub(r"[^A-Za-z0-9À-ÿ._ -]+", "_", Path(name).stem).strip(" .")
    suffix = Path(name).suffix.lower()
    return f"{(stem or 'documento')[:120]}{suffix}"

def validate_upload(name):
    cleaned = safe_filename(name)
    suffix = Path(cleaned).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Formato no permitido: {suffix or '(sin extensión)'}")
    return cleaned

def ensure_inside(root, target):
    root = root.resolve()
    target = target.resolve()
    if target != root and root not in target.parents:
        raise ValueError("Ruta fuera del almacén")
    return target
