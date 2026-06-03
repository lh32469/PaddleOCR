from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from .models import EasementDoc
from .ocr_service import get_ocr, process_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class _HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if "GET /health" in record.getMessage():
            record.levelno = logging.DEBUG
            record.levelname = "DEBUG"
        return True

logging.getLogger("uvicorn.access").addFilter(_HealthCheckFilter())


@dataclass
class _OcrJob:
    pdf_bytes: bytes
    filename: str
    callback_url: str


_queue: asyncio.Queue[_OcrJob] = asyncio.Queue()
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ocr")


async def _worker() -> None:
    async with httpx.AsyncClient(timeout=60.0) as http:
        while True:
            job = await _queue.get()
            try:
                loop = asyncio.get_running_loop()
                pages = await loop.run_in_executor(_executor, process_pdf, job.pdf_bytes)
                flat_lines = [line for page in pages for line in page.lines]
                doc = EasementDoc(
                    id=job.filename,
                    filename=job.filename,
                    pages=pages,
                    lines=flat_lines,
                    pageCount=len(pages),
                    createdAt=datetime.now(timezone.utc),
                )
                resp = await http.post(
                    job.callback_url,
                    content=doc.model_dump_json(),
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                logger.info("callback delivered status=%d url=%s file=%s",
                            resp.status_code, job.callback_url, job.filename)
            except Exception:
                logger.exception("job failed file=%s callback=%s",
                                 job.filename, job.callback_url)
            finally:
                _queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(_executor, get_ocr)
    logger.info("Apple Vision OCR ready")
    worker_task = asyncio.create_task(_worker())
    yield
    worker_task.cancel()
    _executor.shutdown(wait=False)


app = FastAPI(title="macOS Easement OCR Service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "queued": _queue.qsize()}


@app.post("/api/easement", status_code=201)
async def submit_easement(
    file: UploadFile = File(...),
    callbackUrl: str = Form(...),
):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    await _queue.put(_OcrJob(
        pdf_bytes=pdf_bytes,
        filename=file.filename,
        callback_url=callbackUrl,
    ))
    logger.info("accepted file=%s callback=%s depth=%d",
                file.filename, callbackUrl, _queue.qsize())
    return {"accepted": True, "filename": file.filename, "queued": _queue.qsize()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("macos.main:app", host="0.0.0.0", port=8000, workers=1, timeout_keep_alive=120)
