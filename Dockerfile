FROM python:3.11-slim

WORKDIR /service

# libGL   — OpenCV (bundled with PaddleOCR)
# libglib2.0-0 — libgthread (OpenCV)
# libgomp1 — GNU OpenMP runtime; PaddlePaddle's libpaddle.so links against libgomp.so.1
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download PaddleOCR detection / recognition / angle-classifier models at build
# time so the running pod needs no internet access and starts without delay.
COPY download_models.py .
RUN python download_models.py

COPY app/ app/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
