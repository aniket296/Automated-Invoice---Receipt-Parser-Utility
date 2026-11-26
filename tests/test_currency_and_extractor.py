"""Unit tests for currency detection, amount parsing, date normalization, and field extraction."""

from pathlib import Path
from src.core.field_extractor import extract_invoice_fields
from src.core.vendor_profiles import VendorProfileStore
from src.models.invoice_model import ExtractionMethod
from src.models.vendor_rule import VendorProfile
from src.utils.currency_parser import (
    detect_currency,
    normalize_date_string,
    parse_monetary_amount,
)


def test_detect_currency_symbols_and_codes() -> None:
    """Verifies $, €, £, ₹ and ISO currency codes are properly detected."""
    assert detect_currency("Grand Total: $450.00") == "USD"
    assert detect_currency("Amount Due: USD 120.00") == "USD"
    assert detect_currency("Summe: € 1.250,00") == "EUR"
    assert detect_currency("Total EUR 89.50") == "EUR"
    assert detect_currency("Balance Due: £340.75") == "GBP"
    assert detect_currency("Invoice Total GBP 500") == "GBP"
    assert detect_currency("Net Payable: ₹ 12,500.00") == "INR"
    assert detect_currency("Grand Total: Rs. 850.00") == "INR"
    assert detect_currency("Total INR 999.00") == "INR"
    assert detect_currency("No symbol text", default="CAD") == "CAD"


def test_parse_monetary_amount_us_and_european() -> None:
    """Verifies US and European thousands/decimal separators parse into clean floats."""
    assert parse_monetary_amount("$1,234.56") == 1234.56
    assert parse_monetary_amount("USD 45,000.00") == 45000.00
    assert parse_monetary_amount("€ 1.234,56") == 1234.56
    assert parse_monetary_amount("1234,50") == 1234.50
    assert parse_monetary_amount("£99.95") == 99.95
    assert parse_monetary_amount("Rs. 1,500.25") == 1500.25
    assert parse_monetary_amount("($250.00)") == -250.00
    assert parse_monetary_amount("") is None
    assert parse_monetary_amount("N/A") is None


def test_normalize_date_string_formats() -> None:
    """Verifies common invoice date formats normalize to ISO YYYY-MM-DD."""
    assert normalize_date_string("2026-11-26") == "2026-11-26"
    assert normalize_date_string("26/11/2026") == "2026-11-26"
    assert normalize_date_string("11/26/2026") == "2026-11-26"
    assert normalize_date_string("26-Nov-2026") == "2026-11-26"
    assert normalize_date_string("November 26, 2026") == "2026-11-26"
    assert normalize_date_string("Nov 26th, 2026") == "2026-11-26"
    assert normalize_date_string("Invalid Date String") is None


def test_extract_invoice_fields_heuristic() -> None:
    """Verifies heuristic extraction of vendor, invoice #, date, totals, and line items."""
    raw_text = "\n".join(
        [
            "TAX INVOICE",
            "BlueHorizon Logistics Group",
            "Invoice Number: BHL-2026-309",
            "Invoice Date: 15-Nov-2026",
            "",
            "Description  Qty  Unit Price  Line Total",
            "Express Freight Container  2  400.00  800.00",
            "Customs Clearance Fee  1  150.00  150.00",
            "",
            "Subtotal: $950.00",
            "Tax (10%): $95.00",
            "Grand Total: $1,045.00",
        ]
    )

    record = extract_invoice_fields(
        raw_text=raw_text,
        file_path="bhl_invoice.pdf",
        method=ExtractionMethod.DIGITAL_PDF,
    )

    assert record.vendor_name == "BlueHorizon Logistics Group"
    assert record.invoice_number == "BHL-2026-309"
    assert record.invoice_date == "2026-11-15"
    assert record.currency == "USD"
    assert record.subtotal == 950.00
    assert record.tax_amount == 95.00
    assert record.grand_total == 1045.00
    assert len(record.line_items) == 2
    assert record.line_items[0].description == "Express Freight Container"
    assert record.line_items[0].quantity == 2.0
    assert record.line_items[0].line_total == 800.00


def test_vendor_profile_custom_regex_overrides(tmp_path: Path) -> None:
    """Verifies VendorProfileStore persistence and custom regex extraction overrides."""
    store_file = tmp_path / "custom_profiles.json"
    store = VendorProfileStore(store_file)

    profile = VendorProfile(
        vendor_name="EuroTech GmbH",
        match_keywords=["eurotech", "et-billing"],
        invoice_number_regex=r"Ref-ID:\s*(ET-\d+)",
        date_regex=r"BillingTag:\s*(\d{2}\.\d{2}\.\d{4})",
        total_regex=r"Endbetrag:\s*([\d.,]+)",
        tax_regex=r"MwSt:\s*([\d.,]+)",
        default_currency="EUR",
    )
    store.add_or_update_profile(profile)

    # Reload from disk to verify JSON persistence
    reloaded_store = VendorProfileStore(store_file)
    assert len(reloaded_store.get_all_profiles()) == 1

    raw_text = "\n".join(
        [
            "ET-BILLING PORTAL DOCUMENT",
            "Ref-ID: ET-88421",
            "BillingTag: 19.11.2026",
            "MwSt: 19,00",
            "Endbetrag: 119,00",
        ]
    )

    rec = extract_invoice_fields(
        raw_text=raw_text,
        file_path="eurotech.pdf",
        method=ExtractionMethod.DIGITAL_PDF,
        vendor_store=reloaded_store,
    )

    assert rec.vendor_name == "EuroTech GmbH"
    assert rec.invoice_number == "ET-88421"
    assert rec.invoice_date == "2026-11-19"
    assert rec.currency == "EUR"
    assert rec.tax_amount == 19.00
    assert rec.grand_total == 119.00

    assert reloaded_store.delete_profile("EuroTech GmbH") is True
    assert len(reloaded_store.get_all_profiles()) == 0
