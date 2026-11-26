"""Side-by-Side Visual Verification & Inline Editing Workspace Pane."""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Callable, Optional
from PIL import ImageTk

from src.core.ocr_engine import render_document_preview
from src.gui.styles import (
    COLOR_AMBER_BG,
    COLOR_AMBER_WARN,
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_EMERALD_BG,
    COLOR_EMERALD_OK,
    COLOR_RED_BG,
    COLOR_RED_ERROR,
    COLOR_SLATE_HEADER,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_MONO,
)
from src.models.invoice_model import AuditStatus, InvoiceRecord, LineItem
from src.utils.currency_parser import normalize_date_string, parse_monetary_amount


class LineItemDialog(tk.Toplevel):
    """Compact modal dialog to add or edit an invoice LineItem."""

    def __init__(
        self,
        parent: tk.Widget,
        initial: Optional[LineItem] = None,
    ) -> None:
        super().__init__(parent)
        self.title("Add / Edit Line Item")
        self.geometry("380x230")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self.result: Optional[LineItem] = None

        self.var_desc = tk.StringVar(value=initial.description if initial else "")
        self.var_qty = tk.StringVar(value=f"{initial.quantity:.2f}" if initial else "1.00")
        self.var_unit = tk.StringVar(value=f"{initial.unit_price:.2f}" if initial else "0.00")
        self.var_total = tk.StringVar(value=f"{initial.line_total:.2f}" if initial else "0.00")

        frame = ttk.Frame(self, padding=14)
        frame.pack(fill=tk.BOTH, expand=True)

        fields = [
            ("Description:", self.var_desc),
            ("Quantity:", self.var_qty),
            ("Unit Price:", self.var_unit),
            ("Line Total:", self.var_total),
        ]
        for idx, (label_text, var) in enumerate(fields):
            ttk.Label(frame, text=label_text).grid(row=idx, column=0, sticky="w", pady=4)
            ent = ttk.Entry(frame, textvariable=var, width=28)
            ent.grid(row=idx, column=1, sticky="ew", padx=(8, 0), pady=4)
            if idx in (1, 2):
                ent.bind("<FocusOut>", self._auto_calc_total)

        frame.columnconfigure(1, weight=1)

        btn_bar = ttk.Frame(frame)
        btn_bar.grid(row=4, column=0, columnspan=2, pady=(14, 0), sticky="e")

        ttk.Button(btn_bar, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=4)
        ttk.Button(
            btn_bar,
            text="Save Item",
            style="Primary.TButton",
            command=self._on_save,
        ).pack(side=tk.RIGHT, padx=4)

    def _auto_calc_total(self, _event: Optional[tk.Event] = None) -> None:
        try:
            q = float(self.var_qty.get())
            u = float(self.var_unit.get())
            if q > 0 and u > 0:
                self.var_total.set(f"{q * u:.2f}")
        except ValueError:
            pass

    def _on_save(self) -> None:
        desc = self.var_desc.get().strip()
        if not desc:
            messagebox.showwarning("Validation", "Description is required.", parent=self)
            return
        qty = parse_monetary_amount(self.var_qty.get()) or 1.0
        unit_p = parse_monetary_amount(self.var_unit.get()) or 0.0
        tot_p = parse_monetary_amount(self.var_total.get())
        if tot_p is None or tot_p == 0.0:
            tot_p = round(qty * unit_p, 2)

        self.result = LineItem(
            description=desc,
            quantity=round(qty, 2),
            unit_price=round(unit_p, 2),
            line_total=round(tot_p, 2),
        )
        self.destroy()


class VerificationPane(ttk.Frame):
    """Split right-hand verification workspace with Visual Preview and Inline Editing."""

    def __init__(
        self,
        parent: tk.Widget,
        on_record_saved: Optional[Callable[[InvoiceRecord], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.on_record_saved = on_record_saved
        self.current_record: Optional[InvoiceRecord] = None
        self._working_line_items: list[LineItem] = []
        self._photo_image: Optional[ImageTk.PhotoImage] = None

        # Editable Form Variables
        self.var_vendor = tk.StringVar()
        self.var_invoice_no = tk.StringVar()
        self.var_invoice_date = tk.StringVar()
        self.var_currency = tk.StringVar(value="USD")
        self.var_subtotal = tk.StringVar(value="0.00")
        self.var_tax = tk.StringVar(value="0.00")
        self.var_grand_total = tk.StringVar(value="0.00")

        self._build_ui()

    def _build_ui(self) -> None:
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # LEFT SUB-PANE: Visual Preview & Raw Text Tabs
        left_frame = ttk.LabelFrame(paned, text=" Document Preview & Raw Text ")
        paned.add(left_frame, weight=5)

        self.notebook = ttk.Notebook(left_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Tab 1: Scrollable Visual Page 1 Preview Canvas
        preview_tab = ttk.Frame(self.notebook)
        self.notebook.add(preview_tab, text="📄 Visual Preview (Page 1)")

        self.preview_canvas = tk.Canvas(
            preview_tab,
            bg="#E2E8F0",
            highlightthickness=0,
        )
        v_scroll = ttk.Scrollbar(preview_tab, orient=tk.VERTICAL, command=self.preview_canvas.yview)
        h_scroll = ttk.Scrollbar(preview_tab, orient=tk.HORIZONTAL, command=self.preview_canvas.xview)
        self.preview_canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.preview_canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        preview_tab.rowconfigure(0, weight=1)
        preview_tab.columnconfigure(0, weight=1)

        # Tab 2: Raw Extracted Text Inspector
        raw_tab = ttk.Frame(self.notebook)
        self.notebook.add(raw_tab, text="📝 Raw Extracted Text")

        self.raw_text_widget = tk.Text(
            raw_tab,
            wrap=tk.WORD,
            font=FONT_MONO,
            bg=COLOR_BG_CARD,
            fg=COLOR_SLATE_HEADER,
            padx=8,
            pady=8,
        )
        raw_scroll = ttk.Scrollbar(raw_tab, orient=tk.VERTICAL, command=self.raw_text_widget.yview)
        self.raw_text_widget.configure(yscrollcommand=raw_scroll.set)
        self.raw_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        raw_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # RIGHT SUB-PANE: Audit Alert Banner, Editable Fields & Line Items
        right_frame = ttk.LabelFrame(paned, text=" Editable Fields & Line Items ")
        paned.add(right_frame, weight=5)

        right_inner = tk.Frame(right_frame, bg=COLOR_BG_CARD, padx=10, pady=8)
        right_inner.pack(fill=tk.BOTH, expand=True)

        # Audit Alert Banner
        self.audit_banner = tk.Label(
            right_inner,
            text="Select an invoice from the queue to inspect and edit.",
            bg="#E2E8F0",
            fg=COLOR_SLATE_HEADER,
            font=FONT_BODY_BOLD,
            anchor="w",
            justify=tk.LEFT,
            wraplength=360,
            padx=10,
            pady=6,
            relief=tk.SOLID,
            bd=1,
        )
        self.audit_banner.pack(fill=tk.X, pady=(0, 8))

        # Editable Form Fields Grid
        form_frame = tk.Frame(right_inner, bg=COLOR_BG_CARD)
        form_frame.pack(fill=tk.X, pady=2)

        field_specs = [
            ("Vendor Name:", self.var_vendor),
            ("Invoice Number:", self.var_invoice_no),
            ("Invoice Date (YYYY-MM-DD):", self.var_invoice_date),
            ("Currency:", self.var_currency),
            ("Subtotal:", self.var_subtotal),
            ("Tax / GST:", self.var_tax),
            ("Grand Total:", self.var_grand_total),
        ]

        for row_idx, (lbl_txt, var) in enumerate(field_specs):
            tk.Label(
                form_frame,
                text=lbl_txt,
                bg=COLOR_BG_CARD,
                fg=COLOR_SLATE_HEADER,
                font=FONT_BODY_BOLD,
                anchor="w",
            ).grid(row=row_idx, column=0, sticky="w", pady=3)

            if lbl_txt == "Currency:":
                cmb = ttk.Combobox(
                    form_frame,
                    textvariable=var,
                    values=["USD", "EUR", "GBP", "INR", "CAD", "AUD"],
                    width=24,
                )
                cmb.grid(row=row_idx, column=1, sticky="ew", padx=(8, 0), pady=3)
            else:
                ent = ttk.Entry(form_frame, textvariable=var, width=26)
                ent.grid(row=row_idx, column=1, sticky="ew", padx=(8, 0), pady=3)

        form_frame.columnconfigure(1, weight=1)

        # Line Items Header & Buttons
        items_header = tk.Frame(right_inner, bg=COLOR_BG_CARD)
        items_header.pack(fill=tk.X, pady=(10, 4))

        tk.Label(
            items_header,
            text="Extracted Line Items:",
            bg=COLOR_BG_CARD,
            fg=COLOR_SLATE_HEADER,
            font=FONT_BODY_BOLD,
        ).pack(side=tk.LEFT)

        self.btn_remove_item = ttk.Button(
            items_header,
            text="- Remove Item",
            command=self._handle_remove_item,
        )
        self.btn_remove_item.pack(side=tk.RIGHT, padx=2)

        self.btn_add_item = ttk.Button(
            items_header,
            text="+ Add Item",
            command=self._handle_add_item,
        )
        self.btn_add_item.pack(side=tk.RIGHT, padx=2)

        # Compact LineItem Treeview
        items_tree_frame = tk.Frame(right_inner, bg=COLOR_BG_CARD)
        items_tree_frame.pack(fill=tk.BOTH, expand=True, pady=2)

        cols = ("description", "qty", "unit_price", "line_total")
        self.items_tree = ttk.Treeview(
            items_tree_frame,
            columns=cols,
            show="headings",
            height=5,
            selectmode="browse",
        )
        self.items_tree.heading("description", text="Description")
        self.items_tree.heading("qty", text="Qty")
        self.items_tree.heading("unit_price", text="Unit Price")
        self.items_tree.heading("line_total", text="Line Total")

        self.items_tree.column("description", width=155, anchor="w")
        self.items_tree.column("qty", width=48, anchor="center")
        self.items_tree.column("unit_price", width=75, anchor="e")
        self.items_tree.column("line_total", width=80, anchor="e")

        items_scroll = ttk.Scrollbar(
            items_tree_frame, orient=tk.VERTICAL, command=self.items_tree.yview
        )
        self.items_tree.configure(yscrollcommand=items_scroll.set)
        self.items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        items_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Prominent Save Corrections & Re-Audit Button
        self.btn_save_corrections = ttk.Button(
            right_inner,
            text="💾 Save Corrections & Re-Audit",
            style="Primary.TButton",
            command=self.save_current_record,
        )
        self.btn_save_corrections.pack(fill=tk.X, pady=(10, 2))

    def load_record(self, record: Optional[InvoiceRecord]) -> None:
        """Populates the preview canvas, raw text, audit banner, form fields, and line items."""
        self.current_record = record
        self.preview_canvas.delete("all")
        self.raw_text_widget.configure(state=tk.NORMAL)
        self.raw_text_widget.delete("1.0", tk.END)

        if record is None:
            self.audit_banner.configure(
                text="Select an invoice from the queue to inspect and edit.",
                bg="#E2E8F0",
                fg=COLOR_SLATE_HEADER,
            )
            self.var_vendor.set("")
            self.var_invoice_no.set("")
            self.var_invoice_date.set("")
            self.var_currency.set("USD")
            self.var_subtotal.set("0.00")
            self.var_tax.set("0.00")
            self.var_grand_total.set("0.00")
            self._working_line_items = []
            self._refresh_line_items_tree()
            return

        # Populate Audit Alert Banner
        self._update_audit_banner(record)

        # Populate Form Inputs
        self.var_vendor.set(record.vendor_name)
        self.var_invoice_no.set(record.invoice_number)
        self.var_invoice_date.set(record.invoice_date)
        self.var_currency.set(record.currency or "USD")
        self.var_subtotal.set(f"{record.subtotal:.2f}")
        self.var_tax.set(f"{record.tax_amount:.2f}")
        self.var_grand_total.set(f"{record.grand_total:.2f}")

        # Populate Line Items
        self._working_line_items = [
            LineItem(
                description=i.description,
                quantity=i.quantity,
                unit_price=i.unit_price,
                line_total=i.line_total,
            )
            for i in record.line_items
        ]
        self._refresh_line_items_tree()

        # Populate Raw Text
        self.raw_text_widget.insert(tk.END, record.raw_text or "(No text extracted)")

        # Render Page 1 Visual Preview
        pil_img = render_document_preview(record.file_path, max_width=460)
        self._photo_image = ImageTk.PhotoImage(pil_img)
        self.preview_canvas.create_image(10, 10, anchor=tk.NW, image=self._photo_image)
        self.preview_canvas.configure(
            scrollregion=(0, 0, pil_img.width + 20, pil_img.height + 20)
        )

    def _update_audit_banner(self, record: InvoiceRecord) -> None:
        if record.audit_status == AuditStatus.OK:
            self.audit_banner.configure(
                text="✅ AUDIT OK — Math integrity verified and no duplicates detected.",
                bg=COLOR_EMERALD_BG,
                fg="#065F46",
            )
        elif record.audit_status == AuditStatus.DUPLICATE:
            notes = " | ".join(record.audit_notes) or "Duplicate invoice detected."
            self.audit_banner.configure(
                text=f"🔴 DUPLICATE — {notes}",
                bg=COLOR_RED_BG,
                fg="#991B1B",
            )
        elif record.audit_status == AuditStatus.MATH_MISMATCH:
            notes = " | ".join(record.audit_notes) or "Math integrity mismatch."
            self.audit_banner.configure(
                text=f"⚠️ MATH MISMATCH — {notes}",
                bg=COLOR_AMBER_BG,
                fg="#92400E",
            )
        else:
            notes = " | ".join(record.audit_notes) or "Needs manual review."
            self.audit_banner.configure(
                text=f"🔍 {record.audit_status.value} — {notes}",
                bg=COLOR_AMBER_BG,
                fg="#92400E",
            )

    def _refresh_line_items_tree(self) -> None:
        for item_id in self.items_tree.get_children():
            self.items_tree.delete(item_id)
        for idx, item in enumerate(self._working_line_items):
            self.items_tree.insert(
                "",
                tk.END,
                iid=str(idx),
                values=(
                    item.description,
                    f"{item.quantity:.2f}",
                    f"{item.unit_price:.2f}",
                    f"{item.line_total:.2f}",
                ),
            )

    def _handle_add_item(self) -> None:
        if self.current_record is None:
            return
        dlg = LineItemDialog(self)
        self.wait_window(dlg)
        if dlg.result is not None:
            self._working_line_items.append(dlg.result)
            self._refresh_line_items_tree()

    def _handle_remove_item(self) -> None:
        if self.current_record is None:
            return
        sel = self.items_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self._working_line_items):
            self._working_line_items.pop(idx)
            self._refresh_line_items_tree()

    def add_line_item_direct(self, item: LineItem) -> None:
        """Programmatically appends a LineItem to the working list and refreshes the view."""
        self._working_line_items.append(item)
        self._refresh_line_items_tree()

    def save_current_record(self) -> bool:
        """Applies form edits to current_record and invokes the re-audit callback."""
        if self.current_record is None:
            return False

        self.current_record.vendor_name = self.var_vendor.get().strip()
        self.current_record.invoice_number = self.var_invoice_no.get().strip()

        raw_date = self.var_invoice_date.get().strip()
        norm_date = normalize_date_string(raw_date)
        self.current_record.invoice_date = norm_date if norm_date else raw_date

        self.current_record.currency = self.var_currency.get().strip().upper() or "USD"

        sub_val = parse_monetary_amount(self.var_subtotal.get())
        tax_val = parse_monetary_amount(self.var_tax.get())
        tot_val = parse_monetary_amount(self.var_grand_total.get())

        self.current_record.subtotal = round(sub_val if sub_val is not None else 0.0, 2)
        self.current_record.tax_amount = round(tax_val if tax_val is not None else 0.0, 2)
        self.current_record.grand_total = round(tot_val if tot_val is not None else 0.0, 2)

        self.current_record.line_items = list(self._working_line_items)

        if self.on_record_saved:
            self.on_record_saved(self.current_record)

        self._update_audit_banner(self.current_record)
        return True
