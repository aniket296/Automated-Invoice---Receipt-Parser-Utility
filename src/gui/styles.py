"""Forest-Slate Corporate Studio Theme & Typography Configuration."""

import tkinter as tk
from tkinter import ttk

# Color Palette
COLOR_SLATE_HEADER = "#0F172A"
COLOR_SLATE_SUBHEADER = "#1E293B"
COLOR_FOREST_PRIMARY = "#065F46"
COLOR_FOREST_HOVER = "#047857"
COLOR_EMERALD_OK = "#10B981"
COLOR_EMERALD_BG = "#ECFDF5"
COLOR_AMBER_WARN = "#F59E0B"
COLOR_AMBER_BG = "#FFFBEB"
COLOR_RED_ERROR = "#EF4444"
COLOR_RED_BG = "#FEF2F2"
COLOR_BG_MAIN = "#F8FAFC"
COLOR_BG_CARD = "#FFFFFF"
COLOR_BORDER = "#CBD5E1"
COLOR_TEXT_PRIMARY = "#0F172A"
COLOR_TEXT_MUTED = "#475569"

# Typography
FONT_FAMILY_UI = "Segoe UI"
FONT_FAMILY_MONO = "Consolas"

FONT_HEADER_TITLE = (FONT_FAMILY_UI, 14, "bold")
FONT_HEADER_SUB = (FONT_FAMILY_UI, 9)
FONT_SECTION_TITLE = (FONT_FAMILY_UI, 10, "bold")
FONT_BODY = (FONT_FAMILY_UI, 9)
FONT_BODY_BOLD = (FONT_FAMILY_UI, 9, "bold")
FONT_KPI_VALUE = (FONT_FAMILY_UI, 15, "bold")
FONT_KPI_LABEL = (FONT_FAMILY_UI, 8, "bold")
FONT_MONO = (FONT_FAMILY_MONO, 9)
FONT_MONO_BOLD = (FONT_FAMILY_MONO, 9, "bold")


def apply_forest_slate_theme(root: tk.Tk) -> ttk.Style:
    """Applies the Forest-Slate corporate theme using ttk.Style('clam')."""
    root.configure(bg=COLOR_BG_MAIN)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    # Base Frames & Labels
    style.configure("TFrame", background=COLOR_BG_MAIN)
    style.configure("Card.TFrame", background=COLOR_BG_CARD, relief="solid", borderwidth=1)
    style.configure("Header.TFrame", background=COLOR_SLATE_HEADER)
    style.configure("Toolbar.TFrame", background=COLOR_BG_CARD)

    style.configure(
        "TLabel",
        background=COLOR_BG_MAIN,
        foreground=COLOR_TEXT_PRIMARY,
        font=FONT_BODY,
    )
    style.configure(
        "Card.TLabel",
        background=COLOR_BG_CARD,
        foreground=COLOR_TEXT_PRIMARY,
        font=FONT_BODY,
    )
    style.configure(
        "Muted.TLabel",
        background=COLOR_BG_MAIN,
        foreground=COLOR_TEXT_MUTED,
        font=FONT_BODY,
    )
    style.configure(
        "Section.TLabel",
        background=COLOR_BG_MAIN,
        foreground=COLOR_SLATE_HEADER,
        font=FONT_SECTION_TITLE,
    )

    # Labelframes
    style.configure(
        "TLabelframe",
        background=COLOR_BG_CARD,
        bordercolor=COLOR_BORDER,
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "TLabelframe.Label",
        background=COLOR_BG_CARD,
        foreground=COLOR_SLATE_HEADER,
        font=FONT_BODY_BOLD,
    )

    # Primary Forest-Green Action Button
    style.configure(
        "Primary.TButton",
        background=COLOR_FOREST_PRIMARY,
        foreground="#FFFFFF",
        font=FONT_BODY_BOLD,
        padding=(10, 5),
        borderwidth=0,
    )
    style.map(
        "Primary.TButton",
        background=[("active", COLOR_FOREST_HOVER), ("disabled", "#94A3B8")],
        foreground=[("disabled", "#E2E8F0")],
    )

    # Secondary Slate Button
    style.configure(
        "Secondary.TButton",
        background=COLOR_SLATE_SUBHEADER,
        foreground="#FFFFFF",
        font=FONT_BODY_BOLD,
        padding=(10, 5),
        borderwidth=0,
    )
    style.map(
        "Secondary.TButton",
        background=[("active", "#334155"), ("disabled", "#94A3B8")],
    )

    # Standard Outline Button
    style.configure(
        "TButton",
        background="#E2E8F0",
        foreground=COLOR_TEXT_PRIMARY,
        font=FONT_BODY,
        padding=(8, 4),
    )
    style.map(
        "TButton",
        background=[("active", "#CBD5E1")],
    )

    # Treeview Styling
    style.configure(
        "Treeview",
        background=COLOR_BG_CARD,
        fieldbackground=COLOR_BG_CARD,
        foreground=COLOR_TEXT_PRIMARY,
        rowheight=26,
        font=FONT_BODY,
        bordercolor=COLOR_BORDER,
    )
    style.configure(
        "Treeview.Heading",
        background=COLOR_SLATE_HEADER,
        foreground="#FFFFFF",
        font=FONT_BODY_BOLD,
        padding=(6, 5),
        relief="flat",
    )
    style.map(
        "Treeview.Heading",
        background=[("active", COLOR_SLATE_SUBHEADER)],
    )
    style.map(
        "Treeview",
        background=[("selected", COLOR_FOREST_PRIMARY)],
        foreground=[("selected", "#FFFFFF")],
    )

    # Notebook Tabs
    style.configure("TNotebook", background=COLOR_BG_MAIN, borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background="#E2E8F0",
        foreground=COLOR_TEXT_PRIMARY,
        font=FONT_BODY_BOLD,
        padding=(10, 4),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLOR_FOREST_PRIMARY)],
        foreground=[("selected", "#FFFFFF")],
    )

    # Progressbar
    style.configure(
        "Horizontal.TProgressbar",
        troughcolor="#E2E8F0",
        background=COLOR_EMERALD_OK,
        thickness=10,
    )

    return style
