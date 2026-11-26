"""Main Studio Application Window for Automated Invoice & Receipt Parser Utility."""

from pathlib import Path
import tkinter as tk
from tkinter import ttk
from src.gui.components.folder_toolbar import FolderToolbar
from src.gui.components.summary_bar import SummaryBar
from src.gui.styles import apply_forest_slate_theme


class InvoiceParserApp:
    """High-DPI Windows Desktop Studio Shell for Invoice & Receipt Parsing."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Automated Invoice & Receipt Parser Utility v1.0.0")
        self.root.geometry("1360x820")
        self.root.minsize(1080, 680)

        self._set_window_icon()
        self.style = apply_forest_slate_theme(self.root)

        self.toolbar = FolderToolbar(self.root)
        self.toolbar.pack(fill=tk.X)

        self.summary_bar = SummaryBar(self.root)
        self.summary_bar.pack(fill=tk.X)

        self.workspace_frame = ttk.Frame(self.root)
        self.workspace_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    def _set_window_icon(self) -> None:
        """Sets the window icon from assets/app_icon.ico if available."""
        project_root = Path(__file__).resolve().parent.parent.parent
        icon_path = project_root / "assets" / "app_icon.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(default=str(icon_path))
            except tk.TclError:
                pass
