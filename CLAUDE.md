# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this service does

A FastAPI (Python) microservice that accepts a PDF file via `POST /api/easement`, runs PaddleOCR on every rendered page, and returns an `EasementDoc` JSON object — a structure mirroring the Java model `org.gpc4j.easements.model.EasementDoc` used by the consuming application.

## Development commands

```bash
# Install deps (use a venv)
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload --port 8000

# Test the endpoint
curl -X POST http://localhost:8000/api/easement \
     -F "file=@sample.pdf" | python -m json.tool

# Build Docker image
docker build -t paddleocr-easement:latest .

# Deploy to k8s (assumes image is already pushed/available)
kubectl apply -f k8s/
```

## Architecture

```
app/
  main.py        — FastAPI app; lifespan warms up the PaddleOCR model at startup
  ocr_service.py — PDF→image rendering (PyMuPDF at 200 DPI) + PaddleOCR call
  models.py      — Pydantic EasementDoc / EasementPage (mirrors the Java model)
download_models.py — run once during `docker build` to pre-bake model weights
k8s/
  deployment.yaml — 2 replicas; 4 GB RAM / 4 CPU limit; readiness probe delays 45 s
  service.yaml    — ClusterIP on port 80 → pod port 8000
```

## Key design decisions

- **Single PaddleOCR instance** (`_ocr` global in `ocr_service.py`): model loading takes ~20 s and ~300 MB; it must not be re-created per request.
- **Model warm-up in lifespan**: `get_ocr()` is called in the FastAPI `lifespan` context so the readiness probe is only satisfied after the model is loaded, not just after the process starts.
- **200 DPI rendering**: balances OCR accuracy against memory for large PDFs. Tune `dpi` in `_page_to_array` if needed.
- **Confidence scaling**: PaddleOCR returns scores in [0, 1]; they are multiplied by 100 to match the 0–100 scale documented in `EasementPage.confidence`.
- **`--workers 1`**: multiple uvicorn workers would each load the full model, exceeding the 4 GB pod limit. Use horizontal pod scaling instead.
- **Models baked into the image**: `download_models.py` runs during `docker build` so pods start without internet access and without the cold-download delay.

## Response shape

```jsonc
{
  "id": "scan.pdf",          // set to the uploaded filename
  "filename": "scan.pdf",
  "pageCount": 3,
  "pages": [
    { "pageNumber": 1, "lines": ["EASEMENT AGREEMENT", ...], "confidence": 94.3 }
  ],
  "lines": ["EASEMENT AGREEMENT", ...],  // flat concat of all pages, for full-text search
  "createdAt": "2026-05-31T18:00:00Z"
}
```
