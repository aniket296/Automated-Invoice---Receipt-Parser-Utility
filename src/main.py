"""Application entry point with Windows High-DPI awareness configuration."""

import ctypes
import sys
import tkinter as tk
from src.gui.app import InvoiceParserApp
from src.utils.logger import get_logger

logger = get_logger()


def enable_windows_high_dpi() -> None:
    """Enables per-monitor High-DPI awareness on Windows 10/11."""
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def main() -> None:
    """Launches the Automated Invoice & Receipt Parser Utility GUI."""
    enable_windows_high_dpi()
    logger.info("Starting Automated Invoice & Receipt Parser Utility...")
    root = tk.Tk()
    _app = InvoiceParserApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
