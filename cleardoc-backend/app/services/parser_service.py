import io
import mimetypes
import os
from typing import Optional

import structlog

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - optional runtime dependency
    fitz = None

try:
    import pytesseract
except ImportError:  # pragma: no cover - optional runtime dependency
    pytesseract = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover - optional runtime dependency
    Image = None

try:
    import magic as python_magic
except ImportError:  # pragma: no cover - optional runtime dependency
    python_magic = None

logger = structlog.get_logger()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg",
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def _detect_mime(file_bytes: bytes, filename: str) -> str:
    if python_magic is not None:
        return python_magic.from_buffer(file_bytes[:2048], mime=True)

    guessed_type, _ = mimetypes.guess_type(filename or "")
    if guessed_type in ALLOWED_MIME_TYPES:
        return guessed_type

    extension = os.path.splitext(filename or "")[1].lower()
    if extension == ".pdf":
        return "application/pdf"
    if extension in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if extension == ".png":
        return "image/png"
    return ""


def validate_file(file_bytes: bytes, filename: str) -> tuple[bool, str]:
    if len(file_bytes) > MAX_FILE_SIZE:
        return False, "File too large. Maximum size is 5MB."

    mime = _detect_mime(file_bytes, filename)
    if mime not in ALLOWED_MIME_TYPES:
        return False, "File type not supported. Upload PDF, JPG, or PNG only."

    return True, "ok"


async def extract_text_from_file(
    file_bytes: bytes, filename: str
) -> tuple[Optional[str], Optional[str]]:
    """
    Returns (extracted_text, error_message)
    """
    is_valid, error = validate_file(file_bytes, filename)
    if not is_valid:
        return None, error

    mime = _detect_mime(file_bytes, filename)

    try:
        if mime == "application/pdf":
            if fitz is None:
                return None, "PDF extraction is unavailable in this environment."
            return await extract_from_pdf(file_bytes), None
        if Image is None or pytesseract is None:
            return None, "Image OCR is unavailable in this environment."
        return await extract_from_image(file_bytes), None
    except Exception as e:
        logger.error("file_extraction_failed", error=str(e))
        return None, "Could not read file. Please try pasting the text instead."


async def extract_from_pdf(file_bytes: bytes) -> str:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed")

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text_parts = []

    try:
        for page_num in range(min(doc.page_count, 10)):
            page = doc[page_num]
            text = page.get_text()

            if text.strip():
                text_parts.append(text)
            else:
                if Image is None or pytesseract is None:
                    continue
                pix = page.get_pixmap(dpi=200)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ocr_text = pytesseract.image_to_string(img)
                text_parts.append(ocr_text)
    finally:
        doc.close()

    full_text = "\n".join(text_parts).strip()
    return full_text[:10000] if len(full_text) > 10000 else full_text


async def extract_from_image(file_bytes: bytes) -> str:
    if Image is None or pytesseract is None:
        raise RuntimeError("Image OCR dependencies are not installed")

    image = Image.open(io.BytesIO(file_bytes))
    text = pytesseract.image_to_string(image, config="--psm 6")
    return text[:10000].strip()
