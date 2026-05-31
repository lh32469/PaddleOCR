"""Pre-download PaddleOCR English models during Docker image build."""
from paddleocr import PaddleOCR

PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
print("PaddleOCR models downloaded successfully.")
