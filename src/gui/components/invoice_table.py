"""Filterable Invoice Queue Table with Audit Status Badges and Extraction Method Indicators."""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from src.gui.styles import (
    COLOR_AMBER_BG,
    COLOR_BG_CARD,
    COLOR_EMERALD_BG,
    COLOR_RED_BG,
    FONT_BODY,
    FONT_BODY_BOLD,
)
from src.models.invoice_model import AuditStatus, ExtractionMethod, InvoiceRecord

STATUS_BADGE_MAP: dict[AuditStatus, str] = {
    AuditStatus.OK: "✅ OK",
    AuditStatus.MATH_MISMATCH: "⚠️ MATH_MISMATCH",
    AuditStatus.DUPLICATE: "🔴 DUPLICATE",
    AuditStatus.NEEDS_REVIEW: "🔍 NEEDS_REVIEW",
    AuditStatus.FAILED: "🔴 FAILED",
}

METHOD_LABEL_MAP: dict[ExtractionMethod, str] = {
    ExtractionMethod.DIGITAL_PDF: "PDF",
    ExtractionMethod.LOCAL_OCR: "OCR",
    ExtractionMethod.FAILED: "ERR",
}


class InvoiceTable(ttk.Frame):
    """Filterable Treeview table displaying parsed InvoiceRecords and emitting selection callbacks."""

    def __init__(
        self,
        parent: tk.Widget,
        on_record_selected: Optional[Callable[[Optional[InvoiceRecord]], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.on_record_selected = on_record_selected
        self._records: list[InvoiceRecord] = []
        self._record_map: dict[str, InvoiceRecord] = {}

        self.filter_status_var = tk.StringVar(value="All")
        self.search_vendor_var = tk.StringVar(value="")

        self._build_ui()

    def _build_ui(self) -> None:
        # Top Filter Strip
        filter_bar = tk.Frame(self, bg=COLOR_BG_CARD, padx=8, pady=6, relief=tk.SOLID, bd=1)
        filter_bar.pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            filter_bar,
            text="Filter Status:",
            bg=COLOR_BG_CARD,
            font=FONT_BODY_BOLD,
        ).pack(side=tk.LEFT, padx=(2, 4))

        self.cmb_status = ttk.Combobox(
            filter_bar,
            textvariable=self.filter_status_var,
            values=["All", "OK", "MATH_MISMATCH", "DUPLICATE", "NEEDS_REVIEW"],
            state="readonly",
            width=16,
        )
        self.cmb_status.pack(side=tk.LEFT, padx=(0, 12))
        self.cmb_status.bind("<<ComboboxSelected>>", lambda _e: self.refresh_table())

        tk.Label(
            filter_bar,
            text="Search Vendor / File:",
            bg=COLOR_BG_CARD,
            font=FONT_BODY_BOLD,
        ).pack(side=tk.LEFT, padx=(2, 4))

        self.ent_search = ttk.Entry(
            filter_bar,
            textvariable=self.search_vendor_var,
            width=24,
        )
        self.ent_search.pack(side=tk.LEFT, padx=(0, 6))
        self.ent_search.bind("<KeyRelease>", lambda _e: self.refresh_table())

        btn_clear = ttk.Button(
            filter_bar,
            text="Clear",
            command=self._clear_filters,
        )
        btn_clear.pack(side=tk.LEFT, padx=2)

        # Scrollable Treeview Container
        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = (
            "file_name",
            "method",
            "vendor",
            "invoice_no",
            "date",
            "total",
            "audit_status",
        )
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        headings = [
            ("file_name", "File Name", 155, "w"),
            ("method", "Method", 58, "center"),
            ("vendor", "Vendor", 155, "w"),
            ("invoice_no", "Invoice #", 105, "w"),
            ("date", "Date", 88, "center"),
            ("total", "Total", 105, "e"),
            ("audit_status", "Audit Status", 138, "w"),
        ]
        for col_id, title, width, anchor in headings:
            self.tree.heading(col_id, text=title)
            self.tree.column(col_id, width=width, minwidth=50, anchor=anchor)

        # Row background tags for audit visual cues
        self.tree.tag_configure("OK", background=COLOR_EMERALD_BG)
        self.tree.tag_configure("MATH_MISMATCH", background=COLOR_AMBER_BG)
        self.tree.tag_configure("NEEDS_REVIEW", background=COLOR_AMBER_BG)
        self.tree.tag_configure("DUPLICATE", background=COLOR_RED_BG)
        self.tree.tag_configure("FAILED", background=COLOR_RED_BG)

        y_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _clear_filters(self) -> None:
        self.filter_status_var.set("All")
        self.search_vendor_var.set("")
        self.refresh_table()

    def set_records(self, records: list[InvoiceRecord]) -> None:
        """Sets the underlying list of InvoiceRecords and populates the table."""
        self._records = list(records)
        self._record_map = {r.record_id: r for r in self._records}
        self.refresh_table()

    def get_filtered_records(self) -> list[InvoiceRecord]:
        """Returns records matching the current status combobox and vendor search query."""
        status_filter = self.filter_status_var.get().strip()
        query = self.search_vendor_var.get().strip().lower()

        filtered: list[InvoiceRecord] = []
        for rec in self._records:
            if status_filter and status_filter != "All":
                if rec.audit_status.value != status_filter:
                    continue
            if query:
                haystack = f"{rec.vendor_name} {rec.file_name} {rec.invoice_number}".lower()
                if query not in haystack:
                    continue
            filtered.append(rec)
        return filtered

    def refresh_table(self, preserve_selection_id: Optional[str] = None) -> None:
        """Repopulates Treeview rows based on active filters."""
        current_sel = preserve_selection_id
        if current_sel is None:
            sel_items = self.tree.selection()
            if sel_items:
                current_sel = sel_items[0]

        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

        filtered = self.get_filtered_records()
        for rec in filtered:
            method_str = METHOD_LABEL_MAP.get(rec.extraction_method, "PDF")
            total_str = f"{rec.currency} {rec.grand_total:,.2f}"
            badge_str = STATUS_BADGE_MAP.get(rec.audit_status, rec.audit_status.value)
            display_name = f"[Archived] {rec.file_name}" if rec.is_archived else rec.file_name

            self.tree.insert(
                "",
                tk.END,
                iid=rec.record_id,
                values=(
                    display_name,
                    method_str,
                    rec.vendor_name or "(Unknown Vendor)",
                    rec.invoice_number or "—",
                    rec.invoice_date or "—",
                    total_str,
                    badge_str,
                ),
                tags=(rec.audit_status.value,),
            )

        if current_sel and self.tree.exists(current_sel):
            self.tree.selection_set(current_sel)
            self.tree.see(current_sel)
        elif filtered:
            first_id = filtered[0].record_id
            self.tree.selection_set(first_id)
            self._emit_selected(first_id)
        else:
            if self.on_record_selected:
                self.on_record_selected(None)

    def select_record_by_id(self, record_id: str) -> None:
        """Programmatically selects a row by record_id."""
        if self.tree.exists(record_id):
            self.tree.selection_set(record_id)
            self.tree.see(record_id)
            self._emit_selected(record_id)

    def _on_tree_select(self, _event: tk.Event) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        self._emit_selected(sel[0])

    def _emit_selected(self, record_id: str) -> None:
        rec = self._record_map.get(record_id)
        if self.on_record_selected:
            self.on_record_selected(rec)
