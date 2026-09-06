from __future__ import annotations

import pytest

from app.ai.client import get_provider, set_provider
from app.ai.providers.mock import MockProvider
from app.artefacts import ocr, parsers


@pytest.fixture(autouse=True)
def _use_mock_ai():
    mock = MockProvider()
    set_provider(mock)
    yield
    set_provider(None)


def test_sniff_extension_detects_images():
    png_head = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    assert parsers.sniff_extension("exam_page.png", png_head) == "png"

    jpg_head = b"\xff\xd8\xff\xe0\x00\x10JFIF"
    assert parsers.sniff_extension("exam_photo.jpg", jpg_head) == "jpg"
    assert parsers.sniff_extension("scan.jpeg", jpg_head) == "jpeg"


@pytest.mark.asyncio
async def test_extract_text_async_runs_ocr_on_image():
    # Synthetic image header
    png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    text = await parsers.extract_text_async("png", png_data)
    assert len(text) >= 20
    assert "Define DBMS" in text
    assert "Course: CSE 3101" in text


@pytest.mark.asyncio
async def test_extract_text_async_runs_ocr_on_scanned_pdf(monkeypatch):
    # A PDF with 0 extractable text
    fake_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    # Mock extract_images_from_pdf to return a synthetic page image
    monkeypatch.setattr(
        ocr, "extract_images_from_pdf", lambda data, max_pages=10: [(b"fake_image_bytes", "image/jpeg")]
    )

    text = await parsers.extract_text_async("pdf", fake_pdf)
    assert len(text) >= 20
    assert "Define DBMS" in text


@pytest.mark.asyncio
async def test_perform_ocr_custom_queued_result():
    provider = get_provider()
    assert isinstance(provider, MockProvider)
    provider.queue("extraction", "Custom OCR Extracted Question 1: Explain ACID properties. [10]")

    res = await ocr.perform_ocr("png", b"\x89PNG\r\n\x1a\n")
    assert "Explain ACID properties" in res
