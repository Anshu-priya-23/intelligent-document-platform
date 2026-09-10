import io
import pymupdf
import pytest
from PIL import Image
from backend.app.services.document_validation_service import validate_file
from backend.app.core.config import settings
from backend.app.utils.exceptions import AppError

@pytest.mark.parametrize("name,data,code", [("bad.txt", b"text", "UNSUPPORTED_FILE_TYPE"), ("empty.pdf", b"", "EMPTY_FILE"), ("bad.pdf", b"%PDF-corrupt", "UNREADABLE_FILE"), ("bad.png", b"bad", "UNREADABLE_FILE"), ("../evil.pdf", b"a", "INVALID_FILE_NAME")])
def test_invalid(name, data, code):
    with pytest.raises(AppError) as error: validate_file(name, data)
    assert error.value.code == code

def test_pdf(pdf):
    assert validate_file("ok.pdf", pdf).page_count == 1

@pytest.mark.parametrize("count", [3, 4])
def test_pages(count):
    doc = pymupdf.open()
    for _ in range(count): doc.new_page()
    data = doc.tobytes()
    doc.close()
    if count == 3: assert validate_file("ok.pdf", data).page_count == 3
    else:
        with pytest.raises(AppError, match="PAGE_LIMIT_EXCEEDED"): validate_file("long.pdf", data)

@pytest.mark.parametrize("fmt,ext", [("PNG", "png"), ("JPEG", "jpg")])
def test_image(fmt, ext):
    out = io.BytesIO()
    Image.new("RGB", (100, 100), "white").save(out, format=fmt)
    assert validate_file("image." + ext, out.getvalue()).page_count == 1
    with pytest.raises(AppError): validate_file("spoof.pdf", out.getvalue())

def test_limit(pdf, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 10)
    with pytest.raises(AppError, match="FILE_TOO_LARGE"): validate_file("big.pdf", pdf)

def test_encrypted():
    doc = pymupdf.open(); doc.new_page()
    data = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="secret", user_pw="secret")
    doc.close()
    with pytest.raises(AppError, match="UNREADABLE_FILE"): validate_file("locked.pdf", data)
