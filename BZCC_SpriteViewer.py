
#!/usr/bin/env python3
"""
BZ2 Sprite Viewer
=================
Compact sprite table viewer/editor for Battlezone-style sprite.txt tables.

Features:
- Compact 2-column Properties panel
- Live adjustments preview
- Save Raw Crop (no adjustments)
- Export with Adjustments
- Save Modified Table Copy
- Batch export visible sprites or current file group
- Windows clipboard copy with win32clipboard, fallback temp-file path
- Zoom % in toolbar
- Modified sprites highlighted in tree
- Size info in Properties
- Guarded property updates to avoid false modification records
"""

from __future__ import annotations

import io
import os
import re
import sys
import json
import shutil
import platform
import subprocess
import tempfile
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk, filedialog, colorchooser, messagebox
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageTk, ImageEnhance, ImageOps

# ----------------------------------------------------------------------
# Configuration & paths
# ----------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = SCRIPT_DIR / "sprite_viewer_config.json"

if getattr(sys, "frozen", False):
    TEXCONV_PATH = Path(sys._MEIPASS) / "texconv.exe"  # type: ignore[attr-defined]
else:
    TEXCONV_PATH = SCRIPT_DIR / "texconv.exe"

CACHE_DIR = Path(tempfile.gettempdir()) / "bz2_sprite_cache"

SPRITE_LINE_RE = re.compile(
    r'^(?P<indent>\s*)"(?P<name>[^"]+)"\s+'
    r'(?P<file>\S+)\s+'
    r'(?P<u>\d+)\s+(?P<v>\d+)\s+(?P<w>\d+)\s+(?P<h>\d+)\s+'
    r'(?P<tw>\d+)\s+(?P<th>\d+)\s+(?P<flags>\S+)'
)


def load_config() -> dict:
    if CONFIG_FILE.is_file():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_config(config: dict) -> None:
    try:
        CONFIG_FILE.write_text(
            json.dumps(config, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def parse_sprite_table(filepath: str) -> List[dict]:
    entries: List[dict] = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for idx, raw_line in enumerate(f):
            line = raw_line.rstrip("\n")
            m = SPRITE_LINE_RE.match(line)
            if not m:
                continue
            entries.append(
                {
                    "line_index": idx,
                    "raw_line": raw_line,
                    "name": m.group("name"),
                    "file": m.group("file"),
                    "u": int(m.group("u")),
                    "v": int(m.group("v")),
                    "w": int(m.group("w")),
                    "h": int(m.group("h")),
                    "tw": int(m.group("tw")),
                    "th": int(m.group("th")),
                    "flags": m.group("flags"),
                }
            )
    return entries


def find_image_file(base_dir: str, filename_no_ext: str) -> Optional[str]:
    base = filename_no_ext.lower()
    valid_exts = {".png", ".dds", ".tga", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff"}
    for root, _, files in os.walk(base_dir):
        for f in files:
            stem, ext = os.path.splitext(f)
            if stem.lower() == base and ext.lower() in valid_exts:
                return os.path.join(root, f)
    return None


def texconv_convert(src_path: str, dst_dir: str) -> Optional[str]:
    if not Path(TEXCONV_PATH).is_file():
        return None
    os.makedirs(dst_dir, exist_ok=True)
    try:
        subprocess.run(
            [str(TEXCONV_PATH), "-ft", "png", "-o", dst_dir, "-y", src_path],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"texconv failed for {src_path}: {e.stderr}")
        return None
    base = os.path.splitext(os.path.basename(src_path))[0]
    png_path = os.path.join(dst_dir, base + ".png")
    return png_path if os.path.isfile(png_path) else None


def apply_dark_theme(root: tk.Tk) -> str:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    bg_dark = "#2b2b2b"
    bg_mid = "#3c3c3c"
    fg = "#e0e0e0"
    entry_bg = "#3a3a3a"
    tree_bg = "#2a2a2a"
    tree_sel = "#29465f"
    btn_bg = "#474747"
    btn_act = "#5a5a5a"

    default_font = ("Segoe UI", 9) if platform.system() == "Windows" else ("Helvetica", 10)
    root.option_add("*Font", default_font)

    style.configure("TFrame", background=bg_dark)
    style.configure("TLabel", background=bg_dark, foreground=fg)
    style.configure("TLabelframe", background=bg_dark, foreground=fg)
    style.configure("TLabelframe.Label", background=bg_dark, foreground=fg)
    style.configure("TNotebook", background=bg_dark, borderwidth=0)
    style.configure("TNotebook.Tab", background=bg_mid, foreground=fg, padding=(8, 3))
    style.map("TNotebook.Tab", background=[("selected", bg_dark)], foreground=[("selected", "#ffffff")])

    style.configure("TButton", background=btn_bg, foreground=fg, borderwidth=0, padding=(5, 2))
    style.map("TButton", background=[("active", btn_act), ("pressed", tree_sel)], foreground=[("active", fg)])

    style.configure("Accent.TButton", background="#2a5c8c", foreground=fg, borderwidth=0, padding=(5, 2))
    style.map("Accent.TButton", background=[("active", "#3173b0"), ("pressed", tree_sel)], foreground=[("active", fg)])

    style.configure("TEntry", fieldbackground=entry_bg, foreground="#ffffff", insertcolor="#ffffff", padding=2)
    style.configure("TSpinbox", fieldbackground=entry_bg, foreground="#ffffff", insertcolor="#ffffff", padding=2)
    style.map("TSpinbox", fieldbackground=[("readonly", entry_bg)], foreground=[("readonly", "#ffffff")])

    style.configure("TCheckbutton", background=bg_dark, foreground=fg)
    style.map("TCheckbutton", background=[("active", bg_dark)], foreground=[("active", fg)])

    style.configure("Treeview", background=tree_bg, foreground="#dcdcdc", fieldbackground=tree_bg, rowheight=19)
    style.map("Treeview", background=[("selected", tree_sel)], foreground=[("selected", "#ffffff")])
    style.configure("Treeview.Heading", background=btn_bg, foreground=fg, relief="flat", padding=3)

    style.configure("Vertical.TScrollbar", background=btn_bg, troughcolor=bg_dark, arrowcolor=fg)
    style.configure("Horizontal.TScrollbar", background=btn_bg, troughcolor=bg_dark, arrowcolor=fg)
    style.configure("TPanedwindow", background=bg_dark, sashwidth=4, sashrelief="flat")
    style.configure("Toolbar.TButton", padding=(6, 2))
    return bg_dark


class SpriteViewer:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("BZ2 Sprite Viewer")
        self.root.geometry("1280x740")
        self.root.minsize(900, 500)

        self.bg_color = apply_dark_theme(root)

        self.config = load_config()
        self.resources_path = self.config.get("resources_path")
        self.zoom_factor = float(self.config.get("zoom_factor", 1.0))
        self.zoom_mode = self.config.get("zoom_mode", "fit")

        self.antialias = tk.BooleanVar(value=bool(self.config.get("antialias", False)))
        self.grid_alpha = tk.BooleanVar(value=bool(self.config.get("grid_alpha", True)))
        self.solid_color = self.config.get("solid_color", "#808080")
        self.filter_text = tk.StringVar(value=self.config.get("filter_text", ""))

        self.brightness_var = tk.DoubleVar(value=float(self.config.get("brightness", 1.0)))
        self.contrast_var = tk.DoubleVar(value=float(self.config.get("contrast", 1.0)))
        self.saturation_var = tk.DoubleVar(value=float(self.config.get("saturation", 1.0)))
        self.gamma_var = tk.DoubleVar(value=float(self.config.get("gamma", 1.0)))
        self.hue_var = tk.DoubleVar(value=float(self.config.get("hue", 0.0)))
        self.invert_var = tk.BooleanVar(value=bool(self.config.get("invert", False)))

        self.sort_key = tk.StringVar(value=self.config.get("sort_key", "Name"))
        self.sort_desc = tk.BooleanVar(value=bool(self.config.get("sort_desc", False)))

        self.sprite_entries: List[dict] = []
        self.file_groups: Dict[str, List[dict]] = {}
        self.table_lines: List[str] = []
        self.image_cache: Dict[str, Optional[Image.Image]] = {}
        self.file_paths: Dict[str, Optional[str]] = {}
        self.modified_entries: Dict[Tuple[str, str], dict] = {}

        self.current_key: Optional[Tuple[str, str]] = None
        self.current_sprite: Optional[dict] = None
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._tk_image = None
        self._updating_props = False
        self._edit_after_id: Optional[str] = None
        self._temp_files: List[str] = []

        if "window_geometry" in self.config:
            try:
                self.root.geometry(self.config["window_geometry"])
            except Exception:
                pass

        self.sprite_table_path: Optional[str] = None
        if self.resources_path and os.path.isdir(self.resources_path):
            self.sprite_table_path = self.locate_sprite_table(self.resources_path)
            if not self.sprite_table_path:
                messagebox.showwarning("Warning", "Saved resource folder has no sprite.txt. Please select a new one.")
                self.ask_resource_folder()
        else:
            self.ask_resource_folder()

        if not self.resources_path or not self.sprite_table_path:
            self.root.destroy()
            return

        os.makedirs(CACHE_DIR, exist_ok=True)
        self.create_widgets()
        self.load_sprite_table()
        self.setup_shortcuts()

        self.filter_text.trace_add("write", lambda *_: self.rebuild_tree())
        self.sort_key.trace_add("write", lambda *_: self.rebuild_tree())
        self.sort_desc.trace_add("write", lambda *_: self.rebuild_tree())

        for var in [
            self.brightness_var,
            self.contrast_var,
            self.saturation_var,
            self.gamma_var,
            self.hue_var,
            self.invert_var,
        ]:
            var.trace_add("write", lambda *_: self.update_display())

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        if not self.grid_alpha.get():
            self.canvas.configure(bg=self.solid_color)

    # ------------------------------------------------------------------
    def on_closing(self) -> None:
        cfg = {
            "resources_path": self.resources_path,
            "window_geometry": self.root.winfo_geometry(),
            "zoom_factor": self.zoom_factor,
            "zoom_mode": self.zoom_mode,
            "antialias": self.antialias.get(),
            "grid_alpha": self.grid_alpha.get(),
            "solid_color": self.solid_color,
            "brightness": self.brightness_var.get(),
            "contrast": self.contrast_var.get(),
            "saturation": self.saturation_var.get(),
            "gamma": self.gamma_var.get(),
            "hue": self.hue_var.get(),
            "invert": self.invert_var.get(),
            "filter_text": self.filter_text.get(),
            "sort_key": self.sort_key.get(),
            "sort_desc": self.sort_desc.get(),
        }
        save_config(cfg)
        for p in self._temp_files:
            try:
                if os.path.isfile(p):
                    os.unlink(p)
            except Exception:
                pass
        self.root.destroy()

    def setup_shortcuts(self) -> None:
        self.root.bind("<Control-f>", lambda e: self.filter_entry.focus_set())
        self.root.bind("<Control-o>", lambda e: self.open_image_file())
        self.root.bind("<Control-Shift-O>", lambda e: self.open_file_location())
        self.root.bind("<Control-0>", lambda e: self.set_zoom_100())
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-e>", lambda e: self.export_sprite())
        self.root.bind("<Control-s>", lambda e: self.save_table_copy())
        self.root.bind("<Control-b>", lambda e: self.batch_export())
        self.root.bind("<F5>", lambda e: self.refresh())
        self.root.bind("<Control-Shift-F>", lambda e: self.change_resource_folder())

    # ------------------------------------------------------------------
    def ask_resource_folder(self) -> None:
        self.resources_path = filedialog.askdirectory(title="Select resource folder (e.g., BZ2R\\bz2r_res)")
        if not self.resources_path:
            return
        self.sprite_table_path = self.locate_sprite_table(self.resources_path)
        if not self.sprite_table_path:
            messagebox.showerror(
                "Error",
                "Could not find sprite.txt inside the selected folder.\n"
                "Ensure it contains interface/sprite.txt or similar.",
            )
            self.resources_path = None
        else:
            save_config({"resources_path": self.resources_path})

    def locate_sprite_table(self, base_dir: str) -> Optional[str]:
        candidate = os.path.join(base_dir, "interface", "sprite.txt")
        if os.path.isfile(candidate):
            return candidate
        for root, _, files in os.walk(base_dir):
            for f in files:
                if f.lower() == "sprite.txt":
                    return os.path.join(root, f)
        return None

    def refresh(self) -> None:
        if not self.sprite_table_path or not os.path.isfile(self.sprite_table_path):
            messagebox.showerror("Error", "Sprite table file not found.")
            return
        self.image_cache.clear()
        self.file_paths.clear()
        self.modified_entries.clear()
        self.current_key = None
        self.current_sprite = None
        self.load_sprite_table()
        self.clear_properties()
        self.update_display()

    # ------------------------------------------------------------------
    # UI CREATION
    # ------------------------------------------------------------------
    def create_widgets(self) -> None:
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Resources Folder...", command=self.change_resource_folder, accelerator="Ctrl+Shift+F")
        file_menu.add_command(label="Refresh Tree", command=self.refresh, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Export Sprite (with adjustments)...", command=self.export_sprite, accelerator="Ctrl+E")
        file_menu.add_command(label="Save Raw Crop...", command=self.save_raw_crop)
        file_menu.add_command(label="Save Modified Table Copy...", command=self.save_table_copy, accelerator="Ctrl+S")
        file_menu.add_command(label="Batch Export Visible...", command=self.batch_export, accelerator="Ctrl+B")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        menubar.add_cascade(label="File", menu=file_menu)

        self.main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # LEFT PANEL
        left_frame = ttk.Frame(self.main_pane, width=255)
        self.main_pane.add(left_frame, weight=0)

        flt = ttk.Frame(left_frame)
        flt.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4, 2))
        ttk.Label(flt, text="Filter:").pack(side=tk.LEFT)
        self.filter_entry = ttk.Entry(flt, textvariable=self.filter_text)
        self.filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))

        srt = ttk.Frame(left_frame)
        srt.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(0, 3))
        ttk.Label(srt, text="Sort:").pack(side=tk.LEFT)
        self.sort_combo = ttk.Combobox(
            srt,
            textvariable=self.sort_key,
            values=["Name", "File", "U", "V", "W", "H", "TW", "TH", "Flags", "Area", "Aspect"],
            state="readonly",
            width=8,
        )
        self.sort_combo.pack(side=tk.LEFT, padx=(3, 0))
        ttk.Checkbutton(srt, text="Desc", variable=self.sort_desc).pack(side=tk.LEFT, padx=(3, 0))

        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tree_frame, selectmode="browse", show="tree")
        self.tree.heading("#0", text="Sprites", anchor="w")
        self.tree.tag_configure("modified", foreground="#f0c050")
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<Button-3>", self.on_tree_context_menu)

        self.tree_context = tk.Menu(self.root, tearoff=0)
        self.tree_context.add_command(label="Copy Name", command=self.copy_sprite_name)
        self.tree_context.add_command(label="Copy File", command=self.copy_sprite_file)
        self.tree_context.add_separator()
        self.tree_context.add_command(label="Open Texture", command=self.open_image_file)
        self.tree_context.add_command(label="Open Folder", command=self.open_file_location)
        self.tree_context.add_separator()
        self.tree_context.add_command(label="Export (adj)...", command=self.export_sprite)
        self.tree_context.add_command(label="Save Raw Crop...", command=self.save_raw_crop)

        # RIGHT PANEL
        right_pane = ttk.PanedWindow(self.main_pane, orient=tk.HORIZONTAL)
        self.main_pane.add(right_pane, weight=1)

        canvas_frame = ttk.Frame(right_pane)
        right_pane.add(canvas_frame, weight=1)

        toolbar = ttk.Frame(canvas_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=2, pady=2)

        for text, cmd in [("In", self.zoom_in), ("Out", self.zoom_out), ("Fit", self.set_zoom_fit), ("100%", self.set_zoom_100), ("Ctr", self.center_image)]:
            ttk.Button(toolbar, text=text, command=cmd, style="Toolbar.TButton", width=4).pack(side=tk.LEFT, padx=1)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=4, fill=tk.Y)
        self.zoom_label = ttk.Label(toolbar, text="100%", width=5, anchor="center")
        self.zoom_label.pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=4, fill=tk.Y)
        ttk.Checkbutton(toolbar, text="AA", variable=self.antialias, command=self.update_display).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(toolbar, text="Grid", variable=self.grid_alpha, command=self.update_display).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="BG", command=self.choose_solid_color, style="Toolbar.TButton", width=3).pack(side=tk.LEFT, padx=1)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=4, fill=tk.Y)
        ttk.Button(toolbar, text="Export", command=self.export_sprite, style="Toolbar.TButton").pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="Raw", command=self.save_raw_crop, style="Toolbar.TButton").pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="Batch", command=self.batch_export, style="Toolbar.TButton").pack(side=tk.LEFT, padx=1)

        self.status = ttk.Label(canvas_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        self.h_scroll = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas = tk.Canvas(canvas_frame, bg=self.bg_color, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", self.on_mousewheel)
        self.canvas.bind("<Button-5>", self.on_mousewheel)
        self.canvas.bind("<ButtonPress-1>", self.on_pan_start)
        self.canvas.bind("<B1-Motion>", self.on_pan_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_pan_end)
        self.canvas.bind("<Configure>", lambda e: self.update_display())

        # SIDE NOTEBOOK
        side_notebook = ttk.Notebook(right_pane, width=255)
        right_pane.add(side_notebook, weight=0)

        prop_frame = ttk.Frame(side_notebook)
        side_notebook.add(prop_frame, text="Properties")
        prop_frame.columnconfigure(0, weight=1)
        prop_frame.columnconfigure(1, weight=1)

        pf = ttk.Frame(prop_frame)
        pf.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(4, 2))
        pf.columnconfigure(0, weight=1)
        self.file_path_var = tk.StringVar(value="")
        ttk.Entry(pf, textvariable=self.file_path_var, state="readonly").grid(row=0, column=0, sticky="ew")
        ttk.Button(pf, text="▶", command=self.open_image_file, width=2).grid(row=0, column=1, padx=(2, 0))
        ttk.Button(pf, text="📂", command=self.open_file_location, width=2).grid(row=0, column=2, padx=(2, 0))

        ttk.Separator(prop_frame, orient=tk.HORIZONTAL).grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=3)

        self.prop_vars: Dict[str, tk.StringVar] = {}
        prop_fields = [
            (2, 0, "U:", "u"),
            (2, 1, "V:", "v"),
            (3, 0, "W:", "w"),
            (3, 1, "H:", "h"),
            (4, 0, "TW:", "tw"),
            (4, 1, "TH:", "th"),
        ]
        for row_i, col_i, lbl, key in prop_fields:
            f = ttk.Frame(prop_frame)
            f.grid(row=row_i, column=col_i, padx=(4, 2), pady=1, sticky="ew")
            ttk.Label(f, text=lbl, width=3, anchor="e").pack(side=tk.LEFT)
            var = tk.StringVar()
            self.prop_vars[key] = var
            sp = ttk.Spinbox(f, textvariable=var, from_=0, to=99999, increment=1, width=6)
            sp.pack(side=tk.LEFT, fill=tk.X, expand=True)
            sp.bind("<KeyRelease>", lambda e, k=key: self.on_property_edit(k))
            sp.bind("<FocusOut>", lambda e, k=key: self.on_property_edit(k, final=True))
            var.trace_add("write", lambda *_args, k=key: self.on_property_edit(k))

        ff = ttk.Frame(prop_frame)
        ff.grid(row=5, column=0, columnspan=2, padx=4, pady=1, sticky="ew")
        ttk.Label(ff, text="Flags:", width=5, anchor="e").pack(side=tk.LEFT)
        self.prop_vars["flags"] = tk.StringVar()
        fl_ent = ttk.Entry(ff, textvariable=self.prop_vars["flags"])
        fl_ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
        fl_ent.bind("<KeyRelease>", lambda e: self.on_property_edit("flags"))
        fl_ent.bind("<FocusOut>", lambda e: self.on_property_edit("flags", final=True))
        self.prop_vars["flags"].trace_add("write", lambda *_: self.on_property_edit("flags"))

        self.size_info_var = tk.StringVar(value="")
        ttk.Label(prop_frame, textvariable=self.size_info_var, foreground="#888888").grid(
            row=6, column=0, columnspan=2, padx=4, pady=(2, 0), sticky="w"
        )

        ttk.Separator(prop_frame, orient=tk.HORIZONTAL).grid(row=7, column=0, columnspan=2, sticky="ew", padx=4, pady=4)

        bf = ttk.Frame(prop_frame)
        bf.grid(row=8, column=0, columnspan=2, padx=4, pady=2, sticky="ew")
        bf.columnconfigure(0, weight=1)
        bf.columnconfigure(1, weight=1)
        ttk.Button(bf, text="Reset Props", command=self.reset_properties).grid(row=0, column=0, padx=(0, 2), sticky="ew")
        ttk.Button(bf, text="Save Entry", command=self.save_entry_to_table, style="Accent.TButton").grid(row=0, column=1, padx=(2, 0), sticky="ew")

        bf2 = ttk.Frame(prop_frame)
        bf2.grid(row=9, column=0, columnspan=2, padx=4, pady=(2, 5), sticky="ew")
        bf2.columnconfigure(0, weight=1)
        bf2.columnconfigure(1, weight=1)
        ttk.Button(bf2, text="Export Adj.", command=self.export_sprite).grid(row=0, column=0, padx=(0, 2), sticky="ew")
        ttk.Button(bf2, text="Raw Crop", command=self.save_raw_crop).grid(row=0, column=1, padx=(2, 0), sticky="ew")

        adj_frame = ttk.Frame(side_notebook)
        side_notebook.add(adj_frame, text="Adjust")
        adj_frame.columnconfigure(1, weight=1)

        sliders = [
            ("Bright", self.brightness_var, 0.0, 3.0),
            ("Contrast", self.contrast_var, 0.0, 3.0),
            ("Saturate", self.saturation_var, 0.0, 3.0),
            ("Gamma", self.gamma_var, 0.1, 5.0),
            ("Hue", self.hue_var, -180.0, 180.0),
        ]
        for i, (lbl, var, mn, mx) in enumerate(sliders):
            self._create_adj_widget(adj_frame, lbl, var, mn, mx, i)

        n = len(sliders)
        ttk.Separator(adj_frame, orient=tk.HORIZONTAL).grid(row=n, column=0, columnspan=3, sticky="ew", padx=6, pady=4)
        ttk.Checkbutton(adj_frame, text="Invert Colors", variable=self.invert_var).grid(row=n + 1, column=0, columnspan=3, padx=6, sticky="w")
        ttk.Button(adj_frame, text="Reset All", command=self.reset_adjustments).grid(row=n + 2, column=0, columnspan=3, padx=6, pady=(4, 6), sticky="ew")

        save_frame = ttk.Frame(side_notebook)
        side_notebook.add(save_frame, text="Save")
        self._create_save_tab(save_frame)

    def _create_save_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        row = 0

        def section(text: str, r: int) -> None:
            ttk.Label(parent, text=text, foreground="#888888").grid(row=r, column=0, padx=6, pady=(7, 2), sticky="w")

        def btn(text: str, cmd, r: int, accent: bool = False) -> None:
            style = "Accent.TButton" if accent else "TButton"
            ttk.Button(parent, text=text, command=cmd, style=style).grid(row=r, column=0, padx=6, pady=2, sticky="ew")

        section("Current Sprite", row)
        row += 1
        btn("Export with Adjustments...", self.export_sprite, row)
        row += 1
        btn("Save Raw Crop (no adjustments)...", self.save_raw_crop, row)
        row += 1
        btn("Copy Image to Clipboard", self.copy_image_to_clipboard, row)
        row += 1

        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(row=row, column=0, sticky="ew", padx=6, pady=5)
        row += 1

        section("Sprite Table", row)
        row += 1
        btn("Save Modified Entry to Table...", self.save_entry_to_table, row, accent=True)
        row += 1
        btn("Save Full Modified Table Copy...", self.save_table_copy, row, accent=True)
        row += 1

        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(row=row, column=0, sticky="ew", padx=6, pady=5)
        row += 1

        section("Batch Export", row)
        row += 1
        btn("Batch Export Visible Sprites...", self.batch_export, row)
        row += 1
        btn("Batch Export Current File Group...", self.batch_export_file_group, row)
        row += 1

        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(row=row, column=0, sticky="ew", padx=6, pady=5)
        row += 1

        self.mod_count_var = tk.StringVar(value="No modifications")
        ttk.Label(parent, textvariable=self.mod_count_var, foreground="#888888").grid(row=row, column=0, padx=6, pady=(2, 4), sticky="w")

    def _create_adj_widget(self, parent: ttk.Frame, label: str, variable: tk.DoubleVar, min_val: float, max_val: float, row_idx: int) -> None:
        ttk.Label(parent, text=label, width=8, anchor="e").grid(row=row_idx, column=0, padx=(6, 2), pady=2, sticky="e")
        scale = ttk.Scale(parent, from_=min_val, to=max_val, variable=variable, orient=tk.HORIZONTAL)
        scale.grid(row=row_idx, column=1, padx=2, pady=2, sticky="ew")
        val_lbl = ttk.Label(parent, width=5, anchor="w")
        val_lbl.grid(row=row_idx, column=2, padx=(2, 6), pady=2, sticky="w")

        def upd(*_args):
            try:
                val_lbl.configure(text=f"{variable.get():.2f}")
            except Exception:
                pass

        variable.trace_add("write", upd)
        upd()

    def reset_adjustments(self) -> None:
        self.brightness_var.set(1.0)
        self.contrast_var.set(1.0)
        self.saturation_var.set(1.0)
        self.gamma_var.set(1.0)
        self.hue_var.set(0.0)
        self.invert_var.set(False)

    # ------------------------------------------------------------------
    # TREE
    # ------------------------------------------------------------------
    def on_tree_context_menu(self, event) -> None:
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.tree_context.tk_popup(event.x_root, event.y_root)

    def copy_sprite_name(self) -> None:
        if self.current_sprite:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_sprite["name"])

    def copy_sprite_file(self) -> None:
        if self.current_sprite:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_sprite["file"])

    def load_sprite_table(self) -> None:
        try:
            self.table_lines = Path(self.sprite_table_path).read_text(encoding="utf-8", errors="ignore").splitlines(True)  # type: ignore[arg-type]
            entries = parse_sprite_table(self.sprite_table_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse sprite table:\n{e}")
            return

        self.sprite_entries = entries
        self.file_groups = {}
        for ent in entries:
            self.file_groups.setdefault(ent["file"].lower(), []).append(ent)
        self.rebuild_tree()
        self.status.config(text=f"Loaded {len(entries)} sprites from {len(self.file_groups)} files.")

    def _sort_key_func(self, key_name: str):
        key_map = {
            "Name": lambda e: e["name"].lower(),
            "File": lambda e: e["file"].lower(),
            "U": lambda e: e["u"],
            "V": lambda e: e["v"],
            "W": lambda e: e["w"],
            "H": lambda e: e["h"],
            "TW": lambda e: e["tw"],
            "TH": lambda e: e["th"],
            "Flags": lambda e: e["flags"].lower(),
            "Area": lambda e: e["w"] * e["h"],
            "Aspect": lambda e: (e["w"] / e["h"]) if e["h"] else 0.0,
        }
        return key_map.get(key_name, key_map["Name"])

    def rebuild_tree(self) -> None:
        selected_key = self.current_key

        self.tree.delete(*self.tree.get_children())
        filter_lower = self.filter_text.get().lower().strip()
        sort_name = self.sort_key.get()
        desc = self.sort_desc.get()
        key_func = self._sort_key_func(sort_name)

        for fname in sorted(self.file_groups.keys()):
            file_entries = self.file_groups[fname]
            if filter_lower:
                file_entries = [e for e in file_entries if filter_lower in e["name"].lower() or filter_lower in e["file"].lower()]
            if not file_entries:
                continue

            file_node = self.tree.insert("", "end", text=f"{fname} ({len(file_entries)})", values=("file", fname), open=True)

            hierarchy = self._build_hierarchy(file_entries)
            self._populate_tree(file_node, hierarchy, fname, key_func, desc)

        for root_item in self.tree.get_children(""):
            self._open_recursive(root_item)

        # restore selection if possible
        if selected_key:
            target = None
            for item in self.tree.get_children(""):
                found = self._find_tree_item_by_key(item, selected_key)
                if found:
                    target = found
                    break
            if target:
                self.tree.selection_set(target)
                self.tree.see(target)

    def _find_tree_item_by_key(self, item_id: str, key: Tuple[str, str]) -> Optional[str]:
        vals = self.tree.item(item_id, "values")
        if vals and len(vals) >= 3 and vals[0] == "sprite":
            if (vals[2], vals[1]) == key:
                return item_id
        for child in self.tree.get_children(item_id):
            found = self._find_tree_item_by_key(child, key)
            if found:
                return found
        return None

    def _open_recursive(self, item_id: str) -> None:
        self.tree.item(item_id, open=True)
        for child in self.tree.get_children(item_id):
            self._open_recursive(child)

    def _build_hierarchy(self, entries: List[dict]) -> dict:
        root_node = {"sprite_entries": [], "subdirs": {}}
        for ent in entries:
            parts = re.split(r"[\\/]", ent["name"])
            cur = root_node
            for part in parts[:-1]:
                cur = cur["subdirs"].setdefault(part, {"sprite_entries": [], "subdirs": {}})
            cur["sprite_entries"].append((parts[-1], ent))
        return root_node

    def _populate_tree(self, parent_node: str, node: dict, file_key: str, key_func, desc: bool) -> None:
        for subdir in sorted(node["subdirs"].keys()):
            sub_node = self.tree.insert(parent_node, "end", text=subdir, values=("folder",))
            self._populate_tree(sub_node, node["subdirs"][subdir], file_key, key_func, desc)

        for sprite_name, ent in sorted(node["sprite_entries"], key=lambda x: key_func(x[1]), reverse=desc):
            is_mod = (file_key, ent["name"]) in self.modified_entries
            tag = ("modified",) if is_mod else ()
            self.tree.insert(parent_node, "end", text=sprite_name, values=("sprite", ent["name"], file_key), tags=tag)

    # ------------------------------------------------------------------
    # IMAGE LOADING
    # ------------------------------------------------------------------
    def _get_path_for_file_key(self, file_key: str) -> Optional[str]:
        if file_key not in self.file_paths:
            self.file_paths[file_key] = find_image_file(self.resources_path, file_key) if self.resources_path else None
        return self.file_paths.get(file_key)

    def get_image(self, file_key_lower: str) -> Optional[Image.Image]:
        if file_key_lower in self.image_cache:
            return self.image_cache[file_key_lower]

        original_path = self._get_path_for_file_key(file_key_lower)
        if not original_path:
            self.image_cache[file_key_lower] = None
            return None

        try:
            img = Image.open(original_path).convert("RGBA")
            self.image_cache[file_key_lower] = img
            return img
        except Exception:
            if Path(TEXCONV_PATH).is_file():
                self.status.config(text=f"Converting {file_key_lower}...")
                self.root.update_idletasks()
                png_path = texconv_convert(original_path, str(CACHE_DIR))
                if png_path:
                    try:
                        img = Image.open(png_path).convert("RGBA")
                        self.image_cache[file_key_lower] = img
                        self.file_paths[file_key_lower] = png_path
                        self.status.config(text=f"Converted {file_key_lower}")
                        return img
                    except Exception as e2:
                        print(f"Failed to load converted PNG: {e2}")

        self.image_cache[file_key_lower] = None
        return None

    def get_sprite_image(self, entry: Optional[dict]) -> Optional[Image.Image]:
        if entry is None:
            return None
        source_img = self.get_image(entry["file"].lower())
        if source_img is None:
            return None

        img_w, img_h = source_img.size
        tw, th = entry["tw"], entry["th"]
        u, v, w, h = entry["u"], entry["v"], entry["w"], entry["h"]

        left = round(u * img_w / tw) if tw > 0 else 0
        top = round(v * img_h / th) if th > 0 else 0
        right = round((u + w) * img_w / tw) if tw > 0 else img_w
        bottom = round((v + h) * img_h / th) if th > 0 else img_h

        left = max(0, min(left, img_w))
        top = max(0, min(top, img_h))
        right = max(0, min(right, img_w))
        bottom = max(0, min(bottom, img_h))

        if right <= left or bottom <= top:
            return None
        return source_img.crop((left, top, right, bottom))

    def apply_adjustments(self, img: Optional[Image.Image]) -> Optional[Image.Image]:
        if img is None:
            return None

        im = img.copy()

        b = float(self.brightness_var.get())
        c = float(self.contrast_var.get())
        s = float(self.saturation_var.get())
        if b != 1.0:
            im = ImageEnhance.Brightness(im).enhance(b)
        if c != 1.0:
            im = ImageEnhance.Contrast(im).enhance(c)
        if s != 1.0:
            im = ImageEnhance.Color(im).enhance(s)

        gamma = float(self.gamma_var.get())
        if gamma != 1.0:
            inv_gamma = 1.0 / gamma
            table = [int(255 * ((i / 255) ** inv_gamma)) for i in range(256)]
            if im.mode == "RGBA":
                r, g, b, a = im.split()
                im = Image.merge("RGBA", (r.point(table), g.point(table), b.point(table), a))
            else:
                im = im.point(table)

        hue = float(self.hue_var.get())
        if hue != 0.0:
            alpha = im.getchannel("A") if im.mode == "RGBA" else None
            rgb = im.convert("RGB").convert("HSV")
            h, s_ch, v = rgb.split()
            shift = int(hue * 255 / 360.0)
            h = h.point(lambda p: (p + shift) % 256)
            im = Image.merge("HSV", (h, s_ch, v)).convert("RGBA")
            if alpha is not None:
                im.putalpha(alpha)

        if self.invert_var.get():
            if im.mode == "RGBA":
                r, g, b, a = im.split()
                im = Image.merge("RGBA", (ImageOps.invert(r), ImageOps.invert(g), ImageOps.invert(b), a))
            else:
                im = ImageOps.invert(im)

        return im

    def get_active_entry(self) -> Optional[dict]:
        if self.current_key is None:
            return None
        return self.modified_entries.get(self.current_key, self.current_sprite)

    # ------------------------------------------------------------------
    # DISPLAY
    # ------------------------------------------------------------------
    def update_display(self) -> None:
        self.canvas.delete("all")

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 2 or ch < 2:
            return

        if self.grid_alpha.get():
            self.canvas.configure(bg=self.bg_color)
            self._draw_checkerboard(cw, ch)
        else:
            self.canvas.configure(bg=self.solid_color)

        if hasattr(self, "zoom_label"):
            self.zoom_label.configure(text=f"{int(round(self.zoom_factor * 100))}%")

        if self.current_key is None:
            self.status.config(text="No sprite selected.")
            return

        entry = self.get_active_entry()
        if entry is None:
            self.status.config(text="No sprite selected.")
            return

        sprite_img = self.get_sprite_image(entry)
        if sprite_img is None:
            self.canvas.create_text(cw / 2, ch / 2, text="Image not found or unsupported format", fill="red", font=("", 12, "bold"))
            self.status.config(text=f"Missing: {entry['file']}")
            return

        adjusted = self.apply_adjustments(sprite_img)
        if adjusted is None:
            return

        new_w = max(1, int(round(adjusted.width * self.zoom_factor)))
        new_h = max(1, int(round(adjusted.height * self.zoom_factor)))
        filt = Image.NEAREST if not self.antialias.get() else Image.LANCZOS
        resized = adjusted.resize((new_w, new_h), filt)

        self._tk_image = ImageTk.PhotoImage(resized)
        self.canvas.create_image(self.pan_x, self.pan_y, anchor="nw", image=self._tk_image)
        self.canvas.configure(scrollregion=(0, 0, max(new_w, cw), max(new_h, ch)))

        self.size_info_var.set(f"{sprite_img.width} × {sprite_img.height} px")
        mc = len(self.modified_entries)
        self.mod_count_var.set(f"{mc} modification{'s' if mc != 1 else ''}" if mc else "No modifications")

        self.status.config(
            text=f"{entry['name']}  |  {sprite_img.width}×{sprite_img.height}px  |  Zoom: {int(round(self.zoom_factor * 100))}%  |  {entry['file']}"
        )

    def _draw_checkerboard(self, width: int, height: int) -> None:
        self.canvas.delete("checker")
        sq = 16
        for y in range(0, height, sq):
            for x in range(0, width, sq):
                color = "#555555" if ((x // sq) + (y // sq)) % 2 == 0 else "#2b2b2b"
                self.canvas.create_rectangle(x, y, x + sq, y + sq, fill=color, outline="", tags="checker")
        self.canvas.tag_lower("checker")

    # ------------------------------------------------------------------
    # ZOOM / PAN
    # ------------------------------------------------------------------
    def apply_zoom_mode(self) -> None:
        if self.zoom_mode == "fit":
            self._zoom_fit()
        elif self.zoom_mode == "100%":
            self.zoom_factor = 1.0
            self.center_image()
        else:
            self.center_image()

    def set_zoom_100(self) -> None:
        self.zoom_mode = "100%"
        self.zoom_factor = 1.0
        self.center_image()

    def set_zoom_fit(self) -> None:
        self.zoom_mode = "fit"
        self._zoom_fit()

    def _zoom_fit(self) -> None:
        if not self.current_key:
            return
        img = self.get_sprite_image(self.get_active_entry())
        if img is None:
            return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 2 or ch < 2:
            return
        self.zoom_factor = min(cw / img.width, ch / img.height) * 0.9
        self.center_image()

    def zoom_in(self) -> None:
        self.zoom_mode = "custom"
        self.zoom_factor = min(self.zoom_factor * 1.2, 64.0)
        self.update_display()

    def zoom_out(self) -> None:
        self.zoom_mode = "custom"
        self.zoom_factor = max(self.zoom_factor / 1.2, 0.05)
        self.update_display()

    def center_image(self) -> None:
        if not self.current_key:
            return
        img = self.get_sprite_image(self.get_active_entry())
        if img is None:
            return
        adj = self.apply_adjustments(img)
        if adj is None:
            return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 2 or ch < 2:
            return
        self.pan_x = (cw - adj.width * self.zoom_factor) / 2
        self.pan_y = (ch - adj.height * self.zoom_factor) / 2
        self.update_display()

    def on_pan_start(self, event) -> None:
        self._pan_start_x = event.x
        self._pan_start_y = event.y
        self._pan_orig_x = self.pan_x
        self._pan_orig_y = self.pan_y

    def on_pan_move(self, event) -> None:
        self.pan_x = self._pan_orig_x + (event.x - self._pan_start_x)
        self.pan_y = self._pan_orig_y + (event.y - self._pan_start_y)
        self.update_display()

    def on_pan_end(self, event) -> None:
        pass

    def on_mousewheel(self, event) -> None:
        if event.delta:
            delta = event.delta
        elif event.num == 4:
            delta = 120
        elif event.num == 5:
            delta = -120
        else:
            return

        factor = 1.1 if delta > 0 else 0.9
        old_zoom = self.zoom_factor
        new_zoom = max(0.05, min(old_zoom * factor, 64.0))
        if new_zoom == old_zoom:
            return

        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        x = cx - self.pan_x
        y = cy - self.pan_y
        scale = new_zoom / old_zoom
        self.pan_x = cx - x * scale
        self.pan_y = cy - y * scale
        self.zoom_factor = new_zoom
        self.zoom_mode = "custom"
        self.update_display()

    def choose_solid_color(self) -> None:
        color = colorchooser.askcolor(title="Choose background color", initialcolor=self.solid_color)
        if color[1]:
            self.solid_color = color[1]
            if not self.grid_alpha.get():
                self.canvas.configure(bg=self.solid_color)
            self.update_display()

    # ------------------------------------------------------------------
    # TREE SELECTION & PROPERTIES
    # ------------------------------------------------------------------
    def on_tree_select(self, event) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        if not values or values[0] != "sprite":
            return

        sprite_name = values[1]
        file_key = values[2]
        entry = next((e for e in self.file_groups.get(file_key, []) if e["name"] == sprite_name), None)
        if not entry:
            return

        self.current_key = (file_key, sprite_name)
        self.current_sprite = self.modified_entries.get(self.current_key, entry)
        self.update_properties_panel()
        self.apply_zoom_mode()

    def update_properties_panel(self) -> None:
        if not self.current_key:
            self.clear_properties()
            return

        self._updating_props = True
        try:
            entry = self.get_active_entry()
            if entry is None:
                self.clear_properties()
                return

            file_key = entry["file"].lower()
            path = self._get_path_for_file_key(file_key)
            self.file_path_var.set(path if path else "Not found")
            for key in ["u", "v", "w", "h", "tw", "th", "flags"]:
                self.prop_vars[key].set(str(entry[key]))
            self.size_info_var.set(self._current_sprite_size_text(entry))
        finally:
            self._updating_props = False

    def _current_sprite_size_text(self, entry: dict) -> str:
        sprite_img = self.get_sprite_image(entry)
        if sprite_img is None:
            return ""
        return f"{sprite_img.width} × {sprite_img.height} px"

    def clear_properties(self) -> None:
        self._updating_props = True
        try:
            self.file_path_var.set("")
            for var in self.prop_vars.values():
                var.set("")
            self.size_info_var.set("")
        finally:
            self._updating_props = False

    def _entry_from_ui(self) -> Optional[dict]:
        if not self.current_key:
            return None
        original = next((e for e in self.file_groups.get(self.current_key[0], []) if e["name"] == self.current_key[1]), None)
        if original is None:
            return None
        mod_entry = self.modified_entries.get(self.current_key)
        if mod_entry is None:
            mod_entry = dict(original)
            self.modified_entries[self.current_key] = mod_entry
        return mod_entry

    def on_property_edit(self, key: str, final: bool = False) -> None:
        if self._updating_props or not self.current_key:
            return

        var = self.prop_vars.get(key)
        if var is None:
            return

        value_str = var.get().strip()
        original = next((e for e in self.file_groups.get(self.current_key[0], []) if e["name"] == self.current_key[1]), None)
        if original is None:
            return

        mod_entry = self.modified_entries.get(self.current_key)
        if mod_entry is None:
            mod_entry = dict(original)
            self.modified_entries[self.current_key] = mod_entry

        if key != "flags":
            if value_str in ("", "-", "+"):
                return
            try:
                mod_entry[key] = int(value_str)
            except ValueError:
                return
        else:
            mod_entry["flags"] = value_str

        self.current_sprite = mod_entry
        self._mark_current_tree_item_modified(True)

        if final:
            self.update_display()
        else:
            if self._edit_after_id:
                try:
                    self.root.after_cancel(self._edit_after_id)
                except Exception:
                    pass
            self._edit_after_id = self.root.after(120, self.update_display)

    def _mark_current_tree_item_modified(self, modified: bool) -> None:
        if not self.current_key:
            return
        target = None
        for item in self.tree.get_children(""):
            target = self._find_tree_item_by_key(item, self.current_key)
            if target:
                break
        if target:
            if modified:
                self.tree.item(target, tags=("modified",))
            else:
                self.tree.item(target, tags=())

    def reset_properties(self) -> None:
        if not self.current_key:
            return
        key = self.current_key
        if key in self.modified_entries:
            del self.modified_entries[key]
        orig = next((e for e in self.file_groups.get(key[0], []) if e["name"] == key[1]), None)
        if orig is None:
            return
        self.current_sprite = orig
        self.update_properties_panel()
        self.update_display()
        self.rebuild_tree()

    # ------------------------------------------------------------------
    # SAVE / EXPORT
    # ------------------------------------------------------------------
    def export_sprite(self) -> None:
        if not self.current_key:
            return
        raw = self.get_sprite_image(self.get_active_entry())
        if raw is None:
            messagebox.showerror("Error", "Cannot export - image not available.")
            return

        adjusted = self.apply_adjustments(raw)
        if adjusted is None:
            return

        name_clean = re.sub(r'[\\/:*?"<>|]', "_", self.get_active_entry()["name"] if self.get_active_entry() else "sprite")
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("TGA", "*.tga"), ("BMP", "*.bmp"), ("All files", "*.*")],
            initialfile=f"{name_clean}.png",
            title="Export Sprite with Adjustments",
        )
        if path:
            try:
                adjusted.save(path)
                self.status.config(text=f"Exported: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Export failed", str(e))

    def save_raw_crop(self) -> None:
        if not self.current_key:
            return
        raw = self.get_sprite_image(self.get_active_entry())
        if raw is None:
            messagebox.showerror("Error", "Cannot save - image not available.")
            return

        name_clean = re.sub(r'[\\/:*?"<>|]', "_", self.get_active_entry()["name"] if self.get_active_entry() else "sprite")
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("TGA", "*.tga"), ("BMP", "*.bmp"), ("All files", "*.*")],
            initialfile=f"{name_clean}_raw.png",
            title="Save Raw Sprite Crop (no adjustments)",
        )
        if path:
            try:
                raw.save(path)
                self.status.config(text=f"Saved raw crop: {os.path.basename(path)}")
            except Exception as e:
                messagebox.showerror("Save failed", str(e))

    def copy_image_to_clipboard(self) -> None:
        if not self.current_key:
            return
        raw = self.get_sprite_image(self.get_active_entry())
        if raw is None:
            messagebox.showwarning("Not available", "No image to copy.")
            return

        adjusted = self.apply_adjustments(raw)
        if adjusted is None:
            return

        try:
            if platform.system() == "Windows":
                try:
                    import win32clipboard  # type: ignore
                    bg = Image.new("RGB", adjusted.size, (128, 128, 128))
                    mask = adjusted.split()[3] if adjusted.mode == "RGBA" else None
                    bg.paste(adjusted.convert("RGB"), mask=mask)
                    buf = io.BytesIO()
                    bg.save(buf, format="BMP")
                    data = buf.getvalue()[14:]
                    buf.close()
                    win32clipboard.OpenClipboard()
                    try:
                        win32clipboard.EmptyClipboard()
                        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                    finally:
                        win32clipboard.CloseClipboard()
                    self.status.config(text="Image copied to clipboard.")
                    return
                except ImportError:
                    pass

            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            adjusted.save(tmp.name)
            tmp.close()
            self._temp_files.append(tmp.name)
            self.root.clipboard_clear()
            self.root.clipboard_append(tmp.name)
            self.status.config(text=f"Temp path copied to clipboard: {tmp.name}")
        except Exception as e:
            messagebox.showerror("Clipboard error", str(e))

    def save_entry_to_table(self) -> None:
        if not self.current_key:
            messagebox.showinfo("Nothing to save", "No sprite selected.")
            return
        if self.current_key not in self.modified_entries:
            messagebox.showinfo("Nothing to save", "No modifications on current sprite.\nEdit U/V/W/H/TW/TH/Flags first.")
            return
        self.save_table_copy(only_key=self.current_key)

    def save_table_copy(self, only_key: Optional[Tuple[str, str]] = None) -> None:
        if not self.sprite_table_path:
            return
        if not self.modified_entries:
            messagebox.showinfo("Nothing to save", "No modifications have been made.")
            return

        mods = {only_key: self.modified_entries[only_key]} if only_key and only_key in self.modified_entries else dict(self.modified_entries)
        if not mods:
            messagebox.showinfo("Nothing to save", "No applicable modifications.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="sprite_modified.txt",
            title="Save Modified Sprite Table Copy",
        )
        if not path:
            return

        try:
            out_lines = list(self.table_lines)
            mod_lookup = {key: entry for key, entry in mods.items()}
            newline = "\r\n" if any(line.endswith("\r\n") for line in self.table_lines) else "\n"

            for idx, line in enumerate(out_lines):
                m = SPRITE_LINE_RE.match(line.rstrip("\n").rstrip("\r"))
                if not m:
                    continue
                key = (m.group("file"), m.group("name"))
                if key not in mod_lookup:
                    continue
                e = mod_lookup[key]
                indent = m.group("indent")
                out_lines[idx] = (
                    f'{indent}"{e["name"]}" {e["file"]} '
                    f'{int(e["u"])} {int(e["v"])} {int(e["w"])} {int(e["h"])} '
                    f'{int(e["tw"])} {int(e["th"])} {e["flags"]}{newline}'
                )

            with open(path, "w", encoding="utf-8", newline="") as f:
                f.writelines(out_lines)
            mc = len(mods)
            msg = f"Saved with {mc} modification{'s' if mc != 1 else ''}:\n{os.path.basename(path)}"
            self.status.config(text=f"Table saved: {os.path.basename(path)}")
            messagebox.showinfo("Saved", msg)
        except Exception as e:
            messagebox.showerror("Save failed", str(e))

    def batch_export(self) -> None:
        filter_lower = self.filter_text.get().lower().strip()
        to_export = [
            e for entries in self.file_groups.values()
            for e in entries
            if not filter_lower or filter_lower in e["name"].lower() or filter_lower in e["file"].lower()
        ]
        if not to_export:
            messagebox.showinfo("Nothing", "No sprites match the current filter.")
            return
        self._do_batch_export(to_export)

    def batch_export_file_group(self) -> None:
        if not self.current_key:
            messagebox.showinfo("No selection", "Select a sprite first.")
            return
        file_key = self.current_key[0]
        entries = self.file_groups.get(file_key, [])
        if not entries:
            messagebox.showinfo("Nothing", "No sprites in current file group.")
            return
        self._do_batch_export(entries)

    def _do_batch_export(self, entries: List[dict]) -> None:
        folder = filedialog.askdirectory(title=f"Select output folder for {len(entries)} sprites")
        if not folder:
            return

        apply_adj = messagebox.askyesno(
            "Apply Adjustments?",
            "Apply current brightness/contrast/gamma/etc. to exported sprites?",
        )

        success = 0
        fail = 0
        for e in entries:
            try:
                img = self.get_sprite_image(e)
                if img is None:
                    fail += 1
                    continue
                if apply_adj:
                    img = self.apply_adjustments(img)
                if img is None:
                    fail += 1
                    continue
                name_clean = re.sub(r'[\\/:*?"<>|]', "_", e["name"])
                img.save(os.path.join(folder, f"{name_clean}.png"))
                success += 1
            except Exception as ex:
                print(f"Batch export error [{e['name']}]: {ex}")
                fail += 1

        self.status.config(text=f"Batch done: {success} exported, {fail} failed.")
        messagebox.showinfo(
            "Batch Export Done",
            f"Exported {success} sprite{'s' if success != 1 else ''}.\n{fail} failed.\n\nOutput folder:\n{folder}",
        )

    # ------------------------------------------------------------------
    # FILE OPEN HELPERS
    # ------------------------------------------------------------------
    def open_image_file(self) -> None:
        if not self.current_key:
            return
        path = self._get_path_for_file_key(self.current_key[0])
        if path and os.path.isfile(path):
            self._open_file_with_default(path)
        else:
            messagebox.showwarning("Not found", "Image file not found on disk.")

    def open_file_location(self) -> None:
        if not self.current_key:
            return
        path = self._get_path_for_file_key(self.current_key[0])
        if path and os.path.isfile(path):
            self._open_file_explorer(path)
        else:
            messagebox.showwarning("Not found", "Image file not found on disk.")

    def _open_file_with_default(self, path: str) -> None:
        if platform.system() == "Windows":
            os.startfile(path)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.run(["open", path], check=False)
        else:
            opener = shutil.which("xdg-open")
            if opener:
                subprocess.run([opener, path], check=False)

    def _open_file_explorer(self, path: str) -> None:
        if platform.system() == "Windows":
            subprocess.run(["explorer", "/select,", path], check=False)
        elif platform.system() == "Darwin":
            subprocess.run(["open", os.path.dirname(path)], check=False)
        else:
            opener = shutil.which("xdg-open")
            if opener:
                subprocess.run([opener, os.path.dirname(path)], check=False)

    def change_resource_folder(self) -> None:
        self.ask_resource_folder()
        if self.resources_path and self.sprite_table_path:
            self.refresh()


# ----------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SpriteViewer(root)
    if getattr(app, "root", None) is not None and app.root.winfo_exists():
        root.mainloop()
