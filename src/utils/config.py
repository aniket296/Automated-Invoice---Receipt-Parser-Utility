"""Application configuration loader and local app data directory manager."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


def get_app_data_dir() -> Path:
    """Returns and ensures existence of ~/.invoice_receipt_parser/ directory."""
    app_dir = Path.home() / ".invoice_receipt_parser"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_vendor_profiles_path() -> Path:
    """Returns the default JSON path for storing custom VendorProfiles."""
    return get_app_data_dir() / "vendor_profiles.json"


def get_log_file_path() -> Path:
    """Returns the default rotating log file path."""
    return get_app_data_dir() / "app.log"


def get_app_log_level() -> str:
    """Returns configured logging level (default INFO)."""
    return os.getenv("APP_LOG_LEVEL", "INFO").upper().strip()


def get_ocr_render_dpi() -> int:
    """Returns configured PDF rendering DPI for OCR fallback (default 220)."""
    try:
        dpi = int(os.getenv("OCR_RENDER_DPI", "220"))
        return max(72, min(dpi, 600))
    except (ValueError, TypeError):
        return 220


def get_math_tolerance() -> float:
    """Returns configured math audit tolerance (default 0.02)."""
    try:
        tol = float(os.getenv("MATH_TOLERANCE", "0.02"))
        return max(0.0, tol)
    except (ValueError, TypeError):
        return 0.02


def get_max_worker_threads() -> int:
    """Returns configured worker thread count for batch scanning (default 4)."""
    try:
        workers = int(os.getenv("MAX_WORKER_THREADS", "4"))
        return max(1, min(workers, 16))
    except (ValueError, TypeError):
        return 4


def get_default_currency() -> str:
    """Returns configured default currency code (default USD)."""
    curr = os.getenv("DEFAULT_CURRENCY", "USD").upper().strip()
    return curr if curr else "USD"
