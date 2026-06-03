from __future__ import annotations

import logging
from typing import List

import fitz  # PyMuPDF
from ocrmac.ocrmac import OCR
from PIL import Image

from .models import EasementPage

logger = logging.getLogger(__name__)

_warmed_up = False


def get_ocr() -> None:
    """Warm up Apple Vision by running a no-op recognition on a 1×1 image.

    Called by the FastAPI lifespan hook via run_in_executor so the event loop
    stays free during the ~300 ms Vision framework initialisation.
    """
    global _warmed_up
    if not _warmed_up:
        dummy = Image.new("RGB", (1, 1), color=(255, 255, 255))
        OCR(dummy, recognition_level="accurate").recognize()
        _warmed_up = True
    logger.info("Apple Vision OCR ready")


def _page_to_pil(page: fitz.Page, dpi: int = 200) -> Image.Image:
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def process_pdf(pdf_bytes: bytes) -> List[EasementPage]:
    """Render each PDF page at 200 DPI, run Apple Vision OCR, return per-page results."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    results: List[EasementPage] = []

    for page_num, page in enumerate(doc, start=1):
        img = _page_to_pil(page)

        # OCR.recognize() returns [(text, confidence_0_to_1, bbox), ...]
        # Empty list for blank or unreadable pages.
        raw = OCR(
            img,
            recognition_level="accurate",
            language_preference=["en-US"],
        ).recognize()

        lines: List[str] = []
        scores: List[float] = []

        for text, confidence, _bbox in raw:
            text = text.strip()
            if text:
                lines.append(text)
                scores.append(confidence)  # already in [0, 1]

        # Scale 0-1 → 0-100 to match EasementPage.confidence contract.
        mean_score = sum(scores) / len(scores) if scores else 0.0
        page_confidence = round(mean_score * 100, 2)

        results.append(EasementPage(pageNumber=page_num, lines=lines, confidence=page_confidence))
        logger.info("page=%d lines=%d confidence=%.1f%%", page_num, len(lines), page_confidence)

    doc.close()
    return results
