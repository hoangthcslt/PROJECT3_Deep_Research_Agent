import asyncio
import io
import uuid
from pathlib import Path

import pymupdf as fitz
import pytest
from starlette.datastructures import Headers, UploadFile

import app.tools.parse_pdf as parse_pdf_module
from app.services import pdf_storage
from app.tools.parse_pdf import PDFParseError, PDFTooLargeError, parse_pdf


def _pdf_bytes(pages: list[str]) -> bytes:
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        if text:
            page.insert_text((72, 72), text)
    content = doc.tobytes()
    doc.close()
    return content


def _image_only_pdf() -> bytes:
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 20), False)
    pixmap.clear_with(200)
    doc = fitz.open()
    doc.new_page().insert_image(fitz.Rect(20, 20, 100, 100), pixmap=pixmap)
    content = doc.tobytes()
    doc.close()
    return content


def _upload(content: bytes, filename="report.pdf", media_type="application/pdf") -> UploadFile:
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": media_type}),
    )


def test_parse_pdf_bounds_utf8_excerpt_and_first_ten_pages():
    long_doc = fitz.open()
    page = long_doc.new_page()
    page.insert_textbox(fitz.Rect(20, 20, 590, 770), "Evidence " * 2_000, fontsize=2)
    long_pdf = long_doc.tobytes()
    long_doc.close()
    oversized_excerpt = parse_pdf(long_pdf)
    ten_page_excerpt = parse_pdf(_pdf_bytes([f"Page {number}" for number in range(11)]))

    assert len(oversized_excerpt.full_text.encode("utf-8")) <= parse_pdf_module.MAX_EXCERPT_BYTES
    assert oversized_excerpt.metadata["truncated"] is True
    assert "Page 9" in ten_page_excerpt.full_text
    assert "Page 10" not in ten_page_excerpt.full_text
    assert ten_page_excerpt.page_count == 11
    assert ten_page_excerpt.metadata["truncated"] is True


def test_parse_pdf_rejects_blank_and_image_only_content_without_ocr():
    for content in (_pdf_bytes([""]), _image_only_pdf()):
        with pytest.raises(PDFParseError, match="no extractable text"):
            parse_pdf(content)


def test_parse_pdf_rejects_encrypted_corrupt_and_over_page_limit_files():
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Secret")
    encrypted = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw="owner-password",
        user_pw="user-password",
    )
    doc.close()

    with pytest.raises(PDFParseError, match="Encrypted"):
        parse_pdf(encrypted)
    with pytest.raises(PDFParseError, match="malformed"):
        parse_pdf(b"not a PDF")
    with pytest.raises(PDFTooLargeError, match="100 page"):
        parse_pdf(_pdf_bytes([f"Page {number}" for number in range(101)]))


def test_save_upload_sanitizes_name_stores_private_file_and_closes_upload(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf_storage, "UPLOAD_ROOT", tmp_path / "uploads")
    session_id = str(uuid.uuid4())
    upload = _upload(_pdf_bytes(["Indexed text"]), filename=r"C:\private\report.pdf")

    record = asyncio.run(pdf_storage.save_upload(upload, session_id))
    source = record["source"]
    stored = pdf_storage.stored_file(session_id, source["source_id"])

    assert source["title"] == "report.pdf"
    assert source["source_type"] == "uploaded_pdf"
    assert source["url"] == f"/api/v1/research/{session_id}/sources/{source['source_id']}/pdf"
    assert record["content_kind"] == "pdf_excerpt"
    assert record["content"] == "Indexed text"
    assert len(record["content"].encode("utf-8")) <= 8_000
    assert len(record["preview_text"].encode("utf-8")) <= 2_000
    assert stored.read_bytes()
    assert upload.file.closed
    assert not list(stored.parent.glob("*.part"))

    with pytest.raises(FileNotFoundError):
        pdf_storage.stored_file(str(uuid.uuid4()), source["source_id"])


def test_failed_duplicate_parse_keeps_previous_valid_file_and_cleans_temp(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf_storage, "UPLOAD_ROOT", tmp_path / "uploads")
    session_id = str(uuid.uuid4())
    content = _pdf_bytes(["Previously accepted PDF"])
    first = asyncio.run(pdf_storage.save_upload(_upload(content), session_id))
    stored_path = Path(first["file_path"])
    original = stored_path.read_bytes()

    def fail_parse(_path):
        raise PDFParseError("malformed duplicate")

    monkeypatch.setattr(pdf_storage, "parse_pdf", fail_parse)
    with pytest.raises(PDFParseError, match="malformed duplicate"):
        asyncio.run(pdf_storage.save_upload(_upload(content), session_id))

    assert stored_path.read_bytes() == original
    assert not list(stored_path.parent.glob(".upload-*.part"))


@pytest.mark.parametrize(
    ("filename", "media_type", "content"),
    [
        ("report.txt", "application/pdf", b"%PDF-1.7"),
        ("report.pdf", "text/plain", b"%PDF-1.7"),
        ("report.pdf", "application/pdf", b"not a PDF"),
    ],
)
def test_save_upload_rejects_wrong_name_media_type_or_signature(monkeypatch, tmp_path, filename, media_type, content):
    monkeypatch.setattr(pdf_storage, "UPLOAD_ROOT", tmp_path / "uploads")
    upload = _upload(content, filename=filename, media_type=media_type)

    with pytest.raises(PDFParseError):
        asyncio.run(pdf_storage.save_upload(upload, str(uuid.uuid4())))

    assert upload.file.closed
    assert not list((tmp_path / "uploads").rglob(".upload-*.part"))


def test_save_upload_stops_when_stream_exceeds_limit(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf_storage, "UPLOAD_ROOT", tmp_path / "uploads")
    monkeypatch.setattr(pdf_storage, "MAX_PDF_BYTES", 8)
    upload = _upload(b"%PDF-1.7 and too much data")

    with pytest.raises(pdf_storage.PDFUploadTooLargeError):
        asyncio.run(pdf_storage.save_upload(upload, str(uuid.uuid4())))

    assert upload.file.closed
    assert not list((tmp_path / "uploads").rglob(".upload-*.part"))
