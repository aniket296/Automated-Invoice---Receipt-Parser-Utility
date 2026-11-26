"""Dual Accounting CSV Exporter (Summary Ledger CSV + Detailed Line-Items CSV)."""

import csv
from pathlib import Path
from src.models.invoice_model import InvoiceRecord

SUMMARY_LEDGER_COLUMNS = [
    "File_Name",
    "Extraction_Method",
    "Vendor_Name",
    "Invoice_Number",
    "Invoice_Date",
    "Currency",
    "Subtotal",
    "Tax_Amount",
    "Grand_Total",
    "Line_Item_Count",
    "Audit_Status",
    "Audit_Notes",
]

LINE_ITEMS_COLUMNS = [
    "File_Name",
    "Vendor_Name",
    "Invoice_Number",
    "Invoice_Date",
    "Currency",
    "Item_Description",
    "Quantity",
    "Unit_Price",
    "Line_Total",
]


def export_summary_ledger_csv(records: list[InvoiceRecord], csv_path: str) -> None:
    """Writes UTF-8-SIG Excel-friendly Summary Ledger CSV."""
    target = Path(csv_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(SUMMARY_LEDGER_COLUMNS)
        for rec in records:
            writer.writerow(
                [
                    rec.file_name,
                    rec.extraction_method.value,
                    rec.vendor_name,
                    rec.invoice_number,
                    rec.invoice_date,
                    rec.currency,
                    f"{rec.subtotal:.2f}",
                    f"{rec.tax_amount:.2f}",
                    f"{rec.grand_total:.2f}",
                    len(rec.line_items),
                    rec.audit_status.value,
                    "; ".join(rec.audit_notes),
                ]
            )


def export_line_items_csv(records: list[InvoiceRecord], csv_path: str) -> None:
    """Writes UTF-8-SIG Excel-friendly Detailed Line-Items CSV (one row per LineItem)."""
    target = Path(csv_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(LINE_ITEMS_COLUMNS)
        for rec in records:
            for item in rec.line_items:
                writer.writerow(
                    [
                        rec.file_name,
                        rec.vendor_name,
                        rec.invoice_number,
                        rec.invoice_date,
                        rec.currency,
                        item.description,
                        f"{item.quantity:.2f}",
                        f"{item.unit_price:.2f}",
                        f"{item.line_total:.2f}",
                    ]
                )
