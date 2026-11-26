"""Currency detection, monetary amount normalization, and invoice date parser."""

from datetime import datetime
import re
from typing import Optional


def detect_currency(text: str, default: str = "USD") -> str:
    """Detects currency code from raw text symbols or ISO codes.

    Supports:
    - $ / USD -> USD
    - € / EUR -> EUR
    - £ / GBP -> GBP
    - ₹ / INR / Rs. -> INR
    """
    if not text:
        return default

    # Explicit symbol checks
    if "€" in text or re.search(r"\bEUR\b", text, re.IGNORECASE):
        return "EUR"
    if "£" in text or re.search(r"\bGBP\b", text, re.IGNORECASE):
        return "GBP"
    if "₹" in text or re.search(r"\b(?:INR|Rs)\b", text, re.IGNORECASE):
        return "INR"
    if "$" in text or re.search(r"\bUSD\b", text, re.IGNORECASE):
        return "USD"

    return default


def parse_monetary_amount(raw_str: str) -> Optional[float]:
    """Parses a raw currency string into a clean float.

    Handles:
    - Currency symbols ($, €, £, ₹, Rs., USD, EUR, GBP, INR)
    - US/UK format with comma thousands separator and dot decimal: 1,234.56
    - European format with dot/space thousands separator and comma decimal: 1.234,56 or 1234,56
    - Parentheses or leading minus for negative amounts
    """
    if raw_str is None:
        return None
    cleaned = str(raw_str).strip()
    if not cleaned:
        return None

    is_negative = False
    if (cleaned.startswith("(") and cleaned.endswith(")")) or "-" in cleaned:
        if re.search(r"(?:^|\s|\()-\s*\d|^\(.*\)$", cleaned):
            is_negative = True

    # Strip currency words and symbols (taking care not to eat trailing dot of Rs.)
    cleaned = re.sub(
        r"(?i)\b(?:USD|EUR|GBP|INR|CAD|AUD)\b|(?:^|\s)Rs\.?(?=\s|\d|$)|[$€£₹()+\-]",
        "",
        cleaned,
    ).strip()

    # Extract numeric portion containing digits, commas, dots, spaces
    match = re.search(r"\d[\d\s,.]*\d|\d", cleaned)
    if not match:
        return None

    num_str = match.group(0).replace(" ", "")

    if "," in num_str and "." in num_str:
        last_comma = num_str.rfind(",")
        last_dot = num_str.rfind(".")
        if last_comma > last_dot:
            # European format: 1.234,56
            num_str = num_str.replace(".", "").replace(",", ".")
        else:
            # US format: 1,234.56
            num_str = num_str.replace(",", "")
    elif "," in num_str:
        parts = num_str.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            # Decimal comma: 1234,56
            num_str = num_str.replace(",", ".")
        else:
            # Thousands comma: 1,234 or 1,234,567
            num_str = num_str.replace(",", "")
    elif num_str.count(".") > 1:
        # Multiple dots used as thousands separators: 1.234.567
        num_str = num_str.replace(".", "")

    try:
        value = float(num_str)
        return -value if is_negative else value
    except ValueError:
        return None


_DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%m-%d-%Y",
    "%d.%m.%Y",
    "%d-%b-%Y",
    "%d %b %Y",
    "%d %b, %Y",
    "%d-%B-%Y",
    "%d %B %Y",
    "%d %B, %Y",
    "%b %d, %Y",
    "%b %d %Y",
    "%B %d, %Y",
    "%B %d %Y",
    "%d/%m/%y",
    "%m/%d/%y",
    "%y-%m-%d",
]


def normalize_date_string(raw_str: str) -> Optional[str]:
    """Parses common invoice date formats into standardized ISO YYYY-MM-DD."""
    if not raw_str:
        return None

    candidate = str(raw_str).strip()
    # Remove ordinal suffixes like 1st, 2nd, 3rd, 4th before month or year
    candidate = re.sub(r"\b(\d{1,2})(?:st|nd|rd|th)\b", r"\1", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"\s+", " ", candidate).strip(" .,:;")

    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(candidate, fmt)
            if 1990 <= dt.year <= 2100:
                return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Try extracting an embedded date pattern from a longer string
    patterns = [
        r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b",
        r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b",
        r"\b\d{1,2}[-\s]+[A-Za-z]{3,9}[-\s,]+\d{4}\b",
        r"\b[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}\b",
    ]
    for pat in patterns:
        m = re.search(pat, candidate)
        if m:
            sub = m.group(0).strip()
            for fmt in _DATE_FORMATS:
                try:
                    dt = datetime.strptime(sub, fmt)
                    if 1990 <= dt.year <= 2100:
                        return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue

    return None
