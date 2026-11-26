"""Live Financial KPI Summary Bar displaying 4 key metrics cards."""

import tkinter as tk
from tkinter import ttk
from src.gui.styles import (
    COLOR_AMBER_WARN,
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_EMERALD_OK,
    COLOR_FOREST_PRIMARY,
    COLOR_RED_ERROR,
    COLOR_SLATE_HEADER,
    COLOR_TEXT_MUTED,
    FONT_KPI_LABEL,
    FONT_KPI_VALUE,
)
from src.models.invoice_model import AuditStatus, InvoiceRecord


class SummaryBar(ttk.Frame):
    """Displays 4 live financial KPI cards: Invoices Scanned, Total Spend, Total Tax/GST, and Flagged."""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent)
        self.var_scanned = tk.StringVar(value="0")
        self.var_spend = tk.StringVar(value="USD 0.00")
        self.var_tax = tk.StringVar(value="USD 0.00")
        self.var_flagged = tk.StringVar(value="0")

        self._flagged_value_label: tk.Label | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        container = tk.Frame(self, bg="#F8FAFC")
        container.pack(fill=tk.X, padx=10, pady=4)

        for col in range(4):
            container.columnconfigure(col, weight=1, uniform="kpi")

        self._create_card(
            container,
            col=0,
            title="INVOICES SCANNED",
            var=self.var_scanned,
            accent_color=COLOR_SLATE_HEADER,
        )
        self._create_card(
            container,
            col=1,
            title="TOTAL SPEND",
            var=self.var_spend,
            accent_color=COLOR_FOREST_PRIMARY,
        )
        self._create_card(
            container,
            col=2,
            title="TOTAL TAX / GST",
            var=self.var_tax,
            accent_color=COLOR_SLATE_HEADER,
        )
        self._flagged_value_label = self._create_card(
            container,
            col=3,
            title="FLAGGED / NEEDS REVIEW",
            var=self.var_flagged,
            accent_color=COLOR_EMERALD_OK,
        )

    def _create_card(
        self,
        parent: tk.Widget,
        col: int,
        title: str,
        var: tk.StringVar,
        accent_color: str,
    ) -> tk.Label:
        card = tk.Frame(
            parent,
            bg=COLOR_BG_CARD,
            highlightbackground=COLOR_BORDER,
            highlightthickness=1,
            padx=14,
            pady=8,
        )
        card.grid(row=0, column=col, sticky="ew", padx=4)

        lbl_title = tk.Label(
            card,
            text=title,
            bg=COLOR_BG_CARD,
            fg=COLOR_TEXT_MUTED,
            font=FONT_KPI_LABEL,
            anchor="w",
        )
        lbl_title.pack(fill=tk.X)

        lbl_val = tk.Label(
            card,
            textvariable=var,
            bg=COLOR_BG_CARD,
            fg=accent_color,
            font=FONT_KPI_VALUE,
            anchor="w",
        )
        lbl_val.pack(fill=tk.X, pady=(2, 0))
        return lbl_val

    def update_summary(self, records: list[InvoiceRecord]) -> None:
        """Recalculates and updates all 4 KPI cards from the given batch of InvoiceRecords."""
        count = len(records)
        total_spend = sum(r.grand_total for r in records)
        total_tax = sum(r.tax_amount for r in records)
        flagged_count = sum(1 for r in records if r.audit_status != AuditStatus.OK)

        primary_currency = "USD"
        for r in records:
            if r.currency:
                primary_currency = r.currency
                break

        self.var_scanned.set(f"{count:,}")
        self.var_spend.set(f"{primary_currency} {total_spend:,.2f}")
        self.var_tax.set(f"{primary_currency} {total_tax:,.2f}")
        self.var_flagged.set(f"{flagged_count:,}")

        if self._flagged_value_label is not None:
            if flagged_count == 0:
                self._flagged_value_label.configure(fg=COLOR_EMERALD_OK)
            elif any(
                r.audit_status in (AuditStatus.DUPLICATE, AuditStatus.FAILED)
                for r in records
            ):
                self._flagged_value_label.configure(fg=COLOR_RED_ERROR)
            else:
                self._flagged_value_label.configure(fg=COLOR_AMBER_WARN)
