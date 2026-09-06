from __future__ import annotations

import io
import shutil
import subprocess

from app.ai.client import vision_ocr_call
from app.ai.guard import normalise_text
from app.logging import get_logger

log = get_logger(__name__)

MAX_OCR_PAGES = 10


def extract_images_from_pdf(data: bytes, max_pages: int = MAX_OCR_PAGES) -> list[tuple[bytes, str]]:
    """Extract page images from a PDF using PyMuPDF (preferred) or pypdf."""
    images: list[tuple[bytes, str]] = []

    # 1. Try PyMuPDF page rendering (renders scanned/raster/vector pages reliably)
    try:
        import pymupdf

        doc = pymupdf.open(stream=data, filetype="pdf")
        for page in doc[:max_pages]:
            # Skip empty / blank pages that have no drawings, images, or markings
            if len(page.get_drawings()) == 0 and len(page.get_images()) == 0 and not page.get_text().strip():
                pix_check = page.get_pixmap(dpi=72)
                s = pix_check.samples
                if not s or min(s) == max(s):
                    continue
            # 150 DPI provides clean text legibility for vision models without ballooning token size
            pix = page.get_pixmap(dpi=150)
            images.append((pix.tobytes("jpeg"), "image/jpeg"))
        if images:
            return images
    except Exception as exc:  # noqa: BLE001
        log.debug("pymupdf_render_failed_fallback_to_pypdf", error=str(exc))

    # 2. Fallback: pypdf embedded image extraction
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        for page in reader.pages[:max_pages]:
            for img in page.images:
                ext = img.name.split(".")[-1].lower() if "." in img.name else "jpeg"
                mime = "image/png" if ext == "png" else "image/jpeg"
                images.append((img.data, mime))
                if len(images) >= max_pages:
                    break
            if len(images) >= max_pages:
                break
    except Exception as exc:  # noqa: BLE001
        log.warning("pypdf_image_extraction_failed", error=str(exc))

    return images


def run_local_tesseract(image_bytes: bytes) -> str | None:
    """Run local tesseract CLI on raw image bytes if available on the host system."""
    tesseract_bin = shutil.which("tesseract")
    if not tesseract_bin:
        return None
    try:
        # Check installed languages
        proc = subprocess.run(
            [tesseract_bin, "stdin", "stdout", "--oem", "1"],
            input=image_bytes,
            capture_output=True,
            timeout=15,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout.decode("utf-8", errors="ignore").strip()
    except Exception as exc:  # noqa: BLE001
        log.debug("tesseract_subprocess_failed", error=str(exc))
    return None


async def perform_ocr(ext: str, data: bytes) -> str:
    """Extract text from scanned PDFs or images via local Tesseract or Vision LLM."""
    images: list[tuple[bytes, str]] = []

    if ext in ("png", "jpg", "jpeg"):
        mime = "image/png" if ext == "png" else "image/jpeg"
        try:
            import pymupdf

            img_doc = pymupdf.open(stream=data, filetype=ext)
            if img_doc:
                pix = img_doc[0].get_pixmap()
                s = pix.samples
                if not s or min(s) == max(s):
                    return ""
        except Exception:
            pass
        images = [(data, mime)]
    elif ext == "pdf":
        images = extract_images_from_pdf(data)
    else:
        return ""

    if not images:
        return ""

    # 1. If local tesseract is installed and succeeds, use it for zero-cost offline OCR
    tess_results: list[str] = []
    if shutil.which("tesseract"):
        for img_bytes, _ in images:
            t_txt = run_local_tesseract(img_bytes)
            if t_txt:
                tess_results.append(t_txt)
        combined_tess = "\n\n".join(tess_results)
        if len(combined_tess.strip()) >= 20:
            return normalise_text(combined_tess)

    # 2. Vision LLM OCR (state of the art, handles math/tables/Bangla/English without OS binaries)
    try:
        ocr_text = await vision_ocr_call(images)
        return normalise_text(ocr_text)
    except Exception as exc:
        log.warning("vision_ocr_failed", error=str(exc))
        raise
