"""Multi-threaded invoice folder batch scanner and verified file archiver."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import shutil
import threading
import time
from typing import Callable, Optional

from src.core.field_extractor import extract_invoice_fields
from src.core.integrity_auditor import audit_invoice_batch
from src.core.ocr_engine import HybridOcrEngine
from src.core.vendor_profiles import VendorProfileStore
from src.models.invoice_model import AuditStatus, InvoiceRecord
from src.utils.config import (
    get_math_tolerance,
    get_max_worker_threads,
    get_ocr_render_dpi,
)
from src.utils.logger import get_logger

logger = get_logger()

SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


class InvoiceBatchScanner:
    """Discovers and parses all invoices/receipts in a folder using a worker thread pool."""

    def __init__(
        self,
        ocr_engine: Optional[HybridOcrEngine] = None,
        vendor_store: Optional[VendorProfileStore] = None,
        max_workers: Optional[int] = None,
        ocr_dpi: Optional[int] = None,
        math_tolerance: Optional[float] = None,
    ) -> None:
        self.ocr_engine = ocr_engine or HybridOcrEngine()
        self.vendor_store = vendor_store or VendorProfileStore()
        self.max_workers = max_workers or get_max_worker_threads()
        self.ocr_dpi = ocr_dpi or get_ocr_render_dpi()
        self.math_tolerance = (
            math_tolerance if math_tolerance is not None else get_math_tolerance()
        )
        self.cancel_event = threading.Event()

    def cancel(self) -> None:
        """Signals ongoing batch scan to stop processing queued files."""
        self.cancel_event.set()

    @staticmethod
    def discover_files(folder_path: str) -> list[Path]:
        """Discovers supported invoice/receipt files in folder_path (ignoring /Processed)."""
        root = Path(folder_path)
        if not root.exists() or not root.is_dir():
            return []

        discovered: list[Path] = []
        for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):
            if entry.is_dir():
                if entry.name.lower() == "processed":
                    continue
                continue
            if entry.is_file() and entry.suffix.lower() in SUPPORTED_EXTENSIONS:
                discovered.append(entry)
        return discovered

    def _process_single_file(self, file_path: Path) -> InvoiceRecord:
        """Extracts text and structured fields for a single file."""
        start_ts = time.perf_counter()
        raw_text, method = self.ocr_engine.extract_text(
            str(file_path), ocr_dpi=self.ocr_dpi
        )
        record = extract_invoice_fields(
            raw_text=raw_text,
            file_path=str(file_path),
            method=method,
            vendor_store=self.vendor_store,
        )
        record.duration_ms = round((time.perf_counter() - start_ts) * 1000.0, 2)
        return record

    def scan_folder(
        self,
        folder_path: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> list[InvoiceRecord]:
        """Scans all supported documents in folder_path, audits the batch, and returns records."""
        self.cancel_event.clear()
        files = self.discover_files(folder_path)
        total = len(files)
        if total == 0:
            logger.info("No supported invoice/receipt files found in %s", folder_path)
            return []

        logger.info("Scanning %d files in %s...", total, folder_path)
        results_by_index: dict[int, InvoiceRecord] = {}
        completed_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idx = {
                executor.submit(self._process_single_file, fpath): (idx, fpath)
                for idx, fpath in enumerate(files)
            }
            for future in as_completed(future_to_idx):
                if self.cancel_event.is_set():
                    break
                idx, fpath = future_to_idx[future]
                try:
                    rec = future.result()
                    results_by_index[idx] = rec
                except Exception as exc:
                    logger.exception("Error processing %s: %s", fpath, exc)
                completed_count += 1
                if progress_callback is not None:
                    try:
                        progress_callback(completed_count, total, fpath.name)
                    except Exception:
                        pass

        ordered_records = [
            results_by_index[i] for i in sorted(results_by_index.keys())
        ]
        audit_invoice_batch(ordered_records, tolerance=self.math_tolerance)
        logger.info("Completed batch scan of %d documents.", len(ordered_records))
        return ordered_records


def archive_verified_invoices(records: list[InvoiceRecord], target_folder: str) -> int:
    """Moves AuditStatus.OK files into <target_folder>/Processed/ safely, handling collisions."""
    base_dir = Path(target_folder)
    processed_dir = base_dir / "Processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    archived_count = 0
    for rec in records:
        if rec.audit_status != AuditStatus.OK or rec.is_archived:
            continue

        src_path = Path(rec.file_path)
        if not src_path.exists():
            continue

        dest_path = processed_dir / src_path.name
        collision_idx = 1
        while dest_path.exists():
            dest_path = (
                processed_dir / f"{src_path.stem}_{collision_idx}{src_path.suffix}"
            )
            collision_idx += 1

        try:
            shutil.move(str(src_path), str(dest_path))
            rec.file_path = str(dest_path)
            rec.file_name = dest_path.name
            rec.is_archived = True
            archived_count += 1
        except OSError as exc:
            logger.error("Failed archiving %s: %s", src_path, exc)

    return archived_count
