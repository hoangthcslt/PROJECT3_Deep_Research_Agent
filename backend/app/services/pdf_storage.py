"""Store bounded, validated PDF uploads under generated session paths."""

import asyncio
import hashlib
import os
import re
import tempfile
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.tools.parse_pdf import (
    MAX_PDF_BYTES,
    PDFParseError,
    PDFTooLargeError,
    parse_pdf,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_ROOT = BACKEND_ROOT / "uploads"
MAX_PREVIEW_BYTES = 2_000
CHUNK_SIZE = 64 * 1024


class PDFUploadError(PDFParseError):
    """Upload metadata or file content is invalid."""


class PDFUploadTooLargeError(PDFTooLargeError):
    """Uploaded bytes exceed the accepted limit."""


def _session_directory(session_id: str) -> Path:
    try:
        session_key = str(uuid.UUID(session_id))
    except (AttributeError, ValueError, TypeError) as exc:
        raise PDFUploadError("Invalid research session ID.") from exc
    root = UPLOAD_ROOT.resolve()
    directory = (root / session_key).resolve()
    if not directory.is_relative_to(root):
        raise PDFUploadError("Invalid research session ID.")
    return directory


def _display_filename(value: str | None) -> str:
    basename = (value or "").replace("\\", "/").rsplit("/", 1)[-1]
    basename = re.sub(r"[\x00-\x1f\x7f]", "", basename)
    basename = " ".join(basename.split())[:255]
    if not basename or Path(basename).suffix.lower() != ".pdf":
        raise PDFUploadError("Upload filename must end in .pdf.")
    return basename


def _is_inside_upload_root(path: Path) -> bool:
    root = UPLOAD_ROOT.resolve()
    return path.resolve().is_relative_to(root)


def stored_file(session_id: str, source_id: str) -> Path:
    """Return an existing generated PDF path scoped to one session."""
    if not re.fullmatch(r"REF_PDF_[0-9a-f]{64}", source_id):
        raise FileNotFoundError("PDF source was not found.")
    path = _session_directory(session_id) / f"{source_id}.pdf"
    if not _is_inside_upload_root(path) or not path.is_file():
        raise FileNotFoundError("PDF source was not found.")
    return path.resolve()


async def save_upload(file: UploadFile, session_id: str) -> dict[str, object]:
    """Validate, parse, and persist an uploaded PDF under its generated content ID."""
    temporary_path: Path | None = None
    try:
        session_dir = _session_directory(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        if not _is_inside_upload_root(session_dir):
            raise PDFUploadError("Invalid research session ID.")

        filename = _display_filename(file.filename)
        media_type = (file.content_type or "").split(";", 1)[0].strip().lower()
        if media_type != "application/pdf":
            raise PDFUploadError("Upload content type must be application/pdf.")

        digest = hashlib.sha256()
        size = 0
        signature = bytearray()
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".upload-", suffix=".part", dir=session_dir, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            while chunk := await file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > MAX_PDF_BYTES:
                    raise PDFUploadTooLargeError("PDF exceeds the 10 MiB size limit.")
                if len(signature) < 5:
                    signature.extend(chunk[:5 - len(signature)])
                digest.update(chunk)
                temporary.write(chunk)

        if not bytes(signature).startswith(b"%PDF-"):
            raise PDFUploadError("Upload does not have a valid PDF signature.")

        parsed = await asyncio.to_thread(parse_pdf, temporary_path)
        source_id = "REF_PDF_" + digest.hexdigest()
        target = session_dir / f"{source_id}.pdf"
        if not _is_inside_upload_root(target):
            raise PDFUploadError("Invalid PDF storage path.")

        if target.exists():
            if target.stat().st_size != size or hashlib.sha256(target.read_bytes()).hexdigest() != digest.hexdigest():
                raise PDFUploadError("PDF content hash collision.")
            temporary_path.unlink(missing_ok=True)
        else:
            os.replace(temporary_path, target)
        temporary_path = None

        url = f"/api/v1/research/{uuid.UUID(session_id)}/sources/{source_id}/pdf"
        content = parsed.full_text
        preview = content.encode("utf-8")[:MAX_PREVIEW_BYTES].decode("utf-8", errors="ignore").rstrip()
        return {
            "source": {
                "source_id": source_id,
                "title": filename,
                "url": url,
                "source_type": "uploaded_pdf",
                "content_snippet": preview,
            },
            "file_path": str(target.resolve()),
            "content": content,
            "preview_text": preview,
            "filename": filename,
            "page_count": parsed.page_count,
            "truncated": bool(parsed.metadata.get("truncated")),
            "content_kind": "pdf_excerpt",
        }
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        await file.close()
