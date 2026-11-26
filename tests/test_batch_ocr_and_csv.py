"""Unit tests for HybridOcrEngine, InvoiceBatchScanner, CSV export, and /Processed archiving."""

import csv
from pathlib import Path
from src.core.batch_scanner import InvoiceBatchScanner, archive_verified_invoices
from src.core.csv_exporter import export_line_items_csv, export_summary_ledger_csv
from src.core.ocr_engine import HybridOcrEngine, render_document_preview
from src.core.vendor_profiles import VendorProfileStore
from src.models.invoice_model import AuditStatus, ExtractionMethod


def test_hybrid_ocr_engine_digital_pdf_and_scanned_png(
    synthetic_digital_pdf: Path,
    synthetic_scanned_receipt_png: Path,
) -> None:
    """Verifies PyMuPDF digital fast-path for PDFs and offline RapidOCR for scanned PNGs."""
    engine = HybridOcrEngine()

    pdf_text, pdf_method = engine.extract_text(str(synthetic_digital_pdf))
    assert pdf_method == ExtractionMethod.DIGITAL_PDF
    assert "Apex Cloud Infrastructure Inc." in pdf_text
    assert "INV-2026-501" in pdf_text

    png_text, png_method = engine.extract_text(str(synthetic_scanned_receipt_png))
    assert png_method == ExtractionMethod.LOCAL_OCR
    assert "9081" in png_text or "132.00" in png_text or "GREENFIELD" in png_text.upper()

    preview_img = render_document_preview(str(synthetic_digital_pdf), max_width=360)
    assert preview_img.width <= 360


def test_batch_scanner_csv_export_and_archiver(
    tmp_path: Path,
    synthetic_digital_pdf: Path,
    synthetic_duplicate_pdf: Path,
    synthetic_math_mismatch_pdf: Path,
) -> None:
    """Verifies end-to-end folder scanning, auditing, dual CSV export, and /Processed archiving."""
    store = VendorProfileStore(tmp_path / "empty_profiles.json")
    scanner = InvoiceBatchScanner(vendor_store=store, max_workers=2)

    progress_events: list[tuple[int, int, str]] = []
    records = scanner.scan_folder(
        str(tmp_path),
        progress_callback=lambda done, total, fname: progress_events.append((done, total, fname)),
    )

    assert len(records) == 3
    assert len(progress_events) == 3

    statuses = {r.file_name: r.audit_status for r in records}
    assert statuses["clean_digital_invoice.pdf"] == AuditStatus.OK
    assert statuses["duplicate_digital_invoice.pdf"] == AuditStatus.DUPLICATE
    assert statuses["mismatch_digital_invoice.pdf"] == AuditStatus.MATH_MISMATCH

    # Export Summary Ledger CSV and Line Items CSV
    summary_csv = tmp_path / "exports" / "summary_ledger.csv"
    lines_csv = tmp_path / "exports" / "line_items.csv"
    export_summary_ledger_csv(records, str(summary_csv))
    export_line_items_csv(records, str(lines_csv))

    assert summary_csv.exists()
    assert lines_csv.exists()

    with summary_csv.open("r", encoding="utf-8-sig", newline="") as f:
        sum_rows = list(csv.DictReader(f))
    assert len(sum_rows) == 3
    assert sum_rows[0]["Vendor_Name"] != ""

    with lines_csv.open("r", encoding="utf-8-sig", newline="") as f:
        line_rows = list(csv.DictReader(f))
    assert len(line_rows) >= 3

    # Archive verified (AuditStatus.OK) files into /Processed
    archived_count = archive_verified_invoices(records, str(tmp_path))
    assert archived_count == 1
    processed_file = tmp_path / "Processed" / "clean_digital_invoice.pdf"
    assert processed_file.exists()
    # Non-OK files remain in inbox
    assert (tmp_path / "mismatch_digital_invoice.pdf").exists()
    assert (tmp_path / "duplicate_digital_invoice.pdf").exists()
