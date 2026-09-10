import io
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
import pymupdf
from PIL import Image, ImageOps
from backend.app.core.config import settings
from backend.app.services.ocr_layout_service import spatial_rows, rows_from_words
from backend.app.services.statement_table_service import year_columns, period_cells
from backend.app.utils.exceptions import AppError

log = logging.getLogger(__name__)

def ocr_image(image):
    if not shutil.which(settings.tesseract_cmd):
        raise AppError("OCR_UNAVAILABLE", "Tesseract is not installed or TESSERACT_CMD is incorrect.", 503)
    try:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "page.png"
            oriented = ImageOps.exif_transpose(image).convert("RGB")

            # Resize large images so OCR does not time out on Render free instances.
            oriented.thumbnail((2500, 2500), Image.Resampling.LANCZOS)
            oriented.save(path)
            # Orientation detection can fail on sparse receipts; keep original then.
            osd = subprocess.run([settings.tesseract_cmd, str(path), "stdout", "--psm", "0"], capture_output=True, timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            rotation = re.search(r"Rotate: (90|180|270)", osd.stdout.decode("utf-8", errors="replace"))
            if osd.returncode == 0 and rotation:
                oriented = oriented.rotate(-int(rotation.group(1)), expand=True)
                oriented.save(path)
            result = subprocess.run([settings.tesseract_cmd, str(path), "stdout", "-l", settings.ocr_language, "--psm", "3", "tsv"], capture_output=True, timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if result.returncode:
                raise AppError("OCR_FAILED", "OCR could not read this document.", 502)
            rows, text = spatial_rows(result.stdout.decode("utf-8", errors="replace"))
            headings = [(row, year_columns(row)) for row in rows if year_columns(row)]
            if headings:
                # Automatic segmentation can discard narrow schedules and entire
                # amount columns. A single-block pass recovers the table region;
                # keep automatic segmentation for headers and surrounding prose.
                block = subprocess.run([settings.tesseract_cmd, str(path), "stdout", "-l", settings.ocr_language, "--psm", "6", "tsv"], capture_output=True, timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                if block.returncode:
                    raise AppError("OCR_FAILED", "OCR could not read the statement table.", 502)
                block_rows, _ = spatial_rows(block.stdout.decode("utf-8", errors="replace"))
                columns = headings[0][1]
                start = min(w['top'] for w in headings[0][0]['words'])
                numeric_rows = [r for r in block_rows if min(w['top'] for w in r['words']) > start and len(period_cells(r, columns)) == len(columns)]
                if numeric_rows:
                    end = max(w['top'] + w['height'] for r in numeric_rows for w in r['words'])
                    table_rows = [r for r in block_rows if start <= min(w['top'] for w in r['words']) <= end]
                    schedule = next((w for r in rows for w in r['words'] if w['text'].lower() == 'schedule' and w['top'] < start), None)
                    if schedule:
                        # Tiny schedule digits need isolated recognition. Do not
                        # infer schedules from row order or neighboring numbers.
                        center = schedule['left'] + schedule['width']/2
                        gap = columns[1][1] - columns[0][1]
                        for row in table_rows:
                            if not period_cells(row, columns):
                                continue
                            left, right = int(center-gap*.30), int(center+gap*.30)
                            existing = ' '.join(w['text'] for w in row['words'] if left <= w['left']+w['width']/2 <= right)
                            if len(existing) > 1 and re.fullmatch(r'\d+[A-Za-z]?(?:\s*\(\d+\))?', existing):
                                continue
                            top = max(0, min(w['top'] for w in row['words'])-8)
                            bottom = min(oriented.height, max(w['top']+w['height'] for w in row['words'])+8)
                            crop = oriented.crop((left, top, right, bottom))
                            crop = ImageOps.expand(crop.resize((crop.width*4, crop.height*4)), border=30, fill='white')
                            cell_path = Path(folder) / 'schedule.png'
                            crop.save(cell_path)
                            cell = subprocess.run([settings.tesseract_cmd, str(cell_path), 'stdout', '-l', settings.ocr_language, '--psm', '7'], capture_output=True, timeout=10, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                            token = cell.stdout.decode('utf-8', errors='replace').strip()
                            if cell.returncode == 0 and re.fullmatch(r'\d+[A-Za-z]?(?:\s*\(\d+\))?', token):
                                row['words'] = [w for w in row['words'] if not left <= w['left']+w['width']/2 <= right]
                                row['words'].append({'text':token,'left':left,'top':top,'width':right-left,'height':bottom-top})
                                row['words'].sort(key=lambda w:w['left'])
                                row['text'] = ' '.join(w['text'] for w in row['words'])
                    rows = [r for r in rows if min(w['top'] for w in r['words']) < start or min(w['top'] for w in r['words']) > end] + table_rows
                    rows.sort(key=lambda r:min(w['top'] for w in r['words']))
                    text = '\n'.join(r['text'] for r in rows)
            return rows, text
    except subprocess.TimeoutExpired:
        raise AppError("OCR_TIMEOUT", "OCR exceeded its time limit.", 504) from None
    except OSError:
        raise AppError("OCR_FAILED", "OCR could not be started.", 503) from None

def extract_text(data, mime):
    pages, used = [], False
    if mime == "application/pdf":
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            for i, page in enumerate(doc):
                text = page.get_text("text", sort=True)
                layout_rows, _ = rows_from_words([{'text':w[4], 'left':w[0], 'top':w[1], 'width':w[2]-w[0], 'height':w[3]-w[1]} for w in page.get_text('words')])
                if layout_rows:
                    text = '\n'.join(row['text'] for row in layout_rows)
                # Image-dominated pages may have a native header but scanned body.
                images = page.get_image_info()
                image_area = sum(pymupdf.Rect(x["bbox"]).get_area() for x in images)
                if len(text.strip()) < 40 or image_area > page.rect.get_area() * 0.5:
                    # 300 DPI retains small financial digits that 180 DPI loses.
                    scale = min(300 / 72, (25_000_000 / page.rect.get_area()) ** 0.5)
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale))
                    layout_rows, text = ocr_image(Image.open(io.BytesIO(pix.tobytes("png"))))
                    used = True
                pages.append({"page_number": i + 1, "text": text, "layout_rows": layout_rows})
    else:
        with Image.open(io.BytesIO(data)) as im:
            layout_rows, text = ocr_image(im)
            pages.append({"page_number": 1, "text": text, "layout_rows": layout_rows})
        used = True
    if not any(p["text"].strip() for p in pages):
        raise AppError("NO_READABLE_TEXT", "No readable text was found.", 422)
    log.info("text_extraction_complete pages=%d ocr=%s", len(pages), used)
    return pages, used
