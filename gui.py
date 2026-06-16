#!/usr/bin/env python3
"""
STARLINCS — Signature-driven Transcriptome Alignment for Repurposing
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import tkinter.font as tkFont
import threading
import os
import sys
import time
import tempfile
import subprocess
import zipfile
import logging
import traceback
import webbrowser


logger = logging.getLogger("starlincs.pipeline")



# ── Font setup ───────────────────────────────────────────────────────────────
F_BODY = "Roboto"
F_MONO = "DejaVu Sans Mono"


def font(size=11, bold=False, italic=False, mono=False):
    family = F_MONO if mono else F_BODY
    weight = "bold" if bold else "normal"
    slant  = "italic" if italic else "roman"
    return (family, size, weight, slant)


# ── Colour palette ───────────────────────────────────────────────────────────
BG        = "#f5f6f8"
SURFACE   = "#ffffff"
SURFACE2  = "#f0f2f5"
BORDER    = "#dde1e7"
BORDER_FOCUS = "#4a90d9"
TEXT      = "#1a1d23"
TEXT2     = "#5a6070"
UP_BG     = "#fff0f0"
UP_HDR    = "#c0392b"
UP_BORDER = "#e74c3c"
DN_BG     = "#f0f4ff"
DN_HDR    = "#2563a8"
DN_BORDER = "#3b82f6"
ACCENT    = "#2563a8"
ACCENT_HV = "#1a4f8a"
SUCCESS   = "#16a34a"
WARN_CLR  = "#d97706"
ERR_CLR   = "#dc2626"
BTN_MIMIC = "#2563a8"
BTN_REV   = "#c0392b"
HDR_BG    = "#1a2744"
HDR_TEXT  = "#ffffff"

# ── Constants ─────────────────────────────────────────────────────────────────
ORGAN_MAP = {
    "Bone": "bone.csv",
    "Breast": "breast.csv",
    "Cervix": "cervix.csv",
    "Central Nervous System": "cns.csv",
    "Haematopoietic and Lymphoid Tissue": "haematopoietic_and_lymphoid_tissue.csv",
    "Kidney": "kidney.csv",
    "Large Intestine": "large_intestine.csv",
    "Liver": "liver.csv",
    "Lung": "lung.csv",
    "Pancreas": "pancreas.csv",
    "Placenta": "placenta.csv",
    "Prostate": "prostate.csv",
    "Skin": "skin.csv",
    "Soft Tissue": "soft_tissue.csv",
}

GENE_LIST_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "resources", "genes", "genes_12328.txt"
)
REQUIRED_PACKAGES = ["pandas", "gseapy", "numpy"]

# ── External links ────────────────────────────────────────────────────────────
LINKS = {
    "documentation": "https://github.com/epigen-bioinfolab/CHROMACS/blob/main/User_Manual.pdf",
    "lab_website":   "https://www.epigen-bioinfolab.com/",
    "contact":       "https://www.epigen-bioinfolab.com/contact",
}


# ── Helpers ───────────────────────────────────────────────────────────────────
def check_packages():
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try: __import__(pkg)
        except ImportError: missing.append(pkg)
    return missing

def load_reference_genes(path):
    if not os.path.isfile(path):
        return set()
    with open(path) as fh:
        return {line.strip().upper() for line in fh if line.strip()}

def filter_genes(raw_text, reference, max_genes):
    seen, result = set(), []
    for line in raw_text.splitlines():
        gene = line.strip().upper()
        if gene and gene in reference and gene not in seen:
            result.append(gene)
            seen.add(gene)
            if len(result) >= max_genes:
                break
    return result

def write_gmt(path, label, genes):
    with open(path, "w") as fh:
        fh.write(label + "\tNA\t" + "\t".join(genes) + "\n")

def fmt_target(raw):
    return _fmt_multiline(raw)


# ── Tooltip helper ────────────────────────────────────────────────────────────
class Tooltip:
    """
    Small popup that appears near a widget on hover.
    Usage: Tooltip(widget, "Your help text here")
    """
    PAD    = 8
    DELAY  = 400   # ms before showing

    def __init__(self, widget, text):
        self._widget  = widget
        self._text    = text
        self._tip_win = None
        self._after_id = None
        widget.bind("<Enter>",    self._schedule, add="+")
        widget.bind("<Leave>",    self._cancel,   add="+")
        widget.bind("<Button-1>", self._cancel,   add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self._after_id = self._widget.after(self.DELAY, self._show)

    def _cancel(self, _event=None):
        if self._after_id:
            self._widget.after_cancel(self._after_id)
            self._after_id = None
        self._hide()

    def _show(self):
        if self._tip_win:
            return
        w = self._widget
        try:
            x = w.winfo_rootx() + w.winfo_width() // 2
            y = w.winfo_rooty() + w.winfo_height() + 4
        except Exception:
            return

        self._tip_win = tw = tk.Toplevel(w)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.configure(bg=HDR_BG)

        outer = tk.Frame(tw, bg=HDR_BG, padx=1, pady=1)
        outer.pack()
        inner = tk.Frame(outer, bg="#1e2d4a", padx=self.PAD, pady=self.PAD)
        inner.pack()
        tk.Label(inner, text=self._text,
                 font=font(9), fg="#d0dff0", bg="#1e2d4a",
                 justify="left", wraplength=260).pack()

    def _hide(self):
        if self._tip_win:
            try:
                self._tip_win.destroy()
            except Exception:
                pass
            self._tip_win = None


# ── Help badge (the ? button) ─────────────────────────────────────────────────
class HelpBadge(tk.Label):
    """Small circular ? label that shows a Tooltip on hover."""
    def __init__(self, parent, tip_text, bg=SURFACE, **kw):
        super().__init__(parent,
                         text="?",
                         font=font(8, bold=True),
                         fg=ACCENT, bg=bg,
                         cursor="question_arrow",
                         **kw)
        Tooltip(self, tip_text)


# ── Reusable widgets ──────────────────────────────────────────────────────────
class FlatButton(tk.Button):
    def __init__(self, parent, text, bg, fg, command, width=None, pady=10, **kw):
        cfg = dict(text=text, bg=bg, fg=fg,
                   activebackground=fg, activeforeground=bg,
                   font=font(13, bold=True),
                   relief="flat", bd=0, cursor="hand2",
                   padx=24, pady=pady, command=command)
        if width: cfg["width"] = width
        cfg.update(kw)
        super().__init__(parent, **cfg)
        self._bg, self._fg = bg, fg
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _):
        try: self.configure(bg=self._darken(self._bg))
        except: pass
    def _on_leave(self, _):
        try: self.configure(bg=self._bg)
        except: pass
    @staticmethod
    def _darken(hex_color):
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r, g, b = max(0, r-25), max(0, g-25), max(0, b-25)
        return f"#{r:02x}{g:02x}{b:02x}"


class LinkLabel(tk.Label):
    """Clickable label that opens a URL or calls a command."""
    def __init__(self, parent, text, action, bg=BG, **kw):
        super().__init__(parent, text=text,
                         font=font(11), fg=ACCENT, bg=bg,
                         cursor="hand2", **kw)
        self._action = action
        self.bind("<Enter>",    lambda _: self.configure(fg=ACCENT_HV))
        self.bind("<Leave>",    lambda _: self.configure(fg=ACCENT))
        self.bind("<Button-1>", self._on_click)

    def _on_click(self, _=None):
        if callable(self._action):
            self._action()
        elif isinstance(self._action, str):
            webbrowser.open(self._action)


class SectionLabel(tk.Label):
    def __init__(self, parent, text, **kw):
        super().__init__(parent, text=text,
                         font=font(9, bold=True),
                         fg=TEXT2, bg=kw.pop("bg", BG), **kw)


class Card(tk.Frame):
    def __init__(self, parent, bg=SURFACE, border=BORDER, **kw):
        super().__init__(parent, bg=bg,
                         highlightbackground=border,
                         highlightthickness=1, **kw)


class LabeledSpinbox(tk.Frame):
    """Label + Entry pair with an optional ? help badge."""
    def __init__(self, parent, label, from_, to, default, width=7, tip=None, **kw):
        super().__init__(parent, bg=SURFACE, **kw)
        self._min     = from_
        self._max     = to
        self._default = default

        hdr_row = tk.Frame(self, bg=SURFACE)
        hdr_row.pack(anchor="w")
        SectionLabel(hdr_row, text=label, bg=SURFACE).pack(side="left")
        if tip:
            HelpBadge(hdr_row, tip, bg=SURFACE).pack(side="left", padx=(3, 0))

        self._var = tk.StringVar(value=str(default))
        entry = tk.Entry(self, textvariable=self._var,
                         width=width, font=font(11),
                         relief="flat", bg=SURFACE2, fg=TEXT,
                         insertbackground=TEXT,
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=BORDER_FOCUS)
        entry.pack(anchor="w", pady=(4, 0))

    @property
    def value(self):
        try:
            v = int(self._var.get())
            return max(self._min, min(self._max, v))
        except ValueError:
            return self._default


# ════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("STARLINCS")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(800, 720)
        self.geometry("1100x790")

        self.ref_genes = load_reference_genes(GENE_LIST_FILE)

        self._csv_cache   = {}
        self._meta_cache  = None

        self._frames = {}
        self._container = tk.Frame(self, bg=BG)
        self._container.pack(fill="both", expand=True)

        missing = check_packages()
        pages = (PageInstall, PageHome, PageAnalysis, PageResults) \
                if missing else (PageHome, PageAnalysis, PageResults)

        for F in pages:
            frame = F(self._container, self)
            self._frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self._container.rowconfigure(0, weight=1)
        self._container.columnconfigure(0, weight=1)

        self.show_frame("PageInstall" if missing else "PageHome",
                        missing=missing if missing else None)

    def show_frame(self, name, **kwargs):
        frame = self._frames[name]
        if hasattr(frame, "on_show"):
            frame.on_show(**kwargs)
        frame.tkraise()

    def get_reference_matrix(self, csv_path):
        if csv_path not in self._csv_cache:
            import pandas as pd
            df = pd.read_csv(csv_path, header=0, index_col=False)
            gene_col = df.columns[0]
            df = df.rename(columns={gene_col: "gene_symbol"})
            self._csv_cache[csv_path] = df
        return self._csv_cache[csv_path]

    def get_reference_genes_for(self, csv_path):
        # Create a cache dictionary if it doesn't exist yet
        if not hasattr(self, "_gene_set_cache"):
            self._gene_set_cache = {}
            
        if csv_path not in self._gene_set_cache:
            try:
                df = self.get_reference_matrix(csv_path)
                self._gene_set_cache[csv_path] = {
                    str(g).strip().upper() for g in df["gene_symbol"] if str(g).strip()
                }
            except Exception:
                return self.ref_genes
                
        return self._gene_set_cache[csv_path]

    def get_metadata(self):
        if self._meta_cache is None:
            import pandas as pd
            metadata_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "resources", "metadata.csv")
            if os.path.isfile(metadata_file):
                metadata = pd.read_csv(metadata_file)
                self._meta_cache = (
                    metadata[['cmap_name', 'target', 'moa', 'canonical_smiles',
                               'inchi_key', 'compound_aliases', 'groups']]
                    .drop_duplicates(subset='cmap_name')
                )
        return self._meta_cache


# ════════════════════════════════════════════════════════════════════════════
class PageInstall(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG)
        self.controller = controller

        hdr = tk.Frame(self, bg=HDR_BG, pady=28)
        hdr.pack(fill="x")
        tk.Label(hdr, text="STARLINCS", font=font(20, bold=True),
                 fg=HDR_TEXT, bg=HDR_BG).pack()
        tk.Label(hdr, text="First-time setup — installing required packages",
                 font=font(11), fg="#a0b4cc", bg=HDR_BG).pack(pady=4)

        body = tk.Frame(self, bg=BG, padx=50, pady=30)
        body.pack(fill="both", expand=True)

        warn_card = Card(body, bg="#fffbeb", border=WARN_CLR)
        warn_card.pack(fill="x", pady=(0, 20))
        inner = tk.Frame(warn_card, bg="#fffbeb", padx=20, pady=16)
        inner.pack(fill="x")
        tk.Label(inner, text="Missing Required Packages",
                 font=font(12, bold=True), fg=WARN_CLR, bg="#fffbeb").pack(anchor="w")
        tk.Label(inner,
                 text="The following packages need to be installed before the tool can run:",
                 font=font(10), fg=TEXT, bg="#fffbeb").pack(anchor="w", pady=(6, 4))
        self._pkg_frame = tk.Frame(inner, bg="#fffbeb")
        self._pkg_frame.pack(anchor="w", padx=10)
        tk.Label(inner,
                 text="Click Install below. Requires internet. This only happens once.",
                 font=font(9, italic=True), fg=TEXT2, bg="#fffbeb").pack(anchor="w", pady=(8, 0))

        tk.Label(body, text="Installation Output", font=font(10, bold=True),
                 fg=TEXT2, bg=BG, anchor="w").pack(fill="x", pady=(0, 4))
        self._log = scrolledtext.ScrolledText(body, bg="#1e1e1e", fg="#d4d4d4",
                                              font=font(10, mono=True),
                                              relief="flat", state="disabled", height=12)
        self._log.pack(fill="both", expand=True)

        btn_row = tk.Frame(body, bg=BG)
        btn_row.pack(pady=16)
        self._install_btn = FlatButton(btn_row, "Install Packages", ACCENT, "white",
                                       self._install)
        self._install_btn.pack(side="left", padx=8)
        FlatButton(btn_row, "Skip", SURFACE2, TEXT2, self._skip).pack(side="left", padx=8)

    def on_show(self, missing=None, **_):
        if missing:
            for w in self._pkg_frame.winfo_children(): w.destroy()
            for pkg in missing:
                tk.Label(self._pkg_frame, text=f"• {pkg}",
                         font=font(10, bold=True), fg=ERR_CLR,
                         bg="#fffbeb").pack(anchor="w")

    def _install(self):
        self._install_btn.configure(state="disabled", text="Installing…")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        for pkg in check_packages():
            self._log_append(f"Installing {pkg}…\n")
            try:
                r = subprocess.run([sys.executable, "-m", "pip", "install", pkg],
                                   capture_output=True, text=True)
                if r.returncode == 0:
                    self._log_append(f"  ✔ {pkg} installed\n\n")
                else:
                    self._log_append(f"  ✗ Error:\n{r.stderr}\n\n")
            except Exception as e:
                self._log_append(f"  ✗ {e}\n\n")

        still = check_packages()
        if still:
            self._log_append(f"Still missing: {', '.join(still)}\n"
                             f"Run manually:  pip install {' '.join(still)}\n")
            self.after(0, lambda: self._install_btn.configure(
                state="normal", text="Retry Install"))
        else:
            self._log_append("✔  All packages ready.\n")
            self.after(1500, lambda: self.controller.show_frame("PageHome"))

    def _skip(self): self.controller.show_frame("PageHome")

    def _log_append(self, msg):
        def _do():
            self._log.configure(state="normal")
            self._log.insert("end", msg)
            self._log.see("end")
            self._log.configure(state="disabled")
        self.after(0, _do)


# ════════════════════════════════════════════════════════════════════════════
class PageHome(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG)
        self.controller = controller
        self._custom_matrix_path = None

        # initialise count vars before any widget (including _gene_card) is built
        self._up_count_var = tk.StringVar(value="")
        self._dn_count_var = tk.StringVar(value="")

        # ── Top header bar ────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=HDR_BG, pady=6)
        hdr.pack(fill="x")

        _res = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")

        hdr.columnconfigure(0, weight=1)
        hdr.columnconfigure(1, weight=0)
        hdr.columnconfigure(2, weight=1)

        left_col = tk.Frame(hdr, bg=HDR_BG)
        left_col.grid(row=0, column=0, sticky="w", padx=(6, 0))
        _lab_logo_path = os.path.join(_res, "lab_logo.png")
        if os.path.isfile(_lab_logo_path):
            try:
                from PIL import Image, ImageTk
                _img = Image.open(_lab_logo_path)
                _img.thumbnail((80, 80), Image.LANCZOS)
                self._lab_logo_img = ImageTk.PhotoImage(_img)
                tk.Label(left_col, image=self._lab_logo_img, bg=HDR_BG).pack(anchor="w")
            except ImportError:
                try:
                    self._lab_logo_img = tk.PhotoImage(file=_lab_logo_path)
                    tk.Label(left_col, image=self._lab_logo_img, bg=HDR_BG).pack(anchor="w")
                except Exception:
                    pass
            except Exception:
                pass

        centre_col = tk.Frame(hdr, bg=HDR_BG)
        centre_col.grid(row=0, column=1)
        tk.Label(centre_col, text="STARLINCS",
                 font=font(18, bold=True), fg=HDR_TEXT, bg=HDR_BG).pack()
        tk.Label(centre_col, text="Epigenetics and Bioinformatics Research Laboratory",
                 font=font(11), fg="#a0b4cc", bg=HDR_BG).pack(pady=2)
        tk.Label(centre_col,
                 text="Department of Genetic Engineering and Biotechnology, University of Dhaka",
                 font=font(11), fg="#a0b4cc", bg=HDR_BG).pack(pady=2)

        right_col = tk.Frame(hdr, bg=HDR_BG)
        right_col.grid(row=0, column=2, sticky="e", padx=(0, 6))
        _icon_path = os.path.join(_res, "icon.png")
        if os.path.isfile(_icon_path):
            try:
                from PIL import Image, ImageTk
                _ico = Image.open(_icon_path)
                _ico.thumbnail((80, 80), Image.LANCZOS)
                self._icon_img = ImageTk.PhotoImage(_ico)
                tk.Label(right_col, image=self._icon_img, bg=HDR_BG).pack(anchor="e")
            except ImportError:
                try:
                    self._icon_img = tk.PhotoImage(file=_icon_path)
                    tk.Label(right_col, image=self._icon_img, bg=HDR_BG).pack(anchor="e")
                except Exception:
                    pass
            except Exception:
                pass

        # ── Main body ─────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=BG, padx=24, pady=16)
        body.pack(fill="both", expand=True)

        # ── Controls row ──────────────────────────────────────────────────────
        ctrl = Card(body)
        ctrl.pack(fill="x", pady=(0, 14))
        ctrl_inner = tk.Frame(ctrl, bg=SURFACE, padx=16, pady=14)
        ctrl_inner.pack(fill="x")

        # -- Organ picker --
        organ_col = tk.Frame(ctrl_inner, bg=SURFACE)
        organ_col.pack(side="left", padx=(0, 20))

        organ_hdr = tk.Frame(organ_col, bg=SURFACE)
        organ_hdr.pack(anchor="w")
        SectionLabel(organ_hdr, text="SELECT ORGAN", bg=SURFACE).pack(side="left")
        HelpBadge(organ_hdr,
                  "Choose the tissue/organ type that matches your experimental context.\n"
                  "This selects the pre-built drug-gene ranking matrix for that tissue.",
                  bg=SURFACE).pack(side="left", padx=(3, 0))

        self._organ_var = tk.StringVar(value="Lung")
        self._organ_cb = ttk.Combobox(organ_col, textvariable=self._organ_var,
                                      values=list(ORGAN_MAP.keys()),
                                      state="readonly", width=30, font=font(11))
        self._organ_cb.pack(anchor="w", pady=(4, 0))
        self._organ_cb.bind("<<ComboboxSelected>>", self._on_organ_change)

        # -- Custom matrix upload --
        matrix_col = tk.Frame(ctrl_inner, bg=SURFACE)
        matrix_col.pack(side="left", padx=(0, 20))

        matrix_hdr = tk.Frame(matrix_col, bg=SURFACE)
        matrix_hdr.pack(anchor="w")
        SectionLabel(matrix_hdr, text="CUSTOM REFERENCE (OPTIONAL)", bg=SURFACE).pack(side="left")
        HelpBadge(matrix_hdr,
                  "Upload your own drug-gene ranking CSV instead of using a preset organ.\n"
                  "Format: first column = gene symbols, remaining columns = one drug each, "
                  "values = ranking scores (higher = more upregulated in that drug's signature).",
                  bg=SURFACE).pack(side="left", padx=(3, 0))

        matrix_btn_row = tk.Frame(matrix_col, bg=SURFACE)
        matrix_btn_row.pack(anchor="w", pady=(4, 0))
        self._matrix_lbl = tk.Label(matrix_btn_row, text="Using preset organ",
                                    font=font(9, italic=True), fg=TEXT2, bg=SURFACE)
        self._matrix_lbl.pack(side="left")
        tk.Button(matrix_btn_row, text="Upload CSV",
                  font=font(9), fg=ACCENT, bg=SURFACE2,
                  relief="flat", cursor="hand2", padx=8, pady=3,
                  activeforeground="white", activebackground=ACCENT,
                  command=self._upload_matrix).pack(side="left", padx=(8, 4))
        tk.Button(matrix_btn_row, text="CLEAR",
                  font=font(9, bold=True), fg=ERR_CLR, bg=SURFACE2,
                  relief="flat", cursor="hand2", padx=5, pady=3,
                  activeforeground="white", activebackground=ERR_CLR,
                  command=self._clear_matrix).pack(side="left")

        # Divider
        tk.Frame(ctrl_inner, bg=BORDER, width=1).pack(side="left", fill="y", padx=16)

        # -- Min Gene spinbox --
        self._min_gene_sb = LabeledSpinbox(
            ctrl_inner, "MIN GENE", from_=1, to=200, default=20, width=8,
            tip="Minimum number of genes from your list that must appear in a drug's\n"
                "gene set for that drug to be scored. Sets below this size are skipped.\n"
                "Recommended: 15–25.")
        self._min_gene_sb.pack(side="left", padx=(0, 14))

        # -- Max Gene spinbox --
        self._max_gene_sb = LabeledSpinbox(
            ctrl_inner, "MAX GENE", from_=10, to=2000, default=500, width=8,
            tip="Maximum number of genes from your input list to use.\n"
                "If you provide more genes than this, only the first N are used.\n"
                "Recommended: 200–500 for balanced sensitivity and specificity.")
        self._max_gene_sb.pack(side="left", padx=(0, 14))

        # -- Seed spinbox --
        self._seed_sb = LabeledSpinbox(
            ctrl_inner, "SEED", from_=0, to=99999, default=1234, width=8,
            tip="Random seed for GSEA permutation testing.\n"
                "Set the same value to reproduce identical results across runs.\n"
                "Any integer works — 1234 is the default.")
        self._seed_sb.pack(side="left", padx=(0, 14))

        # -- Perm spinbox --
        self._perm_sb = LabeledSpinbox(
            ctrl_inner, "PERMUTATIONS", from_=10, to=99999, default=1000, width=10,
            tip="Number of permutations for GSEA null distribution estimation.\n"
                "Higher values give more accurate p-values but take longer.\n"
                "100 is fast for exploration; 1000 is standard for publication.")
        self._perm_sb.pack(side="left", padx=(0, 14))

        self._style_widgets()

        # ── Gene input boxes ──────────────────────────────────────────────────
        boxes_outer = tk.Frame(body, bg=BG)
        boxes_outer.pack(fill="both", expand=True)
        boxes_outer.columnconfigure(0, weight=1)
        boxes_outer.columnconfigure(1, weight=1)

        self._up_text   = self._gene_card(boxes_outer, "Upregulated Genes",
                                          UP_HDR, UP_BORDER, UP_BG, col=0)
        self._down_text = self._gene_card(boxes_outer, "Downregulated Genes",
                                          DN_HDR, DN_BORDER, DN_BG, col=1)

        footer = Card(body, bg=SURFACE2, border=BORDER)
        footer.pack(fill="x", pady=(10, 0))
        footer_inner = tk.Frame(footer, bg=SURFACE2, padx=14, pady=8)
        footer_inner.pack(fill="x")
        footer_inner.columnconfigure(0, weight=1)  # links expand

        # Left: quick links
        links_frame = tk.Frame(footer_inner, bg=SURFACE2)
        links_frame.grid(row=0, column=0, sticky="w")

        def _sep(parent):
            tk.Label(parent, text="·", font=font(9), fg=BORDER, bg=SURFACE2).pack(side="left", padx=4)

        LinkLabel(links_frame, "Load Example Dataset",
                  self._load_example, bg=SURFACE2).pack(side="left")
        _sep(links_frame)
        LinkLabel(links_frame, "Documentation",
                  LINKS["documentation"], bg=SURFACE2).pack(side="left")
        _sep(links_frame)
        LinkLabel(links_frame, "Visit Lab Website",
                  LINKS["lab_website"], bg=SURFACE2).pack(side="left")
        _sep(links_frame)
        LinkLabel(links_frame, "Contact",
                  LINKS["contact"], bg=SURFACE2).pack(side="left")

        # Right: reference status + action buttons stacked
        right_frame = tk.Frame(footer_inner, bg=SURFACE2)
        right_frame.grid(row=0, column=1, sticky="e")

        # Reference status (top-right, small)
        self._ref_status_lbl = tk.Label(right_frame, text="", font=font(8),
                                        bg=SURFACE2, anchor="e")
        self._ref_status_lbl.pack(anchor="e", pady=(0, 6))
        
        # AT THE VERY END OF PageHome.__init__ (after button creation), add:
        self._update_status()

        # Action buttons (bottom-right)
        btn_row = tk.Frame(right_frame, bg=SURFACE2)
        btn_row.pack(anchor="e")
        FlatButton(btn_row, "Mimic", BTN_MIMIC, "white",
                   lambda: self._run("mimic"), padx=20, pady=10).pack(side="left", padx=(0, 8))
        FlatButton(btn_row, "Reverse", BTN_REV, "white",
                   lambda: self._run("reverse"), padx=20, pady=10).pack(side="left")

    # ── Widget styling ────────────────────────────────────────────────────────
    def _style_widgets(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("TCombobox",
                    fieldbackground=SURFACE, background=SURFACE,
                    foreground=TEXT, selectbackground=SURFACE,
                    selectforeground=TEXT, bordercolor=BORDER,
                    arrowcolor=TEXT2, font=font(11))
        s.map("TCombobox", fieldbackground=[("readonly", SURFACE)],
              selectbackground=[("readonly", SURFACE)],
              selectforeground=[("readonly", TEXT)])

    def _on_organ_change(self, _=None):
        self._clear_matrix()

    def _upload_matrix(self):
        path = filedialog.askopenfilename(
            title="Select Drug-Gene Matrix CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if path:
            self._custom_matrix_path = path
            name = os.path.basename(path)
            display = name if len(name) <= 32 else "…" + name[-29:]
            self._matrix_lbl.configure(text=display, fg=SUCCESS, font=font(9))
            import pandas as pd
            df = pd.read_csv(path, usecols=[0])

            self.controller.ref_genes = {
                str(x).upper().strip()
                for x in df.iloc[:, 0]
                if pd.notna(x)
            }
            self._update_status()

    def _clear_matrix(self):
        self._custom_matrix_path = None
        self._matrix_lbl.configure(text="Using preset organ",
                                   fg=TEXT2, font=font(9, italic=True))
        self._update_status()

    def _load_example(self):
        """Load the bundled example up.txt and down.txt into the gene boxes."""
        example_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "resources", "example")
        up_path   = os.path.join(example_dir, "up.txt")
        down_path = os.path.join(example_dir, "down.txt")

        loaded = []
        if os.path.isfile(up_path):
            with open(up_path) as fh:
                content = fh.read()
            self._up_text.delete("1.0", "end")
            self._up_text.insert("1.0", content)
            loaded.append("upregulated")

        if os.path.isfile(down_path):
            with open(down_path) as fh:
                content = fh.read()
            self._down_text.delete("1.0", "end")
            self._down_text.insert("1.0", content)
            loaded.append("downregulated")

        if loaded:
            self._update_status()
        else:
            messagebox.showwarning(
                "Example Not Found",
                f"Example files not found in:\n{example_dir}\n\n"
                "Expected: up.txt and down.txt")

    def _gene_card(self, parent, title, hdr_color, border_color, bg_color, col):
        pad = (0, 8) if col == 0 else (8, 0)
        card = tk.Frame(parent, bg=bg_color,
                        highlightbackground=border_color,
                        highlightthickness=2)
        card.grid(row=0, column=col, padx=pad, pady=0, sticky="nsew")
        parent.rowconfigure(0, weight=1)

        hdr_bar = tk.Frame(card, bg=hdr_color, pady=9)
        hdr_bar.pack(fill="x")
        tk.Label(hdr_bar, text=title, font=font(11, bold=True),
                 fg="white", bg=hdr_color).pack(side="left", padx=14)

        # count label — shows "N valid / N entered", updated by _update_status()
        count_var = self._up_count_var if col == 0 else self._dn_count_var
        tk.Label(hdr_bar, textvariable=count_var,
                 font=font(9), fg="white", bg=hdr_color,
                 anchor="e").pack(side="left", padx=(0, 8))

        def do_upload(tw):
            path = filedialog.askopenfilename(
                title=f"Upload {title}",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
            if path:
                with open(path) as fh: content = fh.read()
                tw.delete("1.0", "end")
                tw.insert("1.0", content)
                self._update_status()

        txt = tk.Text(card, bg="white", fg=TEXT,
                      insertbackground=TEXT,
                      font=font(11),
                      relief="flat", wrap="none", undo=True,
                      selectbackground="#b3d1f0",
                      borderwidth=0, highlightthickness=0,
                      height=15)

        vsb = ttk.Scrollbar(card, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y", padx=(0, 4), pady=4)
        txt.pack(fill="both", expand=True, padx=8, pady=(6, 8))
        txt.bind("<KeyRelease>", lambda e: self._update_status())

        tk.Button(hdr_bar, text="Upload .txt",
                  font=font(9), fg=hdr_color, bg="white",
                  relief="flat", cursor="hand2", padx=10, pady=3,
                  activeforeground="white", activebackground=hdr_color,
                  command=lambda tw=txt: do_upload(tw)).pack(side="right", padx=10)

        return txt

    def _active_reference_genes(self):
        # 1. Use custom matrix if uploaded
        if self._custom_matrix_path:
            return self.controller.get_reference_genes_for(self._custom_matrix_path)
            
        # 2. Otherwise, dynamically load genes from the currently selected preset organ
        organ = self._organ_var.get()
        csv_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", ORGAN_MAP[organ])
        return self.controller.get_reference_genes_for(csv_path)

    def _update_status(self):
        ref   = self._active_reference_genes()
        max_g = int(self._max_gene_sb.value)

        # 1. Update the bottom-right reference status label
        if ref:
            self._ref_status_lbl.configure(
                text=f"✔  {len(ref):,} reference genes loaded", fg=SUCCESS)
        else:
            self._ref_status_lbl.configure(
                text="⚠  Reference gene list not found", fg=WARN_CLR)

        up_raw = self._up_text.get("1.0", "end")
        dn_raw = self._down_text.get("1.0", "end")

        if ref:
            up_filt = filter_genes(up_raw, ref, max_g)
            dn_filt = filter_genes(dn_raw, ref, max_g)
        else:
            up_filt = list(dict.fromkeys(
                g.strip().upper() for g in up_raw.splitlines() if g.strip()))[:max_g]
            dn_filt = list(dict.fromkeys(
                g.strip().upper() for g in dn_raw.splitlines() if g.strip()))[:max_g]

        up_n = sum(1 for l in up_raw.splitlines() if l.strip())
        dn_n = sum(1 for l in dn_raw.splitlines() if l.strip())

        self._up_count_var.set(f"{len(up_filt)} valid / {up_n} entered")
        self._dn_count_var.set(f"{len(dn_filt)} valid / {dn_n} entered")

    def _run(self, mode):
        ref   = self._active_reference_genes()
        max_g = int(self._max_gene_sb.value)
        min_g = int(self._min_gene_sb.value)
        seed  = int(self._seed_sb.value)
        perm  = int(self._perm_sb.value)

        up_raw = self._up_text.get("1.0", "end").strip()
        dn_raw = self._down_text.get("1.0", "end").strip()

        if ref:
            up_genes = filter_genes(up_raw, ref, max_g)
            dn_genes = filter_genes(dn_raw, ref, max_g)
        else:
            up_genes = list(dict.fromkeys(
                g.strip().upper() for g in up_raw.splitlines() if g.strip()))[:max_g]
            dn_genes = list(dict.fromkeys(
                g.strip().upper() for g in dn_raw.splitlines() if g.strip()))[:max_g]

        if not up_genes and not dn_genes:
            messagebox.showwarning("No Genes",
                "Please enter at least one gene symbol in either box.")
            return

        if self._custom_matrix_path:
            csv_path    = self._custom_matrix_path
            organ_label = os.path.basename(csv_path)
        else:
            organ    = self._organ_var.get()
            csv_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "data", ORGAN_MAP[organ])
            organ_label = organ

        if not os.path.isfile(csv_path):
            messagebox.showerror("Missing Data File",
                f"Drug ranking file not found:\n{csv_path}")
            return

        self.controller.show_frame("PageAnalysis",
            organ=organ_label, csv_path=csv_path,
            up_genes=up_genes, dn_genes=dn_genes,
            mode=mode, max_gene=max_g, min_gene=min_g, seed=seed, perm=perm)


# ════════════════════════════════════════════════════════════════════════════
class PageAnalysis(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG)
        self.controller = controller

        hdr = tk.Frame(self, bg=HDR_BG, pady=22)
        hdr.pack(fill="x")
        self._title_var = tk.StringVar(value="Running Analysis…")
        tk.Label(hdr, textvariable=self._title_var,
                 font=font(16, bold=True), fg=HDR_TEXT, bg=HDR_BG).pack()

        body = tk.Frame(self, bg=BG, padx=28, pady=18)
        body.pack(fill="both", expand=True)

        prog_card = Card(body)
        prog_card.pack(fill="x", pady=(0, 14))
        prog_inner = tk.Frame(prog_card, bg=SURFACE, padx=16, pady=14)
        prog_inner.pack(fill="x")

        self._prog_lbl = tk.StringVar(value="Initialising…")
        tk.Label(prog_inner, textvariable=self._prog_lbl,
                 font=font(11), fg=TEXT, bg=SURFACE).pack(anchor="w")
        self._prog_var = tk.DoubleVar(value=0)

        s = ttk.Style()
        s.configure("Blue.Horizontal.TProgressbar",
                    troughcolor=SURFACE2, background=ACCENT,
                    borderwidth=0, thickness=10)
        ttk.Progressbar(prog_inner, variable=self._prog_var,
                        maximum=100, mode="determinate",
                        style="Blue.Horizontal.TProgressbar").pack(
            fill="x", pady=(8, 0))

        tk.Label(body, text="Analysis Log",
                 font=font(10, bold=True), fg=TEXT2, bg=BG, anchor="w").pack(fill="x", pady=(0, 4))
        self._log = scrolledtext.ScrolledText(
            body, bg="#1e1e1e", fg="#d4d4d4",
            font=font(10, mono=True), relief="flat",
            state="disabled", height=20)
        self._log.pack(fill="both", expand=True)

        self._cancel_flag = threading.Event()
        FlatButton(self, "Cancel", "#e5e7eb", TEXT2, self._cancel,
                   pady=8).pack(pady=12)

    def on_show(self, organ, csv_path, up_genes, dn_genes, mode,
                max_gene=500, min_gene=20, seed=1234, perm=1000):
        self._cancel_flag.clear()
        self._title_var.set("Gene Set Enrichment Analysis")
        self._log_clear()
        self._prog_var.set(0)
        self._prog_lbl.set("Initialising…")
        self._last_result = None
        import gc; gc.collect()

        threading.Thread(target=self._worker,
                         args=(organ, csv_path, up_genes, dn_genes,
                               mode, max_gene, min_gene, seed, perm),
                         daemon=True).start()

    def _log_append(self, msg):
        def _do():
            self._log.configure(state="normal")
            self._log.insert("end", msg)
            self._log.see("end")
            self._log.configure(state="disabled")
        self.after(0, _do)

    def _log_clear(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    def _cancel(self):
        self._cancel_flag.set()
        self._log_append("Cancelled by user.\n")
        self.controller.show_frame("PageHome")

    def _worker(self, organ, csv_path, up_genes, dn_genes,
                mode, max_gene, min_gene, seed, perm):
        import gc

        tmpdir = None
        try:
            try:
                import pandas as pd
                import gseapy as gp
            except ImportError as e:
                self._log_append(f"Error: missing package — {e}\n"
                                 f"Run:  pip install {' '.join(REQUIRED_PACKAGES)}\n")
                self._fail()
                return

            try:
                meta_slim = self.controller.get_metadata()
            except Exception as e:
                self._log_append(f"Warning: could not load metadata — {e}\n")
                meta_slim = None

            tmpdir = tempfile.mkdtemp(prefix="starlincs_")
            up_gmt = os.path.join(tmpdir, "up_genes.gmt")
            dn_gmt = os.path.join(tmpdir, "dn_genes.gmt")
            tag = organ.lower().replace(" ", "_")
            write_gmt(up_gmt, f"{tag}_up", up_genes)
            write_gmt(dn_gmt, f"{tag}_dn", dn_genes)

            self._log_append(
                f"Organ / Reference : {organ}\n"
                f"Mode              : {mode.upper()}\n"
                f"Upregulated       : {len(up_genes)} genes\n"
                f"Downregulated     : {len(dn_genes)} genes\n"
                f"Min/Max gene      : {min_gene} / {max_gene}\n"
                f"Permutations      : {perm}   Seed: {seed}\n\n")

            try:
                drugs_ranked = self.controller.get_reference_matrix(csv_path)
            except Exception as e:
                self._log_append(f"Error reading CSV: {e}\n")
                self._fail()
                return

            drugs = [c for c in drugs_ranked.columns if c != "gene_symbol"]
            total, done = len(drugs) * 2, 0
            self._log_append(f"Drugs to process: {len(drugs)}\n\n")

            upreg, downreg = [], []

            self._log_append("Upregulated genes are now being mapped to reference\n")
            for drug in drugs:
                if self._cancel_flag.is_set():
                    return
                self._prog_lbl.set(drug)
                t0 = time.time()
                try:
                    pre = gp.prerank(
                        rnk=drugs_ranked[["gene_symbol", drug]],
                        gene_sets=up_gmt, outdir=None, format=None,
                        graph_num=0, permutation_num=perm,
                        weight=0, seed=seed, threads=1,
                        min_size=min_gene, max_size=max_gene)
                    row = pre.res2d[["NES", "Lead_genes"]].copy()
                    row["DRUG"] = drug
                    upreg.append(row)
                    del pre
                    self._log_append(f"  {drug:<34} {time.time()-t0:.1f}s\n")
                except Exception as e:
                    self._log_append(f"  {drug} — error: {e}\n")
                done += 1
                self._prog_var.set(done / total * 100)

            self._log_append("\nDownregulated genes are now being mapped to reference\n")
            for drug in drugs:
                if self._cancel_flag.is_set():
                    return
                self._prog_lbl.set(drug)
                t0 = time.time()
                try:
                    pre = gp.prerank(
                        rnk=drugs_ranked[["gene_symbol", drug]],
                        gene_sets=dn_gmt, outdir=None, format=None,
                        graph_num=0, permutation_num=perm,
                        weight=0, seed=seed, threads=1,
                        min_size=min_gene, max_size=max_gene)
                    row = pre.res2d[["NES", "Lead_genes"]].copy()
                    row["DRUG"] = drug
                    downreg.append(row)
                    del pre
                    self._log_append(f"  {drug:<34} {time.time()-t0:.1f}s\n")
                except Exception as e:
                    self._log_append(f"  {drug} — error: {e}\n")
                done += 1
                self._prog_var.set(done / total * 100)

            gc.collect()

            if not upreg or not downreg:
                self._log_append(
                    "\nError: no GSEA results were produced. "
                    "Check that gene symbols match the reference matrix "
                    "and that min/max gene settings are reasonable.\n")
                self._fail()
                return

            up_df = (pd.concat(upreg, ignore_index=True)
                       .rename(columns={"NES": "NES_up", "Lead_genes": "lead_genes_up"}))
            del upreg

            dn_df = (pd.concat(downreg, ignore_index=True)
                       .rename(columns={"NES": "NES_dn", "Lead_genes": "lead_genes_dn"}))
            del downreg

            merged = pd.merge(up_df, dn_df, on="DRUG")
            del up_df, dn_df

            merged["connectivity_score"] = merged["NES_dn"] - merged["NES_up"]

            if meta_slim is not None:
                merged = (merged
                          .merge(meta_slim, left_on="DRUG", right_on="cmap_name", how="left")
                          .drop(columns="cmap_name"))
            else:
                for col in ["target", "moa", "canonical_smiles",
                            "inchi_key", "compound_aliases", "groups"]:
                    merged[col] = ""

            merged = merged.rename(columns={"DRUG": "drug", "compound_aliases": "alias"})
            merged = (merged.sort_values("connectivity_score",
                                         ascending=(mode == "reverse"))
                            .reset_index(drop=True))

            self._prog_var.set(100)
            self._prog_lbl.set("Complete")
            self._log_append("\nAnalysis complete.\n")

            self.after(0, lambda: self.controller.show_frame(
                "PageResults",
                merged_df=merged,
                organ=organ,
                mode=mode,
                up_count=len(up_genes),
                dn_count=len(dn_genes)))

        except Exception:
            tb = traceback.format_exc()
            self._log_append(f"\nUnexpected error — analysis aborted:\n{tb}\n")
            self._fail()

        finally:
            if tmpdir:
                self._cleanup_tmp(tmpdir)

    def _fail(self):
        def _do():
            self._prog_lbl.set("Error — see log below")
            self._prog_var.set(0)
        self.after(0, _do)

    @staticmethod
    def _cleanup_tmp(tmpdir):
        import shutil
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════════════════
def _fmt_multiline(raw):
    if not raw or str(raw).strip() in ("", "nan", "None"):
        return ""
    raw = str(raw)
    parts = [p.strip() for p in raw.replace("|", ",").split(",") if p.strip()]
    return "\n".join(parts)


class _ScrollableTable(tk.Frame):
    COLS = [
        ("Rank",                 55,  "center", None,                 False),
        ("Drug",                110,  "w",      "drug",               False),
        ("Target",               80,  "w",      "target",             True),
        ("Mode of Action",      210,  "w",      "moa",                True),
        ("Groups",              130,  "w",      "groups",             True),
        ("NES Up",               88,  "e",      "NES_up",             False),
        ("NES Dn",               88,  "e",      "NES_dn",             False),
        ("Connectivity Score",  148,  "e",      "connectivity_score", False),
        ("Alias",               110,  "w",      "alias",              False),
        ("Canonical SMILES",    300,  "w",      "canonical_smiles",   False),
        ("InChI Key",           220,  "w",      "inchi_key",          False),
        ("Leading Genes",       120,  "center", "_leading",           False),
    ]

    ROW_PAD_Y  = 6
    ROW_PAD_X  = 6
    HDR_HEIGHT = 32

    def __init__(self, parent, on_export_genes, **kw):
        super().__init__(parent, bg=BG, **kw)
        self._on_export_genes  = on_export_genes
        self._row_frames       = []
        self._df               = None
        self._selected         = None
        self._updating_scroll  = False
        self._populate_token   = 0

        self._total_width = sum(c[1] for c in self.COLS)

        # precompute column x offsets
        self._col_x = []
        x = 0
        for (_, wd, _, _, _) in self.COLS:
            self._col_x.append(x)
            x += wd

        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        self._hdr_canvas = tk.Canvas(outer, bg=SURFACE2,
                                     height=self.HDR_HEIGHT,
                                     highlightthickness=0)
        self._hdr_canvas.grid(row=0, column=0, sticky="ew")

        self._canvas = tk.Canvas(outer, bg=SURFACE, highlightthickness=0)
        self._canvas.grid(row=1, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(outer, orient="vertical",   command=self._canvas.yview)
        hsb = ttk.Scrollbar(outer, orient="horizontal", command=self._hscroll)
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew", columnspan=2)

        self._canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._inner = tk.Frame(self._canvas, bg=SURFACE)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        for w in (self._canvas, self._inner):
            w.bind("<MouseWheel>", self._on_mousewheel)
            w.bind("<Button-4>",   self._on_mousewheel)
            w.bind("<Button-5>",   self._on_mousewheel)

        self._draw_header()

    def _hscroll(self, *args):
        self._canvas.xview(*args)
        self._hdr_canvas.xview(*args)

    def _on_mousewheel(self, event):
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll( 1, "units")
        else:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _fit_row(self, row_frame, cells):
        if not row_frame.winfo_exists():
            return
        max_h = 30
        for cell in cells:
            if not cell.winfo_exists():
                continue
            text = cell.cget("text")
            if not text:
                lines = 1
            else:
                wraplen = cell.cget("wraplength")
                if wraplen and wraplen > 0:
                    chars_per_line = max(1, int(wraplen / 6.5))
                    lines = 0
                    for segment in text.split("\n"):
                        seg_lines = max(1, -(-len(segment) // chars_per_line))
                        lines += seg_lines
                else:
                    lines = text.count("\n") + 1
            estimated = lines * 18 + self.ROW_PAD_Y * 2
            if estimated > max_h:
                max_h = estimated
        row_frame.configure(height=max_h)
        for c in cells:
            if c.winfo_exists():
                c.place_configure(height=max_h)

    def _on_inner_configure(self, _event=None):
        self._canvas.after_idle(self._update_scrollregion)

    def _update_scrollregion(self):
        if self._updating_scroll or not self._canvas.winfo_exists():
            return
        self._updating_scroll = True
        try:
            bbox = self._canvas.bbox("all")
            if bbox:
                self._canvas.configure(scrollregion=bbox)
        finally:
            self._updating_scroll = False

    def _on_canvas_configure(self, event):
        w = max(event.width, self._total_width)
        self._canvas.itemconfigure(self._canvas_window, width=w)

    def _draw_header(self):
        self._hdr_canvas.delete("all")
        self._hdr_canvas.configure(
            width=self._total_width,
            scrollregion=(0, 0, self._total_width, self.HDR_HEIGHT),
            xscrollcommand=lambda *a: None)
        x = 0
        for (hd, wd, anc, key, _ml) in self.COLS:
            self._hdr_canvas.create_rectangle(
                x, 0, x + wd, self.HDR_HEIGHT,
                fill=SURFACE2, outline=BORDER, width=1)
            if anc == "e":
                tx, tk_anchor = x + wd - self.ROW_PAD_X, "e"
            elif anc == "w":
                tx, tk_anchor = x + self.ROW_PAD_X, "w"
            else:
                tx, tk_anchor = x + wd // 2, "center"
            self._hdr_canvas.create_text(tx, self.HDR_HEIGHT // 2,
                                         text=hd, fill=TEXT,
                                         font=font(10, bold=True),
                                         anchor=tk_anchor)
            x += wd

    def clear(self):
        self._populate_token += 1
        for w in self._inner.winfo_children():
            w.destroy()
        self._row_frames.clear()
        self._selected = None
        self._inner.configure(width=self._total_width, height=0)
        self._canvas.configure(scrollregion=(0, 0, self._total_width, 0))
        self._canvas.yview_moveto(0)
        self._hdr_canvas.xview_moveto(0)

    def populate(self, df, on_done=None, chunk_size=15):
        self._populate_token += 1
        token = self._populate_token

        self._df = df
        for w in self._inner.winfo_children():
            w.destroy()
        self._row_frames.clear()
        self._inner.configure(width=self._total_width, height=0)
        self._canvas.configure(scrollregion=(0, 0, self._total_width, 0))
        self._canvas.yview_moveto(0)

        rows  = list(df.iterrows())
        total = len(rows)

        def build_chunk(start_idx):
            if token != self._populate_token:
                return
            if not self._inner.winfo_exists():
                return
            end_idx = min(start_idx + chunk_size, total)
            for rank_idx in range(start_idx, end_idx):
                _, r = rows[rank_idx]
                self._build_row(rank_idx, r)
            # update scrollregion after each chunk so rows appear progressively
            self._inner.update_idletasks()
            bbox = self._canvas.bbox("all")
            if bbox:
                self._canvas.configure(scrollregion=bbox)
            if end_idx < total:
                self.after(1, lambda: build_chunk(end_idx))
            else:
                self._inner.configure(width=self._total_width)
                self._inner.after_idle(self._on_inner_configure)
                if on_done:
                    on_done()

        if total:
            build_chunk(0)
        else:
            self._inner.configure(width=self._total_width)
            self._inner.after_idle(self._on_inner_configure)
            if on_done:
                on_done()

    def _build_row(self, rank_idx, r):
        score     = r.get("connectivity_score", 0)
        score_clr = "#16a34a" if score >= 0 else "#dc2626"
        row_bg    = SURFACE if rank_idx % 2 == 0 else SURFACE2

        row_frame = tk.Frame(self._inner, bg=row_bg,
                             highlightbackground=BORDER, highlightthickness=0)
        row_frame.pack(fill="x", side="top")

        cells = []
        for col_idx, (hd, wd, anc, key, is_ml) in enumerate(self.COLS):
            if hd == "Rank":
                val = str(rank_idx + 1); clr = TEXT2
            elif hd == "NES Up":
                val = f"{r.get('NES_up', 0):.4f}"; clr = TEXT
            elif hd == "NES Dn":
                val = f"{r.get('NES_dn', 0):.4f}"; clr = TEXT
            elif hd == "Connectivity Score":
                val = f"{score:.4f}"; clr = score_clr
            elif hd == "Leading Genes":
                val = "Export"; clr = ACCENT
            elif key:
                raw = r.get(key, "") or ""
                val = _fmt_multiline(str(raw)) if is_ml else str(raw)
                clr = TEXT
            else:
                val = ""; clr = TEXT

            if anc == "center":
                justify, tk_anchor = "center", "n"
            elif anc == "e":
                justify, tk_anchor = "right",  "ne"
            else:
                justify, tk_anchor = "left",   "nw"

            cell = tk.Label(row_frame, text=val,
                            font=font(10), fg=clr, bg=row_bg,
                            width=0,
                            wraplength=wd - self.ROW_PAD_X * 2 if is_ml else 0,
                            justify=justify, anchor=tk_anchor,
                            padx=self.ROW_PAD_X, pady=self.ROW_PAD_Y)
            cell.place(x=self._col_x[col_idx], y=0, width=wd)
            cells.append(cell)

            if hd == "Leading Genes":
                cell.configure(cursor="hand2")
                cell.bind("<Button-1>",
                          lambda e, idx=rank_idx: self._on_export_genes(self._df.iloc[idx]))

        # store cell refs on frame for fast recolor
        row_frame._cells = cells

        def _enter(e, f=row_frame):
            f.configure(bg="#eef4ff")
            for c in f._cells: c.configure(bg="#eef4ff")
        def _leave(e, f=row_frame, b=row_bg):
            f.configure(bg=b)
            for c in f._cells: c.configure(bg=b)
        def _click(e, f=row_frame, b=row_bg, i=rank_idx):
            self._select_row(f, b, i)

        row_frame.bind("<Enter>",    _enter)
        row_frame.bind("<Leave>",    _leave)
        row_frame.bind("<Button-1>", _click)
        for c in cells:
            c.bind("<Enter>",    _enter)
            c.bind("<Leave>",    _leave)
            c.bind("<Button-1>", _click)

        self._fit_row(row_frame, cells)
        self._row_frames.append((row_frame, rank_idx))

    @staticmethod
    def _recolor_children(frame, color):
        cells = getattr(frame, "_cells", None)
        if cells is not None:
            for c in cells:
                try: c.configure(bg=color)
                except Exception: pass
        else:
            for w in frame.winfo_children():
                try: w.configure(bg=color)
                except Exception: pass

    def _select_row(self, row_frame, base_bg, df_idx):
        if self._selected and self._selected[0].winfo_exists():
            prev_frame, prev_bg = self._selected
            prev_frame.configure(bg=prev_bg)
            self._recolor_children(prev_frame, prev_bg)
        sel_color = "#dbeafe"
        row_frame.configure(bg=sel_color)
        self._recolor_children(row_frame, sel_color)
        self._selected = (row_frame, base_bg)


# ════════════════════════════════════════════════════════════════════════════
class PageResults(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG)
        self.controller = controller
        self._df        = None

        hdr = tk.Frame(self, bg=HDR_BG, pady=18)
        hdr.pack(fill="x")
        hdr_inner = tk.Frame(hdr, bg=HDR_BG)
        hdr_inner.pack(fill="x", padx=20)

        self._title_var = tk.StringVar(value="Results")
        tk.Label(hdr_inner, textvariable=self._title_var,
                 font=font(16, bold=True), fg=HDR_TEXT, bg=HDR_BG).pack(side="left")

        btn_hdr = tk.Frame(hdr_inner, bg=HDR_BG)
        btn_hdr.pack(side="right")

        tk.Button(btn_hdr, text="← New Analysis",
                  font=font(10), fg="white", bg=HDR_BG,
                  relief="flat", cursor="hand2", padx=14, pady=6,
                  activeforeground="white", activebackground=HDR_BG,
                  command=lambda: controller.show_frame("PageHome")).pack(side="left", padx=6)

        tk.Button(btn_hdr, text="Export CSV",
                  font=font(10, bold=True), fg="white", bg=HDR_BG,
                  relief="flat", cursor="hand2", padx=14, pady=6,
                  activeforeground="black", activebackground="white",
                  command=self._export_csv).pack(side="left", padx=6)

        self._summary_var = tk.StringVar()
        summary = tk.Frame(self, bg=SURFACE2,
                           highlightbackground=BORDER, highlightthickness=1)
        summary.pack(fill="x")
        tk.Label(summary, textvariable=self._summary_var,
                 font=font(10), fg=TEXT2, bg=SURFACE2,
                 anchor="w", padx=20, pady=8).pack(fill="x")

        tbl_outer = tk.Frame(self, bg=BG, padx=16, pady=10)
        tbl_outer.pack(fill="both", expand=True)
        tbl_outer.rowconfigure(0, weight=1)
        tbl_outer.columnconfigure(0, weight=1)

        self._table = _ScrollableTable(tbl_outer,
                                       on_export_genes=self._export_leading_genes_row)
        self._table.grid(row=0, column=0, sticky="nsew")

        self._loading = tk.Frame(tbl_outer, bg=SURFACE,
                                 highlightbackground=BORDER, highlightthickness=1)
        loading_inner = tk.Frame(self._loading, bg=SURFACE)
        loading_inner.pack(padx=40, pady=24)
        tk.Label(loading_inner, text="Loading results…",
                 font=font(13, bold=True), fg=TEXT, bg=SURFACE).pack(pady=(0, 6))
        tk.Label(loading_inner, text="Building results table — please wait",
                 font=font(10), fg=TEXT2, bg=SURFACE).pack()

    def on_show(self, merged_df, organ, mode, up_count, dn_count):
        self._df = None
        self._table.clear()
        import gc; gc.collect()

        self._df = merged_df.reset_index(drop=True).head(100)
        mode_str = "Mimic" if mode == "mimic" else "Reverse"
        self._title_var.set("Results — Top 100 Candidates")
        self._summary_var.set(
            f"Organ/Reference: {organ}     Mode: {mode_str}     "
            f"Upregulated genes: {up_count}     Downregulated genes: {dn_count}     "
            f"Drugs ranked: {len(merged_df)}"
        )
        self._loading.place(relx=0.5, rely=0.5, anchor="center")
        self._loading.lift()
        self.update_idletasks()
        self._table.populate(self._df, on_done=self._loading.place_forget)

    def _export_leading_genes_row(self, row):
        drug_name = str(row.get("drug", "drug")).replace(" ", "_").replace("/", "-")
        path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            initialfile=f"{drug_name}_leading_genes.zip",
            filetypes=[("ZIP archive", "*.zip")],
            title="Save Leading Genes")
        if not path:
            return
        up_genes = str(row.get("lead_genes_up", "")).replace(";", "\n")
        dn_genes = str(row.get("lead_genes_dn", "")).replace(";", "\n")
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{drug_name}_leading_genes_up.txt", up_genes)
            zf.writestr(f"{drug_name}_leading_genes_dn.txt", dn_genes)
        messagebox.showinfo("Saved", f"Leading genes exported to:\n{path}")

    def _export_csv(self):
        if self._df is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("TSV files", "*.tsv")],
            title="Export Results")
        if not path:
            return
        sep = "\t" if path.endswith(".tsv") else ","
        export_cols = ["drug", "target", "moa", "groups",
                       "NES_up", "NES_dn", "connectivity_score",
                       "canonical_smiles", "inchi_key", "alias"]
        out = self._df[[c for c in export_cols if c in self._df.columns]]
        out.to_csv(path, index=False, sep=sep)
        messagebox.showinfo("Saved", f"Results exported to:\n{path}")


# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()
