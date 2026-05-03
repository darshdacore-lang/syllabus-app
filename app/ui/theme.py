from tkinter import ttk

PALETTE = {
    "bg": "#f3efe6",
    "surface": "#fbf8f2",
    "surface_alt": "#efe6d6",
    "text": "#2a241d",
    "muted": "#6a6158",
    "accent": "#215145",
    "accent_soft": "#d9ebe6",
    "accent_hover": "#2b6758",
    "border": "#d7cdbd",
    "success": "#4caf50",
    "warning": "#ff9800",
}

FONT_DISPLAY = ("Helvetica Neue", 36, "bold")
FONT_TITLE = ("Helvetica Neue", 22, "bold")
FONT_BODY = ("Helvetica Neue", 12)
FONT_BODY_SMALL = ("Helvetica Neue", 11)
FONT_MUTED = ("Helvetica Neue", 10)


def configure_styles(root):
    root.configure(bg=PALETTE["bg"])
    style = ttk.Style(root)

    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure("App.TFrame", background=PALETTE["bg"])
    style.configure(
        "Card.TFrame",
        background=PALETTE["surface"],
        relief="solid",
        borderwidth=1,
    )
    style.configure(
        "Title.TLabel",
        background=PALETTE["surface"],
        foreground=PALETTE["text"],
        font=FONT_TITLE,
    )
    style.configure(
        "Body.TLabel",
        background=PALETTE["surface"],
        foreground=PALETTE["text"],
        font=FONT_BODY,
    )
    style.configure(
        "Body.Small.TLabel",
        background=PALETTE["surface"],
        foreground=PALETTE["text"],
        font=FONT_BODY_SMALL,
    )
    style.configure(
        "Muted.TLabel",
        background=PALETTE["surface"],
        foreground=PALETTE["muted"],
        font=FONT_MUTED,
    )
    style.configure(
        "Hero.TLabel",
        background=PALETTE["surface"],
        foreground=PALETTE["accent"],
        font=FONT_DISPLAY,
    )
    style.configure(
        "MetricValue.TLabel",
        background=PALETTE["surface"],
        foreground=PALETTE["accent"],
        font=("Helvetica Neue", 28, "bold"),
    )
    style.configure(
        "MetricLabel.TLabel",
        background=PALETTE["surface"],
        foreground=PALETTE["muted"],
        font=FONT_BODY_SMALL,
    )
    style.configure(
        "Section.TLabelframe",
        background=PALETTE["surface"],
        bordercolor=PALETTE["border"],
        relief="solid",
    )
    style.configure(
        "Section.TLabelframe.Label",
        background=PALETTE["surface"],
        foreground=PALETTE["text"],
        font=("Helvetica Neue", 12, "bold"),
    )
    style.configure(
        "Accent.TButton",
        background=PALETTE["accent"],
        foreground=PALETTE["surface"],
        borderwidth=0,
        focusthickness=0,
        padding=(14, 10),
        font=("Helvetica Neue", 11, "bold"),
    )
    style.map(
        "Accent.TButton",
        background=[("active", PALETTE["accent_hover"]), ("disabled", "#b5c8c2")],
        foreground=[("disabled", "#f5f3ee")],
    )
    style.configure(
        "Subtle.TButton",
        background=PALETTE["surface_alt"],
        foreground=PALETTE["text"],
        borderwidth=0,
        focusthickness=0,
        padding=(12, 8),
        font=("Helvetica Neue", 10, "bold"),
    )
    style.map("Subtle.TButton", background=[("active", "#e7dcc9")])

    style.configure(
        "Success.TButton",
        background=PALETTE["success"],
        foreground=PALETTE["surface"],
        borderwidth=0,
        focusthickness=0,
        padding=(10, 6),
    )
    style.map("Success.TButton", background=[("active", "#45a049")])

    style.configure(
        "App.TNotebook",
        background=PALETTE["bg"],
        borderwidth=0,
        tabmargins=(8, 8, 8, 0),
    )
    style.configure(
        "App.TNotebook.Tab",
        background=PALETTE["surface_alt"],
        foreground=PALETTE["muted"],
        borderwidth=0,
        padding=(18, 12),
        font=("Helvetica Neue", 11, "bold"),
    )
    style.map(
        "App.TNotebook.Tab",
        background=[
            ("selected", PALETTE["accent"]),
            ("active", PALETTE["accent_soft"]),
        ],
        foreground=[
            ("selected", PALETTE["surface"]),
            ("active", PALETTE["text"]),
        ],
        expand=[("selected", (0, 2, 0, 0))],
    )
    style.configure(
        "Treeview",
        rowheight=32,
        fieldbackground=PALETTE["surface"],
        background=PALETTE["surface"],
        foreground=PALETTE["text"],
        bordercolor=PALETTE["border"],
        font=FONT_BODY_SMALL,
    )
    style.configure(
        "Treeview.Heading",
        background=PALETTE["surface_alt"],
        foreground=PALETTE["text"],
        font=("Helvetica Neue", 11, "bold"),
    )
    style.map(
        "Treeview",
        background=[("selected", PALETTE["accent_soft"])],
        foreground=[("selected", PALETTE["text"])],
    )
    style.configure(
        "Horizontal.TProgressbar",
        troughcolor=PALETTE["surface_alt"],
        background=PALETTE["accent"],
        bordercolor=PALETTE["surface_alt"],
        lightcolor=PALETTE["accent"],
        darkcolor=PALETTE["accent"],
    )
