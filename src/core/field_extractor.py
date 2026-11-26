"""Heuristic and profile-guided invoice field & line-item extractor."""

from pathlib import Path
import re
from typing import Optional
import uuid
from src.core.vendor_profiles import VendorProfileStore
from src.models.invoice_model import ExtractionMethod, InvoiceRecord, LineItem
from src.models.vendor_rule import VendorProfile
from src.utils.config import get_default_currency
from src.utils.currency_parser import (
    detect_currency,
    normalize_date_string,
    parse_monetary_amount,
)

_GENERIC_HEADER_WORDS = {
    "INVOICE",
    "TAX INVOICE",
    "COMMERCIAL INVOICE",
    "RECEIPT",
    "SALES RECEIPT",
    "PAYMENT RECEIPT",
    "BILL",
    "BILL TO",
    "SHIP TO",
    "SOLD TO",
    "CUSTOMER",
    "ORIGINAL",
    "PAGE",
    "STATEMENT",
    "QUOTATION",
    "ESTIMATE",
    "PURCHASE ORDER",
    "DATE",
    "SUMMARY",
}

_SUMMARY_LINE_KEYWORDS = (
    "subtotal",
    "sub-total",
    "sub total",
    "total",
    "grand total",
    "amount due",
    "balance due",
    "total due",
    "tax",
    "gst",
    "vat",
    "cgst",
    "sgst",
    "igst",
    "sales tax",
    "discount",
    "shipping",
    "amount paid",
    "paid",
    "change",
)


def _extract_with_regex(pattern: str, text: str) -> Optional[str]:
    """Executes a regex pattern and returns the first captured group or full match."""
    if not pattern:
        return None
    try:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if not match:
            return None
        if match.lastindex and match.lastindex >= 1:
            return match.group(1).strip()
        return match.group(0).strip()
    except re.error:
        return None


def _extract_vendor_name_heuristic(raw_text: str) -> str:
    """Finds the first prominent non-generic header line as the vendor name."""
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    for line in lines[:12]:
        # Remove leading/trailing punctuation
        cleaned = re.sub(r"^[\-\*\#\:\s]+|[\-\*\#\:\s]+$", "", line).strip()
        if not cleaned or len(cleaned) < 2:
            continue
        upper = cleaned.upper()
        if upper in _GENERIC_HEADER_WORDS:
            continue
        if any(
            upper.startswith(prefix)
            for prefix in (
                "INVOICE #",
                "INVOICE NO",
                "INVOICE NUMBER",
                "INV#",
                "INV-",
                "RECEIPT #",
                "RECEIPT NO",
                "DATE:",
                "ISSUED:",
                "INVOICE DATE",
                "BILL TO",
                "SHIP TO",
                "TEL:",
                "PHONE:",
                "EMAIL:",
            )
        ):
            continue
        # Skip lines that are purely numbers/dates
        if re.fullmatch(r"[\d\W]+", cleaned):
            continue
        # If a line has multiple columns separated by wide spaces (e.g. "Vendor Ltd    INVOICE"), take left part
        parts = re.split(r"\s{3,}", cleaned)
        candidate = parts[0].strip()
        if candidate.upper() not in _GENERIC_HEADER_WORDS and len(candidate) >= 2:
            return candidate
    return ""


def _extract_invoice_number(raw_text: str, profile: Optional[VendorProfile]) -> str:
    """Extracts the invoice or receipt identifier."""
    if profile and profile.invoice_number_regex:
        custom_val = _extract_with_regex(profile.invoice_number_regex, raw_text)
        if custom_val:
            return custom_val

    patterns = [
        r"(?:Invoice|Inv)\s*(?:#|No\.?|Number|ID)\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/\_]{1,28})",
        r"(?:Invoice|Inv)\s*[:\-]\s*([A-Z0-9][A-Z0-9\-\/\_]{1,28})",
        r"(?:Receipt|Order|Ref)\s*(?:#|No\.?|Number)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/\_]{1,28})",
        r"\b(INV[\-\/][A-Z0-9\-\/]+)\b",
        r"\b(REC[\-\/][A-Z0-9\-\/]+)\b",
    ]
    stopwords = {"DATE", "NUMBER", "NO", "TOTAL", "DUE", "AMOUNT", "TO", "FROM"}
    for pat in patterns:
        for match in re.finditer(pat, raw_text, re.IGNORECASE):
            val = match.group(1).strip(" .,:;#")
            if val.upper() not in stopwords and any(ch.isdigit() for ch in val):
                return val
    return ""


def _extract_invoice_date(raw_text: str, profile: Optional[VendorProfile]) -> str:
    """Extracts and normalizes the invoice date to ISO YYYY-MM-DD."""
    if profile and profile.date_regex:
        custom_raw = _extract_with_regex(profile.date_regex, raw_text)
        if custom_raw:
            norm = normalize_date_string(custom_raw)
            if norm:
                return norm

    labeled_patterns = [
        r"(?:Invoice\s*Date|Issue\s*Date|Issued|Date\s*of\s*Issue|Billing\s*Date|Date)\s*[:\-]?\s*([^\n\r]{6,32})",
    ]
    for pat in labeled_patterns:
        for match in re.finditer(pat, raw_text, re.IGNORECASE):
            norm = normalize_date_string(match.group(1))
            if norm:
                return norm

    # Fallback: scan entire text for standalone date token
    for line in raw_text.splitlines():
        norm = normalize_date_string(line)
        if norm:
            return norm
    return ""


def _extract_totals(
    raw_text: str, profile: Optional[VendorProfile]
) -> tuple[float, float, float]:
    """Extracts (subtotal, tax_amount, grand_total) from raw invoice text."""
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    grand_total: Optional[float] = None

    if profile and profile.total_regex:
        custom_tot = _extract_with_regex(profile.total_regex, raw_text)
        if custom_tot:
            grand_total = parse_monetary_amount(custom_tot)

    if profile and profile.tax_regex:
        custom_tax = _extract_with_regex(profile.tax_regex, raw_text)
        if custom_tax:
            tax_amount = parse_monetary_amount(custom_tax)

    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]

    # Amount token regex at the end of a line
    amt_tail = r"([$€£₹]?\s*\d[\d,.\s]*\d|\b(?:USD|EUR|GBP|INR|Rs\.?)\s*\d[\d,.\s]*\d)\s*$"

    for line in lines:
        lower = line.lower()

        # Check Subtotal
        if subtotal is None and re.search(r"\b(?:sub\s*[-]?total|net\s*amount)\b", lower):
            m = re.search(amt_tail, line, re.IGNORECASE)
            if m:
                val = parse_monetary_amount(m.group(1))
                if val is not None:
                    subtotal = val
            continue

        # Check Tax / GST / VAT
        if tax_amount is None and re.search(
            r"\b(?:sales\s*tax|tax\s*amount|tax|gst|vat|cgst|sgst|igst)\b", lower
        ) and "invoice" not in lower and "id" not in lower and "number" not in lower:
            m = re.search(amt_tail, line, re.IGNORECASE)
            if m:
                val = parse_monetary_amount(m.group(1))
                if val is not None:
                    tax_amount = val
            continue

        # Check Grand Total / Total Due / Amount Due / Balance Due
        if re.search(
            r"\b(?:grand\s*total|total\s*due|amount\s*due|balance\s*due|total\s*amount|total)\b",
            lower,
        ) and not re.search(r"\b(?:sub\s*[-]?total|line\s*total|item\s*total)\b", lower):
            m = re.search(amt_tail, line, re.IGNORECASE)
            if m:
                val = parse_monetary_amount(m.group(1))
                if val is not None and (grand_total is None or "grand" in lower or "due" in lower):
                    grand_total = val

    # Multi-line fallback if label and amount were split across consecutive lines
    if grand_total is None:
        m = re.search(
            r"(?:Grand\s*Total|Total\s*Due|Amount\s*Due|Balance\s*Due|Total)\s*[:\-]?\s*([$€£₹]?\s*(?:USD|EUR|GBP|INR|Rs\.?)?\s*\d[\d,.]*)",
            raw_text,
            re.IGNORECASE,
        )
        if m:
            grand_total = parse_monetary_amount(m.group(1))

    if subtotal is None:
        m = re.search(
            r"(?:Sub\s*[-]?total)\s*[:\-]?\s*([$€£₹]?\s*(?:USD|EUR|GBP|INR|Rs\.?)?\s*\d[\d,.]*)",
            raw_text,
            re.IGNORECASE,
        )
        if m:
            subtotal = parse_monetary_amount(m.group(1))

    if tax_amount is None:
        m = re.search(
            r"(?:Tax|GST|VAT)\s*(?:\(\d+%?\))?\s*[:\-]?\s*([$€£₹]?\s*(?:USD|EUR|GBP|INR|Rs\.?)?\s*\d[\d,.]*)",
            raw_text,
            re.IGNORECASE,
        )
        if m:
            tax_amount = parse_monetary_amount(m.group(1))

    return (
        round(subtotal or 0.0, 2),
        round(tax_amount or 0.0, 2),
        round(grand_total or 0.0, 2),
    )


def _extract_line_items(raw_text: str) -> list[LineItem]:
    """Parses tabular line items from raw invoice text.

    Supports:
    1) <Description>  <Qty>  <Unit Price>  <Line Total>
    2) <Description>  <Amount> (excluding summary/header lines)
    """
    items: list[LineItem] = []
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]

    # Pattern 1: Description + Qty + Unit Price + Line Total
    full_row_re = re.compile(
        r"^(?P<desc>[A-Za-z][A-Za-z0-9\s\-\(\)\/\.,&+#]{2,65}?)\s+"
        r"(?P<qty>\d+(?:\.\d+)?)\s+"
        r"(?:[$€£₹]|USD|EUR|GBP|INR|Rs\.?)?\s*(?P<unit>\d[\d,.]*)\s+"
        r"(?:[$€£₹]|USD|EUR|GBP|INR|Rs\.?)?\s*(?P<total>\d[\d,.]*)$",
        re.IGNORECASE,
    )

    # Pattern 2: Description + at least 2 spaces + single amount with decimals
    two_col_re = re.compile(
        r"^(?P<desc>[A-Za-z][A-Za-z0-9\s\-\(\)\/\.,&+#]{2,65}?)\s{2,}"
        r"(?:[$€£₹]|USD|EUR|GBP|INR|Rs\.?)?\s*(?P<total>\d[\d,]*\.\d{2})$",
        re.IGNORECASE,
    )

    for line in lines:
        lower = line.lower()
        # Skip headers, dates, invoice numbers, and summary lines
        if any(
            lower.startswith(kw) or re.search(rf"\b{re.escape(kw)}\b", lower)
            for kw in _SUMMARY_LINE_KEYWORDS
        ):
            continue
        if any(
            tok in lower
            for tok in (
                "description",
                "unit price",
                "qty",
                "quantity",
                "invoice #",
                "invoice no",
                "invoice number",
                "invoice date",
                "date:",
                "issued:",
                "bill to",
                "ship to",
            )
        ):
            continue

        m_full = full_row_re.match(line)
        if m_full:
            desc = m_full.group("desc").strip(" -:")
            qty = parse_monetary_amount(m_full.group("qty")) or 1.0
            unit_p = parse_monetary_amount(m_full.group("unit")) or 0.0
            tot_p = parse_monetary_amount(m_full.group("total")) or 0.0
            if desc and tot_p > 0:
                items.append(
                    LineItem(
                        description=desc,
                        quantity=round(qty, 2),
                        unit_price=round(unit_p, 2),
                        line_total=round(tot_p, 2),
                    )
                )
            continue

        m_two = two_col_re.match(line)
        if m_two:
            desc = m_two.group("desc").strip(" -:")
            tot_p = parse_monetary_amount(m_two.group("total")) or 0.0
            if desc and tot_p > 0:
                items.append(
                    LineItem(
                        description=desc,
                        quantity=1.0,
                        unit_price=round(tot_p, 2),
                        line_total=round(tot_p, 2),
                    )
                )

    return items


def extract_invoice_fields(
    raw_text: str,
    file_path: str,
    method: ExtractionMethod,
    vendor_store: Optional[VendorProfileStore] = None,
) -> InvoiceRecord:
    """Extracts structured InvoiceRecord fields and line items from raw document text."""
    path_obj = Path(file_path)
    matched_profile: Optional[VendorProfile] = None
    if vendor_store is not None:
        matched_profile = vendor_store.match_vendor(raw_text)

    if matched_profile and matched_profile.vendor_name:
        vendor_name = matched_profile.vendor_name
    else:
        vendor_name = _extract_vendor_name_heuristic(raw_text)

    invoice_number = _extract_invoice_number(raw_text, matched_profile)
    invoice_date = _extract_invoice_date(raw_text, matched_profile)

    default_curr = (
        matched_profile.default_currency
        if (matched_profile and matched_profile.default_currency)
        else get_default_currency()
    )
    currency = detect_currency(raw_text, default=default_curr)

    subtotal, tax_amount, grand_total = _extract_totals(raw_text, matched_profile)
    line_items = _extract_line_items(raw_text)

    # If subtotal was not explicitly labeled but line_items exist and grand_total > 0:
    if subtotal == 0.0 and line_items and grand_total > 0 and tax_amount == 0.0:
        computed_sub = round(sum(i.line_total for i in line_items), 2)
        if computed_sub == grand_total:
            subtotal = computed_sub

    return InvoiceRecord(
        record_id=str(uuid.uuid4()),
        file_path=str(path_obj),
        file_name=path_obj.name,
        extraction_method=method,
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        currency=currency,
        subtotal=subtotal,
        tax_amount=tax_amount,
        grand_total=grand_total,
        line_items=line_items,
        raw_text=raw_text,
    )
