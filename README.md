# Automated Invoice & Receipt Parser Utility

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011%20(x64)-0F172A?style=for-the-badge&logo=windows&logoColor=white" alt="Windows 10/11" />
  <img src="https://img.shields.io/badge/Python-3.11%2B-065F46?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/Hybrid%20OCR-PyMuPDF%20%2B%20Offline%20RapidOCR-10B981?style=for-the-badge" alt="Hybrid OCR" />
  <img src="https://img.shields.io/badge/Privacy-100%25%20Offline%20%2F%20Zero%20Cloud%20Fees-047857?style=for-the-badge" alt="Zero Cloud Fees" />
  <img src="https://img.shields.io/badge/Packaging-PyInstaller%20%26%20Inno%20Setup-1E293B?style=for-the-badge" alt="PyInstaller & Inno Setup" />
  <img src="https://img.shields.io/badge/License-MIT-F59E0B?style=for-the-badge" alt="License MIT" />
</p>

> **An industry-grade, 100% offline Windows 10/11 desktop bookkeeping & document verification studio** built for small business owners, freelancers, and local accounting teams. Batch-scan folders of PDF invoices and receipt images (`.pdf`, `.png`, `.jpg`, `.jpeg`), automatically audit math integrity and duplicate billings, visually verify and edit fields side-by-side, and export Excel-ready accounting ledgers in one click.

---

## Why This Exists (Real-World Impact)

Small businesses, independent contractors, and local bookkeeping teams process dozens to hundreds of vendor invoices and expense receipts every month. Existing cloud OCR services charge expensive recurring per-page SaaS fees and require uploading sensitive financial records (vendor contracts, bank details, tax IDs, and line-item pricing) to third-party servers.

**Automated Invoice & Receipt Parser Utility** solves this directly on your local Windows workstation:
- **Zero Recurring SaaS Fees:** Runs 100% locally with no API keys, no subscriptions, and no internet connection required.
- **100% Financial Data Privacy:** Every invoice, receipt image, vendor rule, and exported CSV stays strictly on your local disk.
- **Instant Digital Fast-Path + Offline AI OCR:** Extracts native digital PDFs in milliseconds via `PyMuPDF` and automatically falls back to an embedded ONNX `RapidOCR` engine only when scanned PDFs or camera receipt photos are encountered.
- **Automated Accounting Controls:** Catches billing errors (`Subtotal + Tax != Grand Total`), line-item sum discrepancies, and duplicate vendor invoices before you pay or import them into your accounting ledger.

---

## Key Features

1. **Hybrid Extraction Engine (`PyMuPDF` + `rapidocr-onnxruntime`)**
   - **Digital PDF Fast-Path:** Native digital PDFs with `>= 40` characters of embedded text bypass OCR completely and parse in milliseconds.
   - **Offline ONNX OCR Fallback:** Scanned PDFs and receipt images (`.png`, `.jpg`, `.jpeg`) are rasterized at configurable DPI (`220 DPI` default) and processed via a lazily initialized, thread-safe `RapidOCR` ONNX pipeline.
2. **Side-by-Side Visual Verification & Inline Editing Studio**
   - **Left Sub-Pane:** High-resolution scrollable Page 1 document preview alongside a **Raw Extracted Text** inspector tab.
   - **Right Sub-Pane:** Color-coded Audit Alert Banner, inline editable fields (`Vendor Name`, `Invoice Number`, `Invoice Date`, `Currency`, `Subtotal`, `Tax / GST`, `Grand Total`), and an interactive `LineItem` editor (`+ Add Item`, `- Remove Item`, `💾 Save Corrections & Re-Audit`).
3. **Automated Math Integrity & Duplicate Invoice Auditor**
   - Flags `MATH_MISMATCH` whenever `abs((Subtotal + Tax) - Grand Total) > tolerance` or when itemized line totals do not sum to the subtotal.
   - Flags `DUPLICATE` across the batch when matching `(vendor_name, invoice_number)` or `(vendor_name, invoice_date, grand_total)` combinations appear.
   - Flags `NEEDS_REVIEW` if critical fields (`Vendor Name` or `Grand Total`) are missing.
4. **Reusable Custom JSON Vendor Profiles**
   - Create and persist custom per-vendor keyword triggers and regex extraction rules (`~/.invoice_receipt_parser/vendor_profiles.json`) via the built-in **Manage Vendor Profiles...** modal.
5. **Dual Accounting CSV Export (UTF-8-SIG Excel-Ready)**
   - **Summary Ledger CSV:** One row per invoice with extraction method, vendor, invoice #, normalized `YYYY-MM-DD` date, currency, subtotal, tax, grand total, line-item count, audit status, and audit notes.
   - **Detailed Line-Items CSV:** One row per itemized `LineItem` linked to its parent invoice metadata for granular expense categorization.
6. **One-Click `/Processed` Inbox Archiver & Built-In Demo Pack**
   - **Load Demo Invoice Pack:** Generates 3 realistic sample PDF invoices (1 clean, 1 math-mismatch, 1 duplicate) so anyone can test the full workflow immediately.
   - **Archive OK Files -> `/Processed`:** Safely moves verified (`AuditStatus.OK`) files into `<inbox>/Processed/` with automatic filename collision handling.

---

## Visual Architecture Diagram

```text
invoice-receipt-parser/
├── .gitignore                        # Excludes .venv, build, dist, dist_installer, *.exe
├── .env.example                      # Isolated environment defaults (DPI, tolerance, threads)
├── README.md                         # Project documentation & quickstart guide
├── pyproject.toml                    # PEP 621 package metadata & pytest configuration
├── requirements.txt                  # Runtime dependencies (PyMuPDF, Pillow, RapidOCR, NumPy)
├── run_local.bat                     # One-click local environment bootstrapper & app launcher
├── build_windows.spec                # PyInstaller standalone .exe specification
├── assets/
│   └── app_icon.ico                  # Multi-resolution Forest-Slate receipt-checkmark icon
├── installer/
│   └── setup.iss                     # Inno Setup 6 Windows installer wizard script
├── scripts/
│   ├── generate_icon.py              # Programmatic Pillow multi-size ICO badge generator
│   ├── build_exe.bat                 # Runs pytest -> generates icon -> builds standalone .exe
│   └── build_installer.bat           # Runs build_exe.bat -> compiles Inno Setup installer
├── src/
│   ├── __init__.py
│   ├── main.py                       # Windows High-DPI entry point
│   ├── core/
│   │   ├── ocr_engine.py             # HybridOcrEngine (PyMuPDF fast-path + lazy RapidOCR)
│   │   ├── vendor_profiles.py        # VendorProfileStore JSON persistence & keyword matcher
│   │   ├── field_extractor.py        # Heuristic & regex-override field + line-item parser
│   │   ├── integrity_auditor.py      # Math integrity, line-item sum & duplicate auditor
│   │   ├── csv_exporter.py           # Dual UTF-8-SIG CSV exporters (Summary + Line Items)
│   │   └── batch_scanner.py          # Multi-threaded folder scanner & /Processed archiver
│   ├── gui/
│   │   ├── app.py                    # Main studio controller & VendorProfileModal editor
│   │   ├── styles.py                 # Forest-Slate corporate theme (#0F172A & #065F46)
│   │   └── components/
│   │       ├── folder_toolbar.py     # Action bar & 3-invoice synthetic Demo Pack generator
│   │       ├── summary_bar.py        # Live 4-card financial KPI summary strip
│   │       ├── invoice_table.py      # Filterable invoice queue table with audit badges
│   │       └── verification_pane.py  # Side-by-side Page 1 preview & inline field editor
│   ├── models/
│   │   ├── invoice_model.py          # ExtractionMethod, AuditStatus, LineItem, InvoiceRecord
│   │   └── vendor_rule.py            # VendorProfile dataclass & JSON serialization
│   └── utils/
│       ├── config.py                 # .env loader & ~/.invoice_receipt_parser/ manager
│       ├── currency_parser.py        # Multi-currency amount parser & ISO date normalizer
│       └── logger.py                 # Rotating file logger & thread-safe GUI queue handler
└── tests/
    ├── conftest.py                   # Synthetic digital PDF & scanned receipt PNG fixtures
    ├── test_currency_and_extractor.py
    ├── test_auditor_and_duplicates.py
    └── test_batch_ocr_and_csv.py
```

---

## Quickstart Guide (4 Options)

### Option 1: Windows Installer (`InvoiceReceiptParser_Setup.exe` from GitHub Releases)
1. Download `InvoiceReceiptParser_Setup.exe` from the repository's **Releases** page (or build it locally via Option 4).
2. Run the installer wizard to install the application, Start Menu shortcut, and optional Desktop icon.
3. Launch **Automated Invoice & Receipt Parser Utility** and click **Load Demo Invoice Pack** on the top toolbar to inspect 3 sample invoices immediately.

### Option 2: One-Click Local Source Launcher (`run_local.bat`)
Double-click `run_local.bat` in the repository root (or run it from Command Prompt / PowerShell):
```bat
run_local.bat
```
- Automatically creates `.venv` if missing, installs `requirements.txt`, generates `assets\app_icon.ico`, and launches the High-DPI desktop studio.

### Option 3: Developer Terminal Setup (`venv` + `pip install -e .`)
```powershell
# 1. Create and activate a Python 3.11 / 3.12 virtual environment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install package in editable mode with dev dependencies
pip install --upgrade pip
pip install -e ".[dev]"

# 3. Generate application icon and launch the desktop GUI
python scripts/generate_icon.py
python -m src.main
```

### Option 4: Rebuilding the Standalone `.exe` & Installer (`scripts\build_exe.bat` & `scripts\build_installer.bat`)
```bat
:: Build standalone single-file executable (dist\InvoiceReceiptParser.exe)
scripts\build_exe.bat

:: Build standalone .exe + Inno Setup Windows Installer (dist_installer\InvoiceReceiptParser_Setup.exe)
scripts\build_installer.bat
```
> **Note:** If Inno Setup 6 (`ISCC.exe`) is not installed on your machine, `scripts\build_installer.bat` exits cleanly (`exit /b 0`) after verifying `dist\InvoiceReceiptParser.exe` and prints the official download link (`https://jrsoftware.org/isdl.php`).

---

## Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **GUI Framework** | `tkinter` / `ttk` (`clam` theme) | High-DPI Windows 10/11 Forest-Slate corporate desktop studio |
| **Digital PDF Engine** | `PyMuPDF` (`fitz >= 1.24.0`) | Sub-10ms native text extraction & Page 1 visual preview rendering |
| **Offline OCR Engine** | `rapidocr-onnxruntime >= 1.3.16` | 100% offline ONNX text detection & recognition for scans/photos |
| **Image Processing** | `Pillow >= 10.0.0` & `NumPy >= 1.24.0` | Multi-resolution `.ico` generation, rasterization & array conversion |
| **Configuration** | `python-dotenv >= 1.0.1` | Environment config loading & `~/.invoice_receipt_parser/` persistence |
| **Testing** | `pytest >= 8.0.0` | Automated unit test suite with synthetic PDF and receipt PNG fixtures |
| **Packaging** | `PyInstaller >= 6.0.0` & `Inno Setup 6` | Standalone `InvoiceReceiptParser.exe` & Windows setup wizard |

---

## Running Automated Tests

Run the full unit test suite (covering US/European currency parsing, ISO date normalization, heuristic & custom regex field extraction, math integrity auditing, duplicate detection, hybrid OCR, and dual CSV exports):

```powershell
.\.venv\Scripts\pytest.exe
```

---

## License

Released under the **MIT License**.
