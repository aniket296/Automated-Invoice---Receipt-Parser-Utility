"""Hybrid PyMuPDF digital text fast-path and offline RapidOCR extraction engine."""

from pathlib import Path
import threading
from typing import Optional
import fitz  # PyMuPDF
import numpy as np
from PIL import Image
from src.models.invoice_model import ExtractionMethod
from src.utils.logger import get_logger

logger = get_logger()


class HybridOcrEngine:
    """Hybrid document text extractor using PyMuPDF fast-path and lazy RapidOCR fallback."""

    _MIN_DIGITAL_CHARS = 40

    def __init__(self) -> None:
        self._ocr_instance = None
        self._lock = threading.Lock()

    def _get_ocr(self):
        """Lazily initializes RapidOCR in a thread-safe manner."""
        if self._ocr_instance is None:
            with self._lock:
                if self._ocr_instance is None:
                    from rapidocr_onnxruntime import RapidOCR

                    logger.info("Initializing offline RapidOCR ONNX engine...")
                    self._ocr_instance = RapidOCR()
        return self._ocr_instance

    def _run_ocr_on_pil_image(self, image: Image.Image) -> str:
        """Runs RapidOCR on a PIL Image and returns lines sorted in reading order."""
        rgb_image = image.convert("RGB")
        img_array = np.array(rgb_image)
        ocr = self._get_ocr()
        with self._lock:
            result, _ = ocr(img_array)

        if not result:
            return ""

        # Sort bounding boxes roughly top-to-bottom, then left-to-right
        # Each item in result is [box_points, text, confidence]
        # box_points: [[x0, y0], [x1, y1], [x2, y2], [x3, y3]]
        lines_with_coords = []
        for item in result:
            if not item or len(item) < 2:
                continue
            box, text = item[0], str(item[1]).strip()
            if not text:
                continue
            try:
                y_top = min(pt[1] for pt in box)
                y_bottom = max(pt[1] for pt in box)
                x_left = min(pt[0] for pt in box)
                height = max(8.0, y_bottom - y_top)
            except Exception:
                y_top, x_left, height = 0.0, 0.0, 12.0
            lines_with_coords.append((y_top, x_left, height, text))

        if not lines_with_coords:
            return ""

        lines_with_coords.sort(key=lambda entry: (entry[0], entry[1]))

        # Group items that lie on the same horizontal visual line
        grouped_lines: list[list[tuple[float, str]]] = []
        current_group: list[tuple[float, str]] = []
        current_y: Optional[float] = None
        current_tol: float = 10.0

        for y_top, x_left, height, text in lines_with_coords:
            if current_y is None or abs(y_top - current_y) <= current_tol:
                current_group.append((x_left, text))
                if current_y is None:
                    current_y = y_top
                    current_tol = max(8.0, height * 0.55)
            else:
                current_group.sort(key=lambda t: t[0])
                grouped_lines.append(current_group)
                current_group = [(x_left, text)]
                current_y = y_top
                current_tol = max(8.0, height * 0.55)

        if current_group:
            current_group.sort(key=lambda t: t[0])
            grouped_lines.append(current_group)

        output_lines = ["  ".join(t[1] for t in grp) for grp in grouped_lines]
        return "\n".join(output_lines)

    def extract_text(self, file_path: str, ocr_dpi: int = 220) -> tuple[str, ExtractionMethod]:
        """Extracts text from a PDF or receipt image using digital fast-path or offline OCR.

        Args:
            file_path: Path to .pdf, .png, .jpg, or .jpeg file.
            ocr_dpi: Resolution used when rasterizing scanned PDF pages for OCR.

        Returns:
            Tuple of (extracted_text, ExtractionMethod).
        """
        path = Path(file_path)
        if not path.exists():
            logger.error("File does not exist: %s", file_path)
            return "", ExtractionMethod.FAILED

        ext = path.suffix.lower()
        try:
            if ext == ".pdf":
                doc = fitz.open(str(path))
                try:
                    digital_pages: list[str] = []
                    for page in doc:
                        page_text = page.get_text("text") or ""
                        if page_text.strip():
                            digital_pages.append(page_text.strip())

                    combined_digital = "\n\n".join(digital_pages).strip()
                    if len(combined_digital) >= self._MIN_DIGITAL_CHARS:
                        return combined_digital, ExtractionMethod.DIGITAL_PDF

                    # Scanned PDF fallback: rasterize each page at ocr_dpi and run RapidOCR
                    zoom = max(1.0, ocr_dpi / 72.0)
                    mat = fitz.Matrix(zoom, zoom)
                    ocr_pages: list[str] = []
                    for page in doc:
                        pix = page.get_pixmap(matrix=mat, alpha=False)
                        pil_img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                        page_ocr = self._run_ocr_on_pil_image(pil_img)
                        if page_ocr.strip():
                            ocr_pages.append(page_ocr.strip())

                    return "\n\n".join(ocr_pages).strip(), ExtractionMethod.LOCAL_OCR
                finally:
                    doc.close()

            elif ext in (".png", ".jpg", ".jpeg"):
                with Image.open(str(path)) as pil_img:
                    ocr_text = self._run_ocr_on_pil_image(pil_img)
                return ocr_text.strip(), ExtractionMethod.LOCAL_OCR

            else:
                logger.warning("Unsupported file extension: %s", ext)
                return "", ExtractionMethod.FAILED

        except Exception as exc:
            logger.exception("Failed extracting text from %s: %s", file_path, exc)
            return "", ExtractionMethod.FAILED


def render_document_preview(file_path: str, max_width: int = 480) -> Image.Image:
    """Renders Page 1 of a PDF or loads a receipt image scaled cleanly to max_width."""
    path = Path(file_path)
    if not path.exists():
        placeholder = Image.new("RGB", (max_width, int(max_width * 1.2)), (241, 245, 249))
        return placeholder

    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            doc = fitz.open(str(path))
            try:
                if len(doc) == 0:
                    return Image.new("RGB", (max_width, int(max_width * 1.2)), (241, 245, 249))
                page = doc[0]
                rect = page.rect
                page_w = max(1.0, rect.width)
                zoom = max(1.0, (max_width * 1.5) / page_w)
                pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            finally:
                doc.close()
        else:
            with Image.open(str(path)) as opened:
                img = opened.convert("RGB")

        if img.width > max_width and max_width > 0:
            ratio = max_width / float(img.width)
            target_h = max(1, int(img.height * ratio))
            img = img.resize((max_width, target_h), Image.Resampling.LANCZOS)
        return img
    except Exception as exc:
        logger.warning("Preview rendering fallback for %s: %s", file_path, exc)
        return Image.new("RGB", (max_width, int(max_width * 1.2)), (241, 245, 249))
