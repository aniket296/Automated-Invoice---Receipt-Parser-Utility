"""Unit tests for the automated Math Integrity & Duplicate Invoice Auditor."""

from src.core.integrity_auditor import audit_invoice_batch
from src.models.invoice_model import AuditStatus, InvoiceRecord, LineItem


def test_audit_status_ok() -> None:
    """Verifies a clean record with valid math and line items passes with AuditStatus.OK."""
    rec = InvoiceRecord(
        record_id="r1",
        file_path="clean.pdf",
        file_name="clean.pdf",
        vendor_name="Cloudflare Inc.",
        invoice_number="CF-1001",
        invoice_date="2026-11-10",
        subtotal=200.00,
        tax_amount=20.00,
        grand_total=220.00,
        line_items=[
            LineItem("Pro Plan", 1.0, 120.00, 120.00),
            LineItem("Dedicated Load Balancer", 1.0, 80.00, 80.00),
        ],
    )
    audit_invoice_batch([rec])
    assert rec.audit_status == AuditStatus.OK
    assert rec.audit_notes == []


def test_audit_status_math_mismatch_and_line_item_sum() -> None:
    """Verifies subtotal + tax != grand_total and line-item sum mismatch trigger MATH_MISMATCH."""
    rec_total_mismatch = InvoiceRecord(
        record_id="r2",
        file_path="mismatch.pdf",
        file_name="mismatch.pdf",
        vendor_name="Stark Industries",
        invoice_number="SI-500",
        invoice_date="2026-11-12",
        subtotal=100.00,
        tax_amount=10.00,
        grand_total=115.00,
    )
    rec_items_mismatch = InvoiceRecord(
        record_id="r3",
        file_path="items_mismatch.pdf",
        file_name="items_mismatch.pdf",
        vendor_name="Wayne Enterprises",
        invoice_number="WE-600",
        invoice_date="2026-11-12",
        subtotal=100.00,
        tax_amount=10.00,
        grand_total=110.00,
        line_items=[
            LineItem("Grappling Hook", 1.0, 75.00, 75.00),
        ],
    )

    audit_invoice_batch([rec_total_mismatch, rec_items_mismatch])

    assert rec_total_mismatch.audit_status == AuditStatus.MATH_MISMATCH
    assert any("100.00" in note and "115.00" in note for note in rec_total_mismatch.audit_notes)

    assert rec_items_mismatch.audit_status == AuditStatus.MATH_MISMATCH
    assert any("Line items sum" in note for note in rec_items_mismatch.audit_notes)


def test_audit_status_duplicate_detection() -> None:
    """Verifies duplicate detection by (vendor, invoice_number) and (vendor, date, grand_total)."""
    first = InvoiceRecord(
        record_id="d1",
        file_path="inv_a.pdf",
        file_name="inv_a.pdf",
        vendor_name="Acme Supplies",
        invoice_number="INV-900",
        invoice_date="2026-11-01",
        subtotal=50.00,
        tax_amount=5.00,
        grand_total=55.00,
    )
    dup_by_number = InvoiceRecord(
        record_id="d2",
        file_path="inv_b.pdf",
        file_name="inv_b.pdf",
        vendor_name="acme supplies",
        invoice_number="inv-900",
        invoice_date="2026-11-05",
        subtotal=80.00,
        tax_amount=8.00,
        grand_total=88.00,
    )
    dup_by_date_total = InvoiceRecord(
        record_id="d3",
        file_path="inv_c.pdf",
        file_name="inv_c.pdf",
        vendor_name="Acme Supplies",
        invoice_number="",
        invoice_date="2026-11-01",
        subtotal=50.00,
        tax_amount=5.00,
        grand_total=55.00,
    )

    audit_invoice_batch([first, dup_by_number, dup_by_date_total])

    assert first.audit_status == AuditStatus.OK
    assert dup_by_number.audit_status == AuditStatus.DUPLICATE
    assert dup_by_date_total.audit_status == AuditStatus.DUPLICATE


def test_audit_status_needs_review() -> None:
    """Verifies missing vendor_name or zero grand_total flags AuditStatus.NEEDS_REVIEW."""
    no_vendor = InvoiceRecord(
        record_id="n1",
        file_path="novendor.pdf",
        file_name="novendor.pdf",
        vendor_name="",
        invoice_number="INV-1",
        invoice_date="2026-11-01",
        grand_total=100.00,
    )
    zero_total = InvoiceRecord(
        record_id="n2",
        file_path="zerototal.pdf",
        file_name="zerototal.pdf",
        vendor_name="Valid Vendor",
        invoice_number="INV-2",
        invoice_date="2026-11-01",
        grand_total=0.0,
    )

    audit_invoice_batch([no_vendor, zero_total])

    assert no_vendor.audit_status == AuditStatus.NEEDS_REVIEW
    assert zero_total.audit_status == AuditStatus.NEEDS_REVIEW
