import io
from typing import Optional
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import magic as python_magic
import structlog

logger = structlog.get_logger()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg",
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def validate_file(file_bytes: bytes, filename: str) -> tuple[bool, str]:
    if len(file_bytes) > MAX_FILE_SIZE:
        return False, "File too large. Maximum size is 5MB."

    mime = python_magic.from_buffer(file_bytes[:2048], mime=True)
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

    mime = python_magic.from_buffer(file_bytes[:2048], mime=True)

    try:
        if mime == "application/pdf":
            return await extract_from_pdf(file_bytes), None
        else:
            return await extract_from_image(file_bytes), None
    except Exception as e:
        logger.error("file_extraction_failed", error=str(e))
        return None, "Could not read file. Please try pasting the text instead."


async def extract_from_pdf(file_bytes: bytes) -> str:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text_parts = []

    for page_num in range(min(doc.page_count, 10)):
        page = doc[page_num]
        text = page.get_text()

        if text.strip():
            text_parts.append(text)
        else:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            ocr_text = pytesseract.image_to_string(img)
            text_parts.append(ocr_text)

    doc.close()
    full_text = "\n".join(text_parts).strip()
    return full_text[:10000] if len(full_text) > 10000 else full_text


async def extract_from_image(file_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(file_bytes))
    text = pytesseract.image_to_string(image, config="--psm 6")
    return text[:10000].strip()
