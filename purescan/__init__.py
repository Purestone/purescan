"""PureScan: Lossless multi-page watermark inversion for scanned PDFs and documents.

Pure mathematical inversion without AI inpainting hallucination.
"""

from .core import invert_multiply, extract_template, detect_watermark_bbox
from .pdf_processor import clean_pdf

__version__ = "0.1.0"
__all__ = ["clean_pdf", "invert_multiply", "extract_template", "detect_watermark_bbox", "__version__"]
