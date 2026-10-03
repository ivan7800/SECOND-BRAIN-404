from email import policy
from email.parser import BytesParser
from pathlib import Path
import json
import re
import zipfile

ALLOWED_EXTENSIONS = {
    ".md", ".txt", ".pdf", ".docx", ".xlsx", ".pptx",
    ".html", ".htm", ".csv", ".json", ".epub", ".eml",
}
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


def _validate_zip_structure(path, required):
    if not zipfile.is_zipfile(path):
        raise ValueError("El archivo no contiene un contenedor ZIP válido")
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if not required.issubset(names):
                raise ValueError("El contenedor no tiene la estructura esperada")
    except zipfile.BadZipFile as exc:
        raise ValueError("Contenedor ZIP inválido") from exc


def _validate_utf8_text(path):
    sample = path.read_bytes()[:_TEXT_SAMPLE_BYTES]
    if b"\x00" in sample:
        raise ValueError("El archivo de texto contiene datos binarios")
    try:
        sample.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("El archivo de texto debe estar codificado en UTF-8") from exc


def validate_file_content(path):
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
        _validate_zip_structure(path, {"[Content_Types].xml", "word/document.xml"})
        return True
    if suffix == ".xlsx":
        _validate_zip_structure(path, {"[Content_Types].xml", "xl/workbook.xml"})
        return True
    if suffix == ".pptx":
        _validate_zip_structure(path, {"[Content_Types].xml", "ppt/presentation.xml"})
        return True
    if suffix == ".epub":
        _validate_zip_structure(path, {"META-INF/container.xml"})
        return True
    if suffix == ".eml":
        try:
            msg = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        except Exception as exc:
            raise ValueError("El archivo EML no se puede interpretar") from exc
        if not (msg.get("subject") or msg.get("from") or msg.get_payload()):
            raise ValueError("El archivo EML no contiene un mensaje reconocible")
        return True

    _validate_utf8_text(path)
    if suffix == ".json":
        try:
            json.loads(path.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("JSON inválido") from exc
    return True


def ensure_inside(root, target):
    root = root.resolve()
    target = target.resolve()
    if target != root and root not in target.parents:
        raise ValueError("Ruta fuera del almacén")
    return target
