from __future__ import annotations

import json
import os
import struct
import uuid
from pathlib import Path

from fastapi import UploadFile


STATIC_ROOT = Path("static").resolve()
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_SIGNATURE_BYTES = 2 * 1024 * 1024

_IMAGE_SIGNATURES = {
    "image/jpeg": ("jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
    "image/png": ("png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
}


def _validate_image_content(content: bytes, content_type: str) -> None:
    if content_type == "image/png":
        if len(content) < 33 or content[12:16] != b"IHDR" or b"IEND" not in content[-16:]:
            raise ValueError("La imagen PNG está incompleta o dañada")
        width, height = struct.unpack(">II", content[16:24])
    else:
        if len(content) < 4 or not content.endswith(b"\xff\xd9"):
            raise ValueError("La imagen JPEG está incompleta o dañada")
        width = height = 0
        index = 2
        start_of_frame = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
        while index + 4 < len(content):
            if content[index] != 0xFF:
                index += 1
                continue
            while index < len(content) and content[index] == 0xFF:
                index += 1
            if index >= len(content):
                break
            marker = content[index]
            index += 1
            if marker in {0xD8, 0xD9, 0x01, *range(0xD0, 0xD8)}:
                continue
            if index + 2 > len(content):
                break
            segment_length = int.from_bytes(content[index:index + 2], "big")
            if segment_length < 2 or index + segment_length > len(content):
                break
            if marker in start_of_frame:
                if segment_length < 7:
                    break
                height = int.from_bytes(content[index + 3:index + 5], "big")
                width = int.from_bytes(content[index + 5:index + 7], "big")
                break
            index += segment_length
        if not width or not height:
            raise ValueError("No se pudo leer la resolución de la imagen JPEG")

    if width <= 0 or height <= 0 or width * height > 40_000_000:
        raise ValueError("La imagen excede la resolución permitida o es inválida")


def public_asset_url(stored_value: str | None) -> str | None:
    """Expose stored paths as static URLs without serializing legacy Base64."""
    if not stored_value:
        return None
    normalized = stored_value.replace("\\", "/")
    if normalized.startswith("data:") or not normalized.startswith("static/"):
        return None
    return f"/{normalized}"


async def save_image_upload(
    upload: UploadFile,
    folder: str,
    *,
    signature: bool = False,
) -> str:
    """Persist a validated image and return its path relative to the repo root."""
    content_type = (upload.content_type or "").lower().split(";", 1)[0].strip()
    if content_type not in _IMAGE_SIGNATURES:
        raise ValueError("El archivo debe ser una imagen PNG o JPEG")
    if signature and content_type != "image/png":
        raise ValueError("La firma debe enviarse como imagen PNG")

    content = await upload.read(MAX_SIGNATURE_BYTES + 1 if signature else MAX_IMAGE_BYTES + 1)
    max_bytes = MAX_SIGNATURE_BYTES if signature else MAX_IMAGE_BYTES
    if not content:
        raise ValueError("El archivo enviado está vacío")
    if len(content) > max_bytes:
        raise ValueError(f"La imagen supera el límite de {max_bytes // (1024 * 1024)} MB")

    extension, validator = _IMAGE_SIGNATURES[content_type]
    if not validator(content):
        raise ValueError("El contenido del archivo no corresponde al formato declarado")
    _validate_image_content(content, content_type)

    # `folder` is a subdirectory under `static` (for example
    # `firmas/prestamos`). Keep the returned path web-relative and resolve it
    # against the same static root used by FastAPI's StaticFiles mount.
    relative_path = Path("static") / folder / f"{uuid.uuid4().hex}.{extension}"
    absolute_path = (STATIC_ROOT.parent / relative_path).resolve()
    if not absolute_path.is_relative_to(STATIC_ROOT):
        raise ValueError("Ruta de archivo no válida")
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(content)
    return relative_path.as_posix()


def delete_stored_upload(path: str | None) -> None:
    """Delete an uploaded file if a later validation/transaction fails."""
    if not path:
        return
    candidate = (STATIC_ROOT.parent / path).resolve()
    if not candidate.is_relative_to(STATIC_ROOT):
        return
    try:
        candidate.unlink(missing_ok=True)
    except OSError:
        pass


def rename_stored_upload(path: str | None, filename: str) -> str | None:
    """Rename a stored upload safely within static, returning its relative path."""
    if not path:
        return None
    source = (STATIC_ROOT.parent / path).resolve()
    if not source.is_relative_to(STATIC_ROOT) or not source.is_file():
        raise ValueError("No se encontró el archivo de evidencia guardado")
    requested = Path(filename)
    # Keep the extension aligned with the validated payload (photos may be
    # JPEG even when a sample filename uses .png).
    destination = (source.parent / requested.with_suffix(source.suffix)).resolve()
    if not destination.is_relative_to(STATIC_ROOT):
        raise ValueError("Ruta de archivo no válida")
    if destination.exists() and destination != source:
        # Partial returns can produce more than one evidence for the same
        # loan detail, so preserve every upload while keeping the requested ID prefix.
        destination = destination.with_name(
            f"{destination.stem}_{uuid.uuid4().hex[:8]}{destination.suffix}"
        )
    os.replace(source, destination)
    return destination.relative_to(STATIC_ROOT.parent).as_posix()


async def save_mapped_photos(
    uploads: list[UploadFile],
    metadata_json: str,
    folder: str,
    id_field: str,
) -> tuple[dict[int, str], list[str]]:
    """Save repeated `fotos` parts mapped to article/detail ids by filename."""
    try:
        metadata = json.loads(metadata_json or "[]")
    except json.JSONDecodeError as exc:
        raise ValueError("La metadata de fotos debe ser un JSON válido") from exc
    if not isinstance(metadata, list):
        raise ValueError("La metadata de fotos debe ser una lista")
    if len(metadata) != len(uploads):
        raise ValueError("Cada foto debe tener una asociación de artículo")

    names: dict[str, int] = {}
    ids: set[int] = set()
    for entry in metadata:
        if not isinstance(entry, dict):
            raise ValueError("Metadata de foto inválida")
        try:
            entity_id = int(entry[id_field])
            filename = str(entry["filename"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Cada foto debe indicar {id_field} y filename") from exc
        if entity_id <= 0 or not filename:
            raise ValueError("La asociación de foto contiene valores inválidos")
        if entity_id in ids or filename in names:
            raise ValueError("No se puede repetir el artículo ni el archivo en las fotos")
        ids.add(entity_id)
        names[filename] = entity_id

    if {upload.filename for upload in uploads} != set(names):
        raise ValueError("Los archivos recibidos no coinciden con la metadata de fotos")

    saved: list[str] = []
    result: dict[int, str] = {}
    try:
        for upload in uploads:
            entity_id = names[upload.filename or ""]
            path = await save_image_upload(upload, folder)
            saved.append(path)
            result[entity_id] = path
    except Exception:
        for path in saved:
            delete_stored_upload(path)
        raise
    return result, saved
