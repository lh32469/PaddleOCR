from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, File, HTTPException, UploadFile

from .models import EasementDoc
from .ocr_service import get_ocr, process_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up PaddleOCR so the first real request doesn't pay the model-load cost.
    get_ocr()
    logger.info("PaddleOCR model ready")
    yield


app = FastAPI(title="PaddleOCR Easement Service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/easement", response_model=EasementDoc)
async def process_easement(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        pages = process_pdf(pdf_bytes)
    except Exception:
        logger.exception("OCR failed for file=%s", file.filename)
        raise HTTPException(status_code=500, detail="OCR processing failed")

    flat_lines = [line for page in pages for line in page.lines]

    return EasementDoc(
        id=file.filename,
        filename=file.filename,
        pages=pages,
        lines=flat_lines,
        pageCount=len(pages),
        createdAt=datetime.now(timezone.utc),
    )
