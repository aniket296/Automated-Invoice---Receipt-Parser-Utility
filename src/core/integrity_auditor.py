"""Automated Math Integrity & Duplicate Invoice Auditor."""

from src.models.invoice_model import AuditStatus, InvoiceRecord, ExtractionMethod


def audit_invoice_batch(
    records: list[InvoiceRecord], tolerance: float = 0.02
) -> list[InvoiceRecord]:
    """Audits a batch of InvoiceRecords for missing fields, math mismatches, and duplicates.

    Evaluation precedence & rules:
    1. Resets audit_notes for each record.
    2. If extraction_method == ExtractionMethod.FAILED: marks AuditStatus.FAILED.
    3. Missing Critical Fields: Flags AuditStatus.NEEDS_REVIEW if grand_total <= 0 or not vendor_name.
    4. Math Integrity Check: If subtotal > 0, verifies abs((subtotal + tax_amount) - grand_total) <= tolerance.
       If violated, flags AuditStatus.MATH_MISMATCH with a clear explanation note.
    5. Line-Item Sum Check: If line_items is non-empty and subtotal > 0, verifies
       abs(sum(i.line_total) - subtotal) <= tolerance and appends an audit note if mismatched
       (and flags AuditStatus.MATH_MISMATCH if not already flagged).
    6. Duplicate Detection: Tracks (vendor_name.lower(), invoice_number.lower()) when invoice_number is present,
       and (vendor_name.lower(), invoice_date, round(grand_total, 2)) across the batch.
       Flags subsequent matches as AuditStatus.DUPLICATE.
    7. If no issues exist, marks AuditStatus.OK.
    """
    seen_vendor_inv_num: set[tuple[str, str]] = set()
    seen_vendor_date_total: set[tuple[str, str, float]] = set()

    for record in records:
        record.audit_notes = []

        if record.extraction_method == ExtractionMethod.FAILED:
            record.audit_status = AuditStatus.FAILED
            record.audit_notes.append("Document text extraction failed.")
            continue

        has_missing_critical = False
        has_math_mismatch = False
        is_duplicate = False

        vendor_clean = record.vendor_name.strip()
        inv_num_clean = record.invoice_number.strip()
        date_clean = record.invoice_date.strip()

        # 1. Missing Critical Fields
        if not vendor_clean:
            has_missing_critical = True
            record.audit_notes.append("Missing vendor name.")
        if record.grand_total <= 0:
            has_missing_critical = True
            record.audit_notes.append("Missing or zero Grand Total.")

        # 2. Math Integrity Check (Subtotal + Tax == Grand Total)
        if record.subtotal > 0 and record.grand_total > 0:
            expected_grand = round(record.subtotal + record.tax_amount, 2)
            if abs(expected_grand - record.grand_total) > tolerance:
                has_math_mismatch = True
                record.audit_notes.append(
                    f"Subtotal ({record.subtotal:.2f}) + Tax ({record.tax_amount:.2f}) "
                    f"!= Grand Total ({record.grand_total:.2f})"
                )

        # 3. Line-Item Sum Check
        if record.line_items and record.subtotal > 0:
            items_sum = round(sum(item.line_total for item in record.line_items), 2)
            if abs(items_sum - record.subtotal) > tolerance:
                has_math_mismatch = True
                record.audit_notes.append(
                    f"Line items sum ({items_sum:.2f}) != Subtotal ({record.subtotal:.2f})"
                )

        # 4. Duplicate Detection
        if vendor_clean and inv_num_clean:
            key_num = (vendor_clean.lower(), inv_num_clean.lower())
            if key_num in seen_vendor_inv_num:
                is_duplicate = True
                record.audit_notes.append(
                    f"Duplicate invoice number '{inv_num_clean}' for vendor '{vendor_clean}'."
                )
            else:
                seen_vendor_inv_num.add(key_num)

        if vendor_clean and date_clean and record.grand_total > 0:
            key_dt = (vendor_clean.lower(), date_clean, round(record.grand_total, 2))
            if key_dt in seen_vendor_date_total:
                if not is_duplicate:
                    is_duplicate = True
                    record.audit_notes.append(
                        f"Duplicate vendor/date/total combination ({vendor_clean}, {date_clean}, {record.grand_total:.2f})."
                    )
            else:
                seen_vendor_date_total.add(key_dt)

        # Determine final status
        if is_duplicate:
            record.audit_status = AuditStatus.DUPLICATE
        elif has_math_mismatch:
            record.audit_status = AuditStatus.MATH_MISMATCH
        elif has_missing_critical:
            record.audit_status = AuditStatus.NEEDS_REVIEW
        else:
            record.audit_status = AuditStatus.OK

    return records
