"""Pytest fixtures generating synthetic digital PDFs and scanned receipt PNGs."""

from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import pytest


def _create_invoice_pdf(
    target_path: Path,
    vendor: str,
    inv_no: str,
    inv_date: str,
    items: list[tuple[str, int, float, float]],
    subtotal: float,
    tax: float,
    grand_total: float,
    currency_symbol: str = "$",
) -> Path:
    """Helper to generate a synthetic digital PDF invoice using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    lines = [
        "INVOICE",
        vendor,
        f"Invoice #: {inv_no}",
        f"Invoice Date: {inv_date}",
        "Bill To: Local Accounting Team",
        "",
        "Description  Qty  Unit Price  Line Total",
    ]
    for desc, qty, unit_p, line_tot in items:
        lines.append(f"{desc}  {qty}  {currency_symbol}{unit_p:.2f}  {currency_symbol}{line_tot:.2f}")

    lines.extend(
        [
            "",
            f"Subtotal: {currency_symbol}{subtotal:.2f}",
            f"Tax (10%): {currency_symbol}{tax:.2f}",
            f"Grand Total: {currency_symbol}{grand_total:.2f}",
        ]
    )

    y = 60
    for line in lines:
        page.insert_text((50, y), line, fontsize=12)
        y += 22

    doc.save(str(target_path))
    doc.close()
    return target_path


@pytest.fixture
def synthetic_digital_pdf(tmp_path: Path) -> Path:
    """Fixture 1: Synthetic clean digital PDF invoice with 2 line items."""
    pdf_file = tmp_path / "clean_digital_invoice.pdf"
    return _create_invoice_pdf(
        target_path=pdf_file,
        vendor="Apex Cloud Infrastructure Inc.",
        inv_no="INV-2026-501",
        inv_date="2026-11-20",
        items=[
            ("Dedicated Server Instance", 2, 150.00, 300.00),
            ("Managed Storage Array", 1, 100.00, 100.00),
        ],
        subtotal=400.00,
        tax=40.00,
        grand_total=440.00,
    )


@pytest.fixture
def synthetic_duplicate_pdf(tmp_path: Path) -> Path:
    """Fixture 3a: Synthetic duplicate invoice PDF matching synthetic_digital_pdf."""
    pdf_file = tmp_path / "duplicate_digital_invoice.pdf"
    return _create_invoice_pdf(
        target_path=pdf_file,
        vendor="Apex Cloud Infrastructure Inc.",
        inv_no="INV-2026-501",
        inv_date="2026-11-20",
        items=[
            ("Dedicated Server Instance", 2, 150.00, 300.00),
            ("Managed Storage Array", 1, 100.00, 100.00),
        ],
        subtotal=400.00,
        tax=40.00,
        grand_total=440.00,
    )


@pytest.fixture
def synthetic_math_mismatch_pdf(tmp_path: Path) -> Path:
    """Fixture 3b: Synthetic math-mismatch invoice PDF (400 + 40 != 495)."""
    pdf_file = tmp_path / "mismatch_digital_invoice.pdf"
    return _create_invoice_pdf(
        target_path=pdf_file,
        vendor="Metro Office Supplies LLC",
        inv_no="INV-2026-777",
        inv_date="2026-11-22",
        items=[
            ("Ergonomic Desk Chair", 2, 200.00, 400.00),
        ],
        subtotal=400.00,
        tax=40.00,
        grand_total=495.00,
    )


@pytest.fixture
def synthetic_scanned_receipt_png(tmp_path: Path) -> Path:
    """Fixture 2: Synthetic high-contrast scanned receipt PNG image for offline RapidOCR."""
    png_file = tmp_path / "scanned_receipt.png"
    img = Image.new("RGB", (850, 520), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 26)
    except OSError:
        font = ImageFont.load_default()

    lines = [
        "GREENFIELD HARDWARE STORE",
        "Invoice No: INV-9081",
        "Date: 2026-11-25",
        "Power Drill Set  1  120.00  120.00",
        "Subtotal: $120.00",
        "Tax: $12.00",
        "Grand Total: $132.00",
    ]

    y = 35
    for line in lines:
        draw.text((40, y), line, fill=(0, 0, 0), font=font)
        y += 58

    img.save(str(png_file), format="PNG")
    return png_file
