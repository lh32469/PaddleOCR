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
# paddleocr pulls in opencv-python + opencv-contrib-python (both 4.6).
# pdf2docx (a paddleocr transitive dep) pulls in opencv-python-headless at a
# different version. Having all three simultaneously causes a "double free or
# corruption" crash when libpaddle loads. Fix: install everything, then replace
# the GUI opencv builds with a single pinned headless build at the same version.
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y opencv-python opencv-contrib-python \
    && pip install --no-cache-dir opencv-python-headless==4.6.0.66

# Disable MKL-DNN (Intel math kernel) whose CPU-feature auto-detection segfaults
# inside Docker/k8s cgroups on some hosts. Safe to set globally; inference falls
# back to the plain Eigen/OpenBLAS path, which is stable in all container envs.
ENV FLAGS_use_mkldnn=0
ENV PADDLE_DISABLE_MKLDNN=1

# Models (~15 MB) are downloaded on first pod startup by the FastAPI lifespan
# hook. Pre-downloading at build time segfaults inside the DinD build sandbox
# because PaddlePaddle's CPU-feature probing requires capabilities that DinD
# does not expose. The readiness probe delay (90 s) covers download + warm-up.

COPY app/ app/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
