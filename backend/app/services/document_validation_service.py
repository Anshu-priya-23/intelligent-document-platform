import io
import warnings
from pathlib import PurePath
import pymupdf
from PIL import Image
from backend.app.core.config import settings
from backend.app.schemas.document import FileValidation
from backend.app.utils.exceptions import AppError

Image.MAX_IMAGE_PIXELS = 25_000_000

def validate_file(name, data):
    if not name or len(name) > 255 or any(c in name for c in '/\\') or any(ord(c) < 32 for c in name):
        raise AppError("INVALID_FILE_NAME", "Use a plain file name of at most 255 characters.")
    ext = PurePath(name).suffix.lower()
    if ext not in {".pdf", ".jpg", ".jpeg", ".png"}:
        raise AppError("UNSUPPORTED_FILE_TYPE", "Only PDF / JPG / PNG documents are supported.", 415)
    if not data:
        raise AppError("EMPTY_FILE", "The uploaded file is empty.")
    if len(data) > settings.max_upload_bytes:
        raise AppError("FILE_TOO_LARGE", "The uploaded file exceeds the size limit.", 413)
    try:
        if ext == ".pdf":
            if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
                raise ValueError("PDF signature")
            with pymupdf.open(stream=data, filetype="pdf") as doc:
                if doc.needs_pass or doc.is_repaired:
                    raise ValueError("encrypted or repaired")
                count = len(doc)
                if count > 3:
                    raise AppError("PAGE_LIMIT_EXCEEDED", "Documents may contain at most 3 pages.")
                if count < 1:
                    raise ValueError("no pages")
                for page in doc:
                    if page.rect.width <= 0 or page.rect.height <= 0 or page.rect.width * page.rect.height > 20_000_000:
                        raise ValueError("page dimensions")
                    page.get_pixmap(matrix=pymupdf.Matrix(0.2, 0.2))
            mime = "application/pdf"
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(data)) as im:
                    expected = "PNG" if ext == ".png" else "JPEG"
                    if im.format != expected or getattr(im, "n_frames", 1) != 1:
                        raise ValueError("image format")
                    im.verify()
                with Image.open(io.BytesIO(data)) as im:
                    im.load()
            count, mime = 1, "image/png" if ext == ".png" else "image/jpeg"
    except AppError:
        raise
    except Exception:
        raise AppError("UNREADABLE_FILE", "The file is corrupted, encrypted, unsafe, or does not match its extension.") from None
    return FileValidation(file_type=mime, page_count=count)
