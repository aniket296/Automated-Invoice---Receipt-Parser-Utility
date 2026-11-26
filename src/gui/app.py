"""Main Studio Application Window with End-to-End Multithreaded Wiring, Vendor Profile Modal & Dual CSV Export."""

from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Optional

from src.core.batch_scanner import InvoiceBatchScanner, archive_verified_invoices
from src.core.csv_exporter import export_line_items_csv, export_summary_ledger_csv
from src.core.integrity_auditor import audit_invoice_batch
from src.core.ocr_engine import HybridOcrEngine
from src.core.vendor_profiles import VendorProfileStore
from src.gui.components.folder_toolbar import FolderToolbar, generate_demo_invoice_pack
from src.gui.components.invoice_table import InvoiceTable
from src.gui.components.summary_bar import SummaryBar
from src.gui.components.verification_pane import VerificationPane
from src.gui.styles import (
    COLOR_BG_CARD,
    COLOR_SLATE_HEADER,
    COLOR_TEXT_MUTED,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SECTION_TITLE,
    apply_forest_slate_theme,
)
from src.models.invoice_model import AuditStatus, InvoiceRecord
from src.models.vendor_rule import VendorProfile
from src.utils.config import get_math_tolerance
from src.utils.logger import get_gui_log_queue, get_logger

logger = get_logger()


class VendorProfileModal(tk.Toplevel):
    """Modal dialog allowing users to add, edit, or delete custom VendorProfile regex rules."""

    def __init__(
        self,
        parent: tk.Widget,
        vendor_store: VendorProfileStore,
        on_profiles_updated: Optional[Any] = None,
    ) -> None:
        super().__init__(parent)
        self.title("Manage Custom Vendor Extraction Profiles")
        self.geometry("760x480")
        self.minsize(700, 440)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self.vendor_store = vendor_store
        self.on_profiles_updated = on_profiles_updated

        self.var_vendor_name = tk.StringVar()
        self.var_keywords = tk.StringVar()
        self.var_inv_regex = tk.StringVar()
        self.var_date_regex = tk.StringVar()
        self.var_total_regex = tk.StringVar()
        self.var_tax_regex = tk.StringVar()
        self.var_currency = tk.StringVar(value="USD")

        self._build_ui()
        self._refresh_list()

    def _build_ui(self) -> None:
        container = ttk.Frame(self, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        # Left side: Existing Profiles List
        left_frame = ttk.LabelFrame(container, text=" Saved Vendor Profiles ")
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.profile_listbox = tk.Listbox(
            left_frame,
            width=26,
            font=FONT_BODY,
            exportselection=False,
        )
        self.profile_listbox.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.profile_listbox.bind("<<ListboxSelect>>", self._on_select_profile)

        left_btns = ttk.Frame(left_frame)
        left_btns.pack(fill=tk.X, padx=6, pady=(0, 6))

        ttk.Button(
            left_btns,
            text="+ New",
            command=self._clear_form,
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            left_btns,
            text="Delete Selected",
            command=self._delete_selected,
        ).pack(side=tk.RIGHT, padx=2)

        # Right side: Profile Regex Editor Form
        right_frame = ttk.LabelFrame(container, text=" Vendor Profile Configuration ")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        form = tk.Frame(right_frame, bg=COLOR_BG_CARD, padx=12, pady=10)
        form.pack(fill=tk.BOTH, expand=True)

        fields = [
            ("Vendor Display Name *:", self.var_vendor_name, "e.g. Northwind Cloud Services"),
            ("Match Keywords (comma-separated) *:", self.var_keywords, "e.g. northwind, nw-cloud"),
            ("Invoice Number Regex (group 1):", self.var_inv_regex, r"e.g. Invoice\s*#:\s*([A-Z0-9\-]+)"),
            ("Date Regex (group 1):", self.var_date_regex, r"e.g. Date:\s*(\d{4}-\d{2}-\d{2})"),
            ("Grand Total Regex (group 1):", self.var_total_regex, r"e.g. Grand Total:\s*\$?([\d,.]+)"),
            ("Tax / GST Regex (group 1):", self.var_tax_regex, r"e.g. Tax:\s*\$?([\d,.]+)"),
            ("Default Currency:", self.var_currency, "USD, EUR, GBP, or INR"),
        ]

        for idx, (label_txt, var, hint) in enumerate(fields):
            tk.Label(
                form,
                text=label_txt,
                bg=COLOR_BG_CARD,
                fg=COLOR_SLATE_HEADER,
                font=FONT_BODY_BOLD,
                anchor="w",
            ).grid(row=idx * 2, column=0, sticky="w", pady=(4, 0))

            ent = ttk.Entry(form, textvariable=var, width=42)
            ent.grid(row=idx * 2, column=1, sticky="ew", padx=(8, 0), pady=(4, 0))

            tk.Label(
                form,
                text=hint,
                bg=COLOR_BG_CARD,
                fg=COLOR_TEXT_MUTED,
                font=("Segoe UI", 8),
                anchor="w",
            ).grid(row=idx * 2 + 1, column=1, sticky="w", padx=(8, 0), pady=(0, 2))

        form.columnconfigure(1, weight=1)

        action_bar = tk.Frame(form, bg=COLOR_BG_CARD)
        action_bar.grid(row=len(fields) * 2, column=0, columnspan=2, sticky="e", pady=(12, 0))

        ttk.Button(
            action_bar,
            text="Close",
            command=self.destroy,
        ).pack(side=tk.RIGHT, padx=4)

        ttk.Button(
            action_bar,
            text="💾 Save Vendor Profile",
            style="Primary.TButton",
            command=self._save_profile,
        ).pack(side=tk.RIGHT, padx=4)

    def _refresh_list(self) -> None:
        self.profile_listbox.delete(0, tk.END)
        for prof in self.vendor_store.get_all_profiles():
            self.profile_listbox.insert(tk.END, prof.vendor_name)

    def _on_select_profile(self, _event: tk.Event) -> None:
        sel = self.profile_listbox.curselection()
        if not sel:
            return
        profiles = self.vendor_store.get_all_profiles()
        idx = sel[0]
        if 0 <= idx < len(profiles):
            prof = profiles[idx]
            self.var_vendor_name.set(prof.vendor_name)
            self.var_keywords.set(", ".join(prof.match_keywords))
            self.var_inv_regex.set(prof.invoice_number_regex)
            self.var_date_regex.set(prof.date_regex)
            self.var_total_regex.set(prof.total_regex)
            self.var_tax_regex.set(prof.tax_regex)
            self.var_currency.set(prof.default_currency or "USD")

    def _clear_form(self) -> None:
        self.profile_listbox.selection_clear(0, tk.END)
        self.var_vendor_name.set("")
        self.var_keywords.set("")
        self.var_inv_regex.set("")
        self.var_date_regex.set("")
        self.var_total_regex.set("")
        self.var_tax_regex.set("")
        self.var_currency.set("USD")

    def _save_profile(self) -> None:
        name = self.var_vendor_name.get().strip()
        keywords = [k.strip() for k in self.var_keywords.get().split(",") if k.strip()]
        if not name or not keywords:
            messagebox.showwarning(
                "Validation",
                "Vendor Display Name and at least one Match Keyword are required.",
                parent=self,
            )
            return

        profile = VendorProfile(
            vendor_name=name,
            match_keywords=keywords,
            invoice_number_regex=self.var_inv_regex.get().strip(),
            date_regex=self.var_date_regex.get().strip(),
            total_regex=self.var_total_regex.get().strip(),
            tax_regex=self.var_tax_regex.get().strip(),
            default_currency=self.var_currency.get().strip().upper() or "USD",
        )
        self.vendor_store.add_or_update_profile(profile)
        self._refresh_list()
        if self.on_profiles_updated:
            self.on_profiles_updated()
        messagebox.showinfo(
            "Saved",
            f"Vendor profile '{name}' saved to {self.vendor_store.json_path.name}.",
            parent=self,
        )

    def _delete_selected(self) -> None:
        sel = self.profile_listbox.curselection()
        if not sel:
            return
        name = self.profile_listbox.get(sel[0])
        if self.vendor_store.delete_profile(name):
            self._refresh_list()
            self._clear_form()
            if self.on_profiles_updated:
                self.on_profiles_updated()


class InvoiceParserApp:
    """High-DPI Windows Desktop Studio Application for Invoice & Receipt Parsing."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Automated Invoice & Receipt Parser Utility v1.0.0")
        self.root.geometry("1380x840")
        self.root.minsize(1100, 700)

        self._set_window_icon()
        self.style = apply_forest_slate_theme(self.root)

        self.ocr_engine = HybridOcrEngine()
        self.vendor_store = VendorProfileStore()
        self.scanner = InvoiceBatchScanner(
            ocr_engine=self.ocr_engine,
            vendor_store=self.vendor_store,
        )

        self.current_folder: Optional[str] = None
        self.records: list[InvoiceRecord] = []
        self._ui_event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._log_queue = get_gui_log_queue()
        self._scan_thread: Optional[threading.Thread] = None

        self.status_var = tk.StringVar(
            value="Ready. Click 'Load Demo Invoice Pack' or 'Select Invoice Folder...' to begin."
        )
        self.progress_var = tk.DoubleVar(value=0.0)

        self._build_layout()
        self._schedule_ui_polling()

    def _set_window_icon(self) -> None:
        """Sets the window icon from assets/app_icon.ico if available."""
        project_root = Path(__file__).resolve().parent.parent.parent
        icon_path = project_root / "assets" / "app_icon.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(default=str(icon_path))
            except tk.TclError:
                pass

    def _build_layout(self) -> None:
        # 1. Top Folder & Action Toolbar
        self.toolbar = FolderToolbar(
            self.root,
            on_select_folder=self.action_select_folder,
            on_scan_folder=self.action_scan_current_folder,
            on_load_demo_pack=self.action_load_demo_pack,
            on_manage_profiles=self.action_open_vendor_profiles_modal,
            on_export_summary_csv=self.action_export_summary_csv,
            on_export_line_items_csv=self.action_export_line_items_csv,
            on_archive_ok_files=self.action_archive_verified_files,
        )
        self.toolbar.pack(fill=tk.X)

        # 2. Live Financial KPI Strip
        self.summary_bar = SummaryBar(self.root)
        self.summary_bar.pack(fill=tk.X)

        # 3. Center Split Workspace (InvoiceTable on Left, VerificationPane on Right)
        self.center_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.center_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        left_queue_container = ttk.LabelFrame(
            self.center_paned, text=" Incoming Invoice & Receipt Queue "
        )
        self.center_paned.add(left_queue_container, weight=5)

        self.invoice_table = InvoiceTable(
            left_queue_container,
            on_record_selected=self._on_table_record_selected,
        )
        self.invoice_table.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        right_verify_container = ttk.Frame(self.center_paned)
        self.center_paned.add(right_verify_container, weight=6)

        self.verification_pane = VerificationPane(
            right_verify_container,
            on_record_saved=self._on_record_inline_saved,
        )
        self.verification_pane.pack(fill=tk.BOTH, expand=True)

        # 4. Bottom Progress & Status Bar
        bottom_bar = tk.Frame(
            self.root,
            bg=COLOR_SLATE_HEADER,
            padx=12,
            pady=5,
        )
        bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = tk.Label(
            bottom_bar,
            textvariable=self.status_var,
            bg=COLOR_SLATE_HEADER,
            fg="#F8FAFC",
            font=FONT_BODY,
            anchor="w",
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.progressbar = ttk.Progressbar(
            bottom_bar,
            variable=self.progress_var,
            maximum=100.0,
            length=220,
            mode="determinate",
        )
        self.progressbar.pack(side=tk.RIGHT, padx=(10, 0))

    def _schedule_ui_polling(self) -> None:
        """Polls background worker events and log queue every 100ms without blocking Tkinter."""
        self._process_queues()
        self.root.after(100, self._schedule_ui_polling)

    def _process_queues(self) -> None:
        # Drain worker UI events
        while True:
            try:
                event_type, payload = self._ui_event_queue.get_nowait()
            except queue.Empty:
                break

            if event_type == "PROGRESS":
                done, total, fname = payload
                pct = (done / float(max(1, total))) * 100.0
                self.progress_var.set(pct)
                self.status_var.set(f"Scanning ({done}/{total}): {fname}...")

            elif event_type == "SCAN_COMPLETE":
                scanned_records: list[InvoiceRecord] = payload
                self.records = scanned_records
                self.toolbar.set_scanning_state(False)
                self.progress_var.set(100.0)
                self.summary_bar.update_summary(self.records)
                self.invoice_table.set_records(self.records)
                ok_count = sum(1 for r in self.records if r.audit_status == AuditStatus.OK)
                flagged = len(self.records) - ok_count
                self.status_var.set(
                    f"Scan complete: {len(self.records)} invoice(s) processed "
                    f"({ok_count} OK, {flagged} flagged for review)."
                )

            elif event_type == "SCAN_ERROR":
                err_msg = str(payload)
                self.toolbar.set_scanning_state(False)
                self.progress_var.set(0.0)
                self.status_var.set(f"Scan failed: {err_msg}")
                messagebox.showerror("Scan Error", err_msg, parent=self.root)

        # Drain logger queue without overwriting active scan progress
        while True:
            try:
                _log_msg = self._log_queue.get_nowait()
            except queue.Empty:
                break

    def _on_table_record_selected(self, record: Optional[InvoiceRecord]) -> None:
        self.verification_pane.load_record(record)

    def _on_record_inline_saved(self, updated_record: InvoiceRecord) -> None:
        """Re-audits the entire batch after inline edits and updates table & KPI summary bar."""
        audit_invoice_batch(self.records, tolerance=get_math_tolerance())
        self.summary_bar.update_summary(self.records)
        self.invoice_table.refresh_table(preserve_selection_id=updated_record.record_id)
        self.status_var.set(
            f"Saved corrections for '{updated_record.file_name}' -> Status: {updated_record.audit_status.value}"
        )

    def action_select_folder(self) -> None:
        """Prompts user to choose an invoice inbox folder and triggers a scan."""
        chosen = filedialog.askdirectory(
            title="Select Folder Containing PDF Invoices & Receipt Images",
            parent=self.root,
        )
        if not chosen:
            return
        self.current_folder = chosen
        self.toolbar.set_folder_path(chosen)
        self.action_scan_current_folder()

    def action_load_demo_pack(self) -> None:
        """Generates the 3-invoice demo pack in a temp folder and immediately scans it."""
        demo_dir = generate_demo_invoice_pack()
        self.current_folder = str(demo_dir)
        self.toolbar.set_folder_path(self.current_folder)
        self.status_var.set(f"Generated 3 demo invoices in {self.current_folder}. Scanning...")
        self.action_scan_current_folder()

    def action_scan_current_folder(self) -> None:
        """Starts a background thread running InvoiceBatchScanner on current_folder."""
        if not self.current_folder:
            messagebox.showinfo(
                "Select Folder",
                "Please select an invoice folder first or click 'Load Demo Invoice Pack'.",
                parent=self.root,
            )
            return

        if self._scan_thread and self._scan_thread.is_alive():
            return

        self.toolbar.set_scanning_state(True)
        self.progress_var.set(0.0)
        self.status_var.set(f"Discovering invoices in {self.current_folder}...")

        folder_target = self.current_folder

        def _worker() -> None:
            try:
                self.vendor_store.load()
                records = self.scanner.scan_folder(
                    folder_target,
                    progress_callback=lambda done, total, fname: self._ui_event_queue.put(
                        ("PROGRESS", (done, total, fname))
                    ),
                )
                self._ui_event_queue.put(("SCAN_COMPLETE", records))
            except Exception as exc:
                logger.exception("Background folder scan failed: %s", exc)
                self._ui_event_queue.put(("SCAN_ERROR", str(exc)))

        self._scan_thread = threading.Thread(target=_worker, daemon=True)
        self._scan_thread.start()

    def action_open_vendor_profiles_modal(self) -> None:
        """Opens the modal dialog to add, edit, or delete custom VendorProfile regex rules."""
        VendorProfileModal(
            self.root,
            vendor_store=self.vendor_store,
            on_profiles_updated=lambda: self.status_var.set(
                f"Updated vendor profiles ({len(self.vendor_store.get_all_profiles())} active rules)."
            ),
        )

    def action_export_summary_csv(self) -> None:
        """Exports the Summary Ledger CSV."""
        if not self.records:
            messagebox.showinfo("No Data", "Scan a folder before exporting CSV.", parent=self.root)
            return
        save_path = filedialog.asksaveasfilename(
            title="Export Summary Ledger CSV",
            defaultextension=".csv",
            initialfile="invoice_summary_ledger.csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            parent=self.root,
        )
        if not save_path:
            return
        try:
            export_summary_ledger_csv(self.records, save_path)
            self.status_var.set(f"Exported Summary Ledger CSV ({len(self.records)} rows) to {save_path}")
            messagebox.showinfo(
                "Export Complete",
                f"Summary Ledger CSV exported successfully:\n{save_path}",
                parent=self.root,
            )
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc), parent=self.root)

    def action_export_line_items_csv(self) -> None:
        """Exports the Detailed Line-Items CSV."""
        if not self.records:
            messagebox.showinfo("No Data", "Scan a folder before exporting CSV.", parent=self.root)
            return
        save_path = filedialog.asksaveasfilename(
            title="Export Detailed Line-Items CSV",
            defaultextension=".csv",
            initialfile="invoice_line_items_detailed.csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            parent=self.root,
        )
        if not save_path:
            return
        try:
            export_line_items_csv(self.records, save_path)
            total_items = sum(len(r.line_items) for r in self.records)
            self.status_var.set(f"Exported Line-Items CSV ({total_items} items) to {save_path}")
            messagebox.showinfo(
                "Export Complete",
                f"Detailed Line-Items CSV ({total_items} rows) exported successfully:\n{save_path}",
                parent=self.root,
            )
        except Exception as exc:
            messagebox.showerror("Export Error", str(exc), parent=self.root)

    def action_archive_verified_files(self) -> None:
        """Moves AuditStatus.OK files into <current_folder>/Processed/."""
        if not self.records or not self.current_folder:
            messagebox.showinfo(
                "No Verified Files",
                "Scan a folder with verified (OK) invoices before archiving.",
                parent=self.root,
            )
            return

        ok_candidates = [
            r for r in self.records if r.audit_status == AuditStatus.OK and not r.is_archived
        ]
        if not ok_candidates:
            messagebox.showinfo(
                "Nothing to Archive",
                "No unarchived invoices with 'OK' audit status were found.",
                parent=self.root,
            )
            return

        moved_count = archive_verified_invoices(self.records, self.current_folder)
        self.invoice_table.refresh_table()
        self.status_var.set(
            f"Archived {moved_count} verified invoice(s) to {Path(self.current_folder) / 'Processed'}."
        )
        messagebox.showinfo(
            "Archive Complete",
            f"Moved {moved_count} verified (OK) invoice file(s) into:\n{Path(self.current_folder) / 'Processed'}",
            parent=self.root,
        )
