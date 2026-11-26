"""Domain model for reusable custom vendor regex extraction profiles."""

from dataclasses import dataclass, field


@dataclass
class VendorProfile:
    """Custom vendor identification and field extraction regex profile."""

    vendor_name: str
    match_keywords: list[str] = field(default_factory=list)
    invoice_number_regex: str = ""
    date_regex: str = ""
    total_regex: str = ""
    tax_regex: str = ""
    default_currency: str = ""

    def to_dict(self) -> dict:
        """Serializes VendorProfile to a JSON-compatible dictionary."""
        return {
            "vendor_name": self.vendor_name,
            "match_keywords": list(self.match_keywords),
            "invoice_number_regex": self.invoice_number_regex,
            "date_regex": self.date_regex,
            "total_regex": self.total_regex,
            "tax_regex": self.tax_regex,
            "default_currency": self.default_currency,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VendorProfile":
        """Deserializes VendorProfile from a dictionary."""
        raw_keywords = data.get("match_keywords", [])
        if isinstance(raw_keywords, str):
            keywords = [k.strip() for k in raw_keywords.split(",") if k.strip()]
        else:
            keywords = [str(k).strip() for k in raw_keywords if str(k).strip()]
        return cls(
            vendor_name=str(data.get("vendor_name", "")).strip(),
            match_keywords=keywords,
            invoice_number_regex=str(data.get("invoice_number_regex", "")).strip(),
            date_regex=str(data.get("date_regex", "")).strip(),
            total_regex=str(data.get("total_regex", "")).strip(),
            tax_regex=str(data.get("tax_regex", "")).strip(),
            default_currency=str(data.get("default_currency", "")).strip(),
        )
