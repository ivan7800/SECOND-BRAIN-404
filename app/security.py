from pathlib import Path
import re
import zipfile

ALLOWED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx"}
_TEXT_SAMPLE_BYTES = 128 * 1024


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


def validate_file_content(path):
    """Valida que el contenido coincida razonablemente con la extensión permitida."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Formato no permitido")

    if path.stat().st_size == 0:
        raise ValueError("Archivo vacío")

    if suffix == ".pdf":
        with path.open("rb") as fh:
            if fh.read(5) != b"%PDF-":
                raise ValueError("El archivo no contiene una cabecera PDF válida")
        return True

    if suffix == ".docx":
        if not zipfile.is_zipfile(path):
            raise ValueError("El archivo no es un DOCX válido")
        try:
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
                required = {"[Content_Types].xml", "word/document.xml"}
                if not required.issubset(names):
                    raise ValueError("El contenedor no tiene estructura DOCX válida")
        except zipfile.BadZipFile as exc:
            raise ValueError("El archivo no es un DOCX válido") from exc
        return True

    sample = path.read_bytes()[:_TEXT_SAMPLE_BYTES]
    if b"\x00" in sample:
        raise ValueError("El archivo de texto contiene datos binarios")
    try:
        sample.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Los archivos Markdown/TXT deben estar codificados en UTF-8") from exc
    return True


def ensure_inside(root, target):
    root = root.resolve()
    target = target.resolve()
    if target != root and root not in target.parents:
        raise ValueError("Ruta fuera del almacén")
    return target
