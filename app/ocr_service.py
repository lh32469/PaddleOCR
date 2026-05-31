from __future__ import annotations

import logging
from typing import List

import fitz  # PyMuPDF
import numpy as np
from paddleocr import PaddleOCR
from PIL import Image

from .models import EasementPage

logger = logging.getLogger(__name__)

# Single shared instance — model loading (~300 MB) is done once at startup.
_ocr: PaddleOCR | None = None


def get_ocr() -> PaddleOCR:
    global _ocr
    if _ocr is None:
        _ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False, enable_mkldnn=False)
    return _ocr


def _page_to_array(page: fitz.Page, dpi: int = 200) -> np.ndarray:
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return np.array(img)


def process_pdf(pdf_bytes: bytes) -> List[EasementPage]:
    """Render each PDF page at 200 DPI, run PaddleOCR, and return per-page results."""
    ocr = get_ocr()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    results: List[EasementPage] = []

    for page_num, page in enumerate(doc, start=1):
        img = _page_to_array(page)
        raw = ocr.ocr(img, cls=True)

        lines: List[str] = []
        scores: List[float] = []

        # raw is [[box, (text, score)], ...]; may be None or [None] for blank pages
        page_boxes = raw[0] if raw and raw[0] else []
        for box_data in page_boxes:
            text, score = box_data[1]
            text = text.strip()
            if text:
                lines.append(text)
                scores.append(score)

        # Scale PaddleOCR 0-1 confidence to Tesseract-compatible 0-100 range
        confidence = round(float(np.mean(scores)) * 100, 2) if scores else 0.0

        results.append(EasementPage(pageNumber=page_num, lines=lines, confidence=confidence))
        logger.info("page=%d lines=%d confidence=%.1f%%", page_num, len(lines), confidence)

    doc.close()
    return results
