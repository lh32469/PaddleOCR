"""Pre-download PaddleOCR English models during Docker image build."""
from paddleocr import PaddleOCR

# enable_mkldnn=False — MKL-DNN CPU-feature probing segfaults in some container
# environments; the Eigen/OpenBLAS fallback is stable everywhere.
PaddleOCR(use_angle_cls=True, lang="en", show_log=False, enable_mkldnn=False)
print("PaddleOCR models downloaded successfully.")
