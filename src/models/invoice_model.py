"""Domain models for invoice records, line items, extraction methods, and audit statuses."""

from dataclasses import dataclass, field
from enum import Enum


class ExtractionMethod(str, Enum):
    """Method used to extract raw text from an invoice or receipt document."""

    DIGITAL_PDF = "DIGITAL_PDF"
    LOCAL_OCR = "LOCAL_OCR"
    FAILED = "FAILED"


class AuditStatus(str, Enum):
    """Automated integrity audit status for a parsed invoice record."""

    OK = "OK"
    MATH_MISMATCH = "MATH_MISMATCH"
    DUPLICATE = "DUPLICATE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"


@dataclass
class LineItem:
    """Single itemized product or service line within an invoice."""

    description: str
    quantity: float = 1.0
    unit_price: float = 0.0
    line_total: float = 0.0

    def to_dict(self) -> dict:
        """Serializes the line item to a plain dictionary."""
        return {
            "description": self.description,
            "quantity": float(self.quantity),
            "unit_price": float(self.unit_price),
            "line_total": float(self.line_total),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LineItem":
        """Deserializes a LineItem from a dictionary."""
        return cls(
            description=str(data.get("description", "")),
            quantity=float(data.get("quantity", 1.0)),
            unit_price=float(data.get("unit_price", 0.0)),
            line_total=float(data.get("line_total", 0.0)),
        )


@dataclass
class InvoiceRecord:
    """Complete structured representation of a parsed invoice or receipt."""

    record_id: str
    file_path: str
    file_name: str
    extraction_method: ExtractionMethod = ExtractionMethod.DIGITAL_PDF
    vendor_name: str = ""
    invoice_number: str = ""
    invoice_date: str = ""  # Normalized YYYY-MM-DD
    currency: str = "USD"
    subtotal: float = 0.0
    tax_amount: float = 0.0
    grand_total: float = 0.0
    line_items: list[LineItem] = field(default_factory=list)
    raw_text: str = ""
    audit_status: AuditStatus = AuditStatus.NEEDS_REVIEW
    audit_notes: list[str] = field(default_factory=list)
    is_archived: bool = False
    duration_ms: float = 0.0
