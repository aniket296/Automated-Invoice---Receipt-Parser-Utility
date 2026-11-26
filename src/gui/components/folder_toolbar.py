"""Top action toolbar with Folder, Rules, and Export & Archive control groups."""

from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
import fitz  # PyMuPDF

from src.gui.styles import (
    COLOR_BG_CARD,
    COLOR_SLATE_HEADER,
    COLOR_TEXT_MUTED,
    FONT_BODY,
    FONT_HEADER_SUB,
    FONT_HEADER_TITLE,
    FONT_MONO,
)


def generate_demo_invoice_pack(target_dir: Optional[str] = None) -> Path:
    """Generates 3 synthetic sample invoices (1 clean, 1 math-mismatch, 1 duplicate) in a temp folder."""
    demo_dir = (
        Path(target_dir)
        if target_dir
        else Path(tempfile.mkdtemp(prefix="invoice_demo_pack_"))
    )
    demo_dir.mkdir(parents=True, exist_ok=True)

    samples = [
        (
            "01_Northwind_Cloud_Clean.pdf",
            "Northwind Cloud Services Ltd.",
            "INV-2026-101",
            "2026-11-18",
            [
                ("Dedicated GPU Cluster Node", 2, 250.00, 500.00),
                ("Enterprise Managed Backup", 1, 100.00, 100.00),
            ],
            600.00,
            60.00,
            660.00,
        ),
        (
            "02_Fabrikam_Office_MathMismatch.pdf",
            "Fabrikam Office Logistics Inc.",
            "INV-2026-204",
            "2026-11-20",
            [
                ("Standing Desk Workstation", 2, 175.00, 350.00),
                ("Monitor Arm Dual Mount", 1, 50.00, 50.00),
            ],
            400.00,
            40.00,
            495.00,  # Intentional math mismatch: 400 + 40 != 495
        ),
        (
            "03_Northwind_Cloud_Duplicate.pdf",
            "Northwind Cloud Services Ltd.",
            "INV-2026-101",  # Intentional duplicate of 01
            "2026-11-18",
            [
                ("Dedicated GPU Cluster Node", 2, 250.00, 500.00),
                ("Enterprise Managed Backup", 1, 100.00, 100.00),
            ],
            600.00,
            60.00,
            660.00,
        ),
    ]

    for fname, vendor, inv_no, inv_date, items, sub, tax, grand in samples:
        pdf_path = demo_dir / fname
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        lines = [
            "TAX INVOICE",
            vendor,
            f"Invoice #: {inv_no}",
            f"Invoice Date: {inv_date}",
            "Bill To: Accounts Payable Department",
            "",
            "Description  Qty  Unit Price  Line Total",
        ]
        for desc, qty, unit_p, line_tot in items:
            lines.append(f"{desc}  {qty}  ${unit_p:.2f}  ${line_tot:.2f}")
        lines.extend(
            [
                "",
                f"Subtotal: ${sub:.2f}",
                f"Tax (10%): ${tax:.2f}",
                f"Grand Total: ${grand:.2f}",
            ]
        )
        y = 55
        for ln in lines:
            page.insert_text((48, y), ln, fontsize=12)
            y += 22
        doc.save(str(pdf_path))
        doc.close()

    return demo_dir


class FolderToolbar(ttk.Frame):
    """Studio header banner and grouped action bar for folder scan, rules, and exports."""

    def __init__(
        self,
        parent: tk.Widget,
        on_select_folder: Optional[Callable[[], None]] = None,
        on_scan_folder: Optional[Callable[[], None]] = None,
        on_load_demo_pack: Optional[Callable[[], None]] = None,
        on_manage_profiles: Optional[Callable[[], None]] = None,
        on_export_summary_csv: Optional[Callable[[], None]] = None,
        on_export_line_items_csv: Optional[Callable[[], None]] = None,
        on_archive_ok_files: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.on_select_folder = on_select_folder
        self.on_scan_folder = on_scan_folder
        self.on_load_demo_pack = on_load_demo_pack
        self.on_manage_profiles = on_manage_profiles
        self.on_export_summary_csv = on_export_summary_csv
        self.on_export_line_items_csv = on_export_line_items_csv
        self.on_archive_ok_files = on_archive_ok_files

        self.folder_var = tk.StringVar(value="No folder selected")
        self._build_ui()

    def _build_ui(self) -> None:
        # Dark Slate Brand Header
        header = tk.Frame(self, bg=COLOR_SLATE_HEADER, padx=14, pady=8)
        header.pack(fill=tk.X)

        title_lbl = tk.Label(
            header,
            text="AUTOMATED INVOICE & RECEIPT PARSER UTILITY",
            bg=COLOR_SLATE_HEADER,
            fg="#FFFFFF",
            font=FONT_HEADER_TITLE,
        )
        title_lbl.pack(side=tk.LEFT)

        sub_lbl = tk.Label(
            header,
            text="Hybrid PyMuPDF + Offline RapidOCR  |  Math Integrity & Duplicate Auditor  |  Side-by-Side Verification Studio",
            bg=COLOR_SLATE_HEADER,
            fg="#94A3B8",
            font=FONT_HEADER_SUB,
        )
        sub_lbl.pack(side=tk.RIGHT)

        # Action Control Strip
        bar = tk.Frame(self, bg=COLOR_BG_CARD, padx=10, pady=8, relief=tk.SOLID, bd=1)
        bar.pack(fill=tk.X, padx=10, pady=(8, 4))

        # Group 1: Folder
        folder_group = ttk.LabelFrame(bar, text=" Folder & Demo ")
        folder_group.pack(side=tk.LEFT, padx=(0, 8), pady=2)

        self.btn_select_folder = ttk.Button(
            folder_group,
            text="Select Invoice Folder...",
            command=self._handle_select_folder,
        )
        self.btn_select_folder.pack(side=tk.LEFT, padx=4, pady=4)

        self.btn_scan_now = ttk.Button(
            folder_group,
            text="Scan Folder Now",
            style="Primary.TButton",
            command=self._handle_scan_folder,
        )
        self.btn_scan_now.pack(side=tk.LEFT, padx=4, pady=4)

        self.btn_demo_pack = ttk.Button(
            folder_group,
            text="Load Demo Invoice Pack",
            style="Secondary.TButton",
            command=self._handle_load_demo,
        )
        self.btn_demo_pack.pack(side=tk.LEFT, padx=4, pady=4)

        # Group 2: Rules
        rules_group = ttk.LabelFrame(bar, text=" Rules ")
        rules_group.pack(side=tk.LEFT, padx=8, pady=2)

        self.btn_manage_profiles = ttk.Button(
            rules_group,
            text="Manage Vendor Profiles...",
            command=self._handle_manage_profiles,
        )
        self.btn_manage_profiles.pack(side=tk.LEFT, padx=6, pady=4)

        # Group 3: Export & Archive
        export_group = ttk.LabelFrame(bar, text=" Export & Archive ")
        export_group.pack(side=tk.LEFT, padx=8, pady=2)

        self.btn_export_summary = ttk.Button(
            export_group,
            text="Export Summary CSV",
            style="Primary.TButton",
            command=self._handle_export_summary,
        )
        self.btn_export_summary.pack(side=tk.LEFT, padx=4, pady=4)

        self.btn_export_lines = ttk.Button(
            export_group,
            text="Export Line-Items CSV",
            command=self._handle_export_lines,
        )
        self.btn_export_lines.pack(side=tk.LEFT, padx=4, pady=4)

        self.btn_archive_ok = ttk.Button(
            export_group,
            text="Archive OK Files -> /Processed",
            command=self._handle_archive_ok,
        )
        self.btn_archive_ok.pack(side=tk.LEFT, padx=4, pady=4)

        # Active Folder Path Strip
        path_strip = tk.Frame(self, bg=COLOR_BG_CARD, padx=12, pady=3)
        path_strip.pack(fill=tk.X, padx=10)
        tk.Label(
            path_strip,
            text="Active Inbox Folder:",
            bg=COLOR_BG_CARD,
            fg=COLOR_TEXT_MUTED,
            font=FONT_BODY,
        ).pack(side=tk.LEFT)
        tk.Label(
            path_strip,
            textvariable=self.folder_var,
            bg=COLOR_BG_CARD,
            fg=COLOR_SLATE_HEADER,
            font=FONT_MONO,
        ).pack(side=tk.LEFT, padx=6)

    def set_folder_path(self, folder_path: str) -> None:
        """Updates the displayed active inbox folder path."""
        self.folder_var.set(folder_path)

    def set_scanning_state(self, is_scanning: bool) -> None:
        """Enables or disables toolbar buttons while a scan is running."""
        state = "disabled" if is_scanning else "normal"
        for btn in (
            self.btn_select_folder,
            self.btn_scan_now,
            self.btn_demo_pack,
            self.btn_export_summary,
            self.btn_export_lines,
            self.btn_archive_ok,
        ):
            btn.configure(state=state)

    def _handle_select_folder(self) -> None:
        if self.on_select_folder:
            self.on_select_folder()

    def _handle_scan_folder(self) -> None:
        if self.on_scan_folder:
            self.on_scan_folder()

    def _handle_load_demo(self) -> None:
        if self.on_load_demo_pack:
            self.on_load_demo_pack()

    def _handle_manage_profiles(self) -> None:
        if self.on_manage_profiles:
            self.on_manage_profiles()

    def _handle_export_summary(self) -> None:
        if self.on_export_summary_csv:
            self.on_export_summary_csv()

    def _handle_export_lines(self) -> None:
        if self.on_export_line_items_csv:
            self.on_export_line_items_csv()

    def _handle_archive_ok(self) -> None:
        if self.on_archive_ok_files:
            self.on_archive_ok_files()
