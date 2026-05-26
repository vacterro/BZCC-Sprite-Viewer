#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BZ2 Sprite Viewer — Enhanced Edition
Compact, robust, esoteric as fuck.
By: Alex & Angry Esoteric Grandpa
"""
from __future__ import annotations

import io
import os
import re
import sys
import json
import time
import logging
import subprocess
import tempfile
import platform
import traceback
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple, Any, Callable

import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from PIL import Image, ImageTk, ImageEnhance, ImageOps

# ----------------------------------------------------------------------
# Logging setup
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Configuration & paths
# ----------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "sprite_viewer_config.json")

if getattr(sys, 'frozen', False):
    TEXCONV_PATH = os.path.join(sys._MEIPASS, "texconv.exe")
else:
    TEXCONV_PATH = os.path.join(SCRIPT_DIR, "texconv.exe")

CACHE_DIR = os.path.join(tempfile.gettempdir(), "bz2_sprite_cache")
MAX_CACHE_SIZE = 50  # LRU cache limit


def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Config load failed: {e}")
    return {}


def save_config(config: Dict[str, Any]) -> None:
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Config save failed: {e}")


# ----------------------------------------------------------------------
# LRU Image Cache
# ----------------------------------------------------------------------
class LRUCache:
    def __init__(self, capacity: int = MAX_CACHE_SIZE):
        self.cache: OrderedDict[str, Image.Image] = OrderedDict()
        self.capacity = capacity

    def get(self, key: str) -> Optional[Image.Image]:
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, value: Image.Image) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        elif len(self.cache) >= self.capacity:
            oldest = next(iter(self.cache))
            del self.cache[oldest]
            logger.debug(f"Cache evicted: {oldest}")
        self.cache[key] = value

    def clear(self) -> None:
        self.cache.clear()


# ----------------------------------------------------------------------
# Sprite table parsing
# ----------------------------------------------------------------------
def parse_sprite_table(filepath: str) -> List[Dict[str, Any]]:
    entries = []
    pattern = re.compile(
        r'^"([^"]+)"\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+)'
    )
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('@include'):
                continue
            m = pattern.match(line)
            if not m:
                logger.debug(f"Skipping malformed line {line_num}: {line[:60]}...")
                continue
            try:
                entries.append({
                    'name':  m.group(1),
                    'file':  m.group(2),
                    'u':     int(m.group(3)),
                    'v':     int(m.group(4)),
                    'w':     int(m.group(5)),
                    'h':     int(m.group(6)),
                    'tw':    int(m.group(7)),
                    'th':    int(m.group(8)),
                    'flags': m.group(9),
                })
            except ValueError as e:
                logger.warning(f"Parse error line {line_num}: {e}")
    return entries


# ----------------------------------------------------------------------
# Recursive file finder with caching
# ----------------------------------------------------------------------
_FILE_FIND_CACHE: Dict[str, Optional[str]] = {}


def find_image_file(base_dir: str, filename_no_ext: str) -> Optional[str]:
    cache_key = f"{base_dir}|{filename_no_ext}".lower()
    if cache_key in _FILE_FIND_CACHE:
        return _FILE_FIND_CACHE[cache_key]

    extensions = {'.png', '.dds', '.tga', '.bmp', '.jpg', '.jpeg', '.tif', '.tiff'}
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            name, ext = os.path.splitext(f)
            if name.lower() == filename_no_ext.lower() and ext.lower() in extensions:
                result = os.path.join(root, f)
                _FILE_FIND_CACHE[cache_key] = result
                return result
    _FILE_FIND_CACHE[cache_key] = None
    return None


# ----------------------------------------------------------------------
# texconv helper
# ----------------------------------------------------------------------
def texconv_convert(src_path: str, dst_dir: str) -> Optional[str]:
    if not os.path.isfile(TEXCONV_PATH):
        logger.warning(f"texconv.exe not found at {TEXCONV_PATH}")
        return None
    os.makedirs(dst_dir, exist_ok=True)
    try:
        result = subprocess.run(
            [TEXCONV_PATH, "-ft", "png", "-o", dst_dir, "-y", src_path],
            check=True, capture_output=True, text=True, timeout=30
        )
        logger.debug(f"texconv stdout: {result.stdout[:200]}")
    except subprocess.TimeoutExpired:
        logger.error(f"texconv timed out on {src_path}")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"texconv failed: {e.stderr[:200]}")
        return None
    base = os.path.splitext(os.path.basename(src_path))[0]
    png_path = os.path.join(dst_dir, base + ".png")
    return png_path if os.path.isfile(png_path) else None


# ----------------------------------------------------------------------
# Dark modern theme — FIXED (no invalid 'modified' state)
# ----------------------------------------------------------------------
def apply_dark_theme(root: tk.Tk) -> str:
    style = ttk.Style(root)
    style.theme_use('clam')

    bg_dark    = "#2b2b2b"
    bg_medium  = "#3c3c3c"
    fg_light   = "#e0e0e0"
    select_bg  = "#4a6e8c"
    entry_bg   = "#3c3c3c"
    entry_fg   = "#ffffff"
    button_bg  = "#4a4a4a"
    button_act = "#5c5c5c"
    tree_bg    = "#2b2b2b"
    tree_fg    = "#dcdcdc"
    tree_sel   = "#2a4b6e"

    default_font = ("Segoe UI", 9) if platform.system() == "Windows" else ("Helvetica", 10)
    root.option_add("*Font", default_font)

    style.configure("TFrame",         background=bg_dark)
    style.configure("TLabel",         background=bg_dark, foreground=fg_light)
    style.configure("TLabelframe",    background=bg_dark, foreground=fg_light)
    style.configure("TLabelframe.Label", background=bg_dark, foreground=fg_light)
    style.configure("TNotebook",      background=bg_dark, borderwidth=0)
    style.configure("TNotebook.Tab",  background=bg_medium, foreground=fg_light, padding=(8, 3))
    style.map("TNotebook.Tab",        background=[('selected', bg_dark)], foreground=[('selected', '#ffffff')])

    style.configure("TButton", background=button_bg, foreground=fg_light,
                    borderwidth=0, focusthickness=0, padding=(6, 3))
    style.map("TButton",
              background=[('active', button_act), ('pressed', select_bg)],
              foreground=[('active', fg_light)])

    style.configure("Accent.TButton", background="#2a5c8c", foreground=fg_light,
                    borderwidth=0, focusthickness=0, padding=(6, 3))
    style.map("Accent.TButton",
              background=[('active', "#3a7cbf"), ('pressed', select_bg)],
              foreground=[('active', fg_light)])

    style.configure("TEntry",   fieldbackground=entry_bg, foreground=entry_fg,
                    insertcolor=entry_fg, borderwidth=1, padding=2)
    style.configure("TSpinbox", fieldbackground=entry_bg, foreground=entry_fg,
                    insertcolor=entry_fg, borderwidth=1, padding=2, arrowsize=12)
    style.map("TSpinbox",
              fieldbackground=[('readonly', entry_bg)],
              foreground=[('readonly', entry_fg)])

    style.configure("TCheckbutton", background=bg_dark, foreground=fg_light)
    style.map("TCheckbutton",
              background=[('active', bg_dark)],
              foreground=[('active', fg_light)])

    # Treeview — ONLY valid states in style.map()
    style.configure("Treeview", background=tree_bg, foreground=tree_fg,
                    fieldbackground=tree_bg, borderwidth=1, rowheight=19)
    style.map("Treeview",
              background=[('selected', tree_sel)],
              foreground=[('selected', '#ffffff')])
    style.configure("Treeview.Heading", background=button_bg, foreground=fg_light,
                    relief="flat", padding=3)
    style.map("Treeview.Heading", background=[('active', button_act)])

    style.configure("Vertical.TScrollbar",   background=button_bg, troughcolor=bg_dark,
                    arrowcolor=fg_light, bordercolor=bg_dark)
    style.configure("Horizontal.TScrollbar", background=button_bg, troughcolor=bg_dark,
                    arrowcolor=fg_light, bordercolor=bg_dark)
    style.configure("TPanedwindow",  background=bg_dark, sashwidth=4,
                    sashrelief='flat', sashcolor=bg_medium)
    style.configure("Toolbar.TButton", padding=(7, 3))
    style.configure("TScale", background=bg_dark, troughcolor=bg_medium)

    return bg_dark


# ----------------------------------------------------------------------
# Main Application
# ----------------------------------------------------------------------
class SpriteViewer:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("BZ2 Sprite Viewer — Enhanced")
        self.root.geometry("1280x740")
        self.root.minsize(900, 500)

        self.bg_color = apply_dark_theme(root)

        self.config         = load_config()
        self.resources_path = self.config.get("resources_path")
        self.zoom_factor    = self.config.get("zoom_factor", 1.0)
        self.zoom_mode      = self.config.get("zoom_mode", "fit")

        self.antialias    = tk.BooleanVar(value=self.config.get("antialias", False))
        self.grid_alpha   = tk.BooleanVar(value=self.config.get("grid_alpha", True))
        self.solid_color  = self.config.get("solid_color", "#808080")
        self.filter_text  = tk.StringVar(value=self.config.get("filter_text", ""))

        self.brightness_var = tk.DoubleVar(value=self.config.get("brightness", 1.0))
        self.contrast_var   = tk.DoubleVar(value=self.config.get("contrast",   1.0))
        self.saturation_var = tk.DoubleVar(value=self.config.get("saturation", 1.0))
        self.gamma_var      = tk.DoubleVar(value=self.config.get("gamma",      1.0))
        self.hue_var        = tk.DoubleVar(value=self.config.get("hue",        0.0))
        self.invert_var     = tk.BooleanVar(value=self.config.get("invert",   False))

        self.sort_key  = tk.StringVar(value=self.config.get("sort_key",  "Name"))
        self.sort_desc = tk.BooleanVar(value=self.config.get("sort_desc", False))

        # Internal state
        self.sprite_entries: List[Dict[str, Any]] = []
        self.file_groups: Dict[str, List[Dict[str, Any]]] = {}
        self.image_cache = LRUCache(MAX_CACHE_SIZE)
        self.file_paths: Dict[str, Optional[str]] = {}
        self.current_sprite: Optional[Dict[str, Any]] = None
        self.modified_entries: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.pan_x = 0
        self.pan_y = 0
        self._tk_image: Optional[ImageTk.PhotoImage] = None
        self._updating_props = False
        self._edit_after_id: Optional[str] = None

        if "window_geometry" in self.config:
            try:
                self.root.geometry(self.config["window_geometry"])
            except Exception:
                pass

        self.sprite_table_path: Optional[str] = None
        if self.resources_path and os.path.isdir(self.resources_path):
            self.sprite_table_path = self.locate_sprite_table(self.resources_path)
            if not self.sprite_table_path:
                messagebox.showwarning("Warning",
                    "Saved resource folder has no sprite.txt. Please select a new one.")
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

        self.filter_text.trace_add("write", lambda *a: self.rebuild_tree())
        self.sort_key.trace_add("write",    lambda *a: self.rebuild_tree())
        self.sort_desc.trace_add("write",   lambda *a: self.rebuild_tree())
        for var in [self.brightness_var, self.contrast_var, self.saturation_var,
                    self.gamma_var, self.hue_var, self.invert_var]:
            var.trace_add("write", lambda *a: self.update_display())

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        if not self.grid_alpha.get():
            self.canvas.configure(bg=self.solid_color)

    # ------------------------------------------------------------------
    def on_closing(self) -> None:
        cfg = {
            "resources_path": self.resources_path,
            "window_geometry": self.root.winfo_geometry(),
            "zoom_factor":  self.zoom_factor,
            "zoom_mode":    self.zoom_mode,
            "antialias":    self.antialias.get(),
            "grid_alpha":   self.grid_alpha.get(),
            "solid_color":  self.solid_color,
            "brightness":   self.brightness_var.get(),
            "contrast":     self.contrast_var.get(),
            "saturation":   self.saturation_var.get(),
            "gamma":        self.gamma_var.get(),
            "hue":          self.hue_var.get(),
            "invert":       self.invert_var.get(),
            "filter_text":  self.filter_text.get(),
            "sort_key":     self.sort_key.get(),
            "sort_desc":    self.sort_desc.get(),
        }
        save_config(cfg)
        self.root.destroy()

    def setup_shortcuts(self) -> None:
        self.root.bind("<Control-f>",       lambda e: self.filter_entry.focus_set())
        self.root.bind("<Control-o>",       lambda e: self.open_image_file())
        self.root.bind("<Control-Shift-O>", lambda e: self.open_file_location())
        self.root.bind("<Control-0>",       lambda e: self.set_zoom_100())
        self.root.bind("<Control-plus>",    lambda e: self.zoom_in())
        self.root.bind("<Control-minus>",   lambda e: self.zoom_out())
        self.root.bind("<Control-e>",       lambda e: self.export_sprite())
        self.root.bind("<Control-s>",       lambda e: self.save_table_copy())
        self.root.bind("<Control-b>",       lambda e: self.batch_export())
        self.root.bind("<F5>",              lambda e: self.refresh())
        self.root.bind("<Control-Shift-F>", lambda e: self.change_resource_folder())
        # Tree navigation
        self.tree.bind("<Down>", lambda e: self._tree_nav(1))
        self.tree.bind("<Up>",   lambda e: self._tree_nav(-1))
        self.tree.bind("<Return>", lambda e: self._tree_select_current())

    def _tree_nav(self, direction: int) -> None:
        items = self.tree.get_children()
        if not items:
            return
        sel = self.tree.selection()
        idx = items.index(sel[0]) if sel and sel[0] in items else 0
        new_idx = max(0, min(len(items) - 1, idx + direction))
        self.tree.selection_set(items[new_idx])
        self.tree.see(items[new_idx])
        self.on_tree_select(None)

    def _tree_select_current(self) -> None:
        sel = self.tree.selection()
        if sel:
            self.tree.event_generate('<<TreeviewSelect>>')

    # ------------------------------------------------------------------
    def ask_resource_folder(self) -> None:
        path = filedialog.askdirectory(title="Select resource folder (e.g., BZ2R\\bz2r_res)")
        if not path:
            return
        self.resources_path = path
        self.sprite_table_path = self.locate_sprite_table(path)
        if not self.sprite_table_path:
            messagebox.showerror("Error",
                "Could not find sprite.txt inside the selected folder.\n"
                "Ensure it contains interface/sprite.txt or similar.")
            self.resources_path = None
        else:
            save_config({"resources_path": path})

    def locate_sprite_table(self, base_dir: str) -> Optional[str]:
        candidate = os.path.join(base_dir, "interface", "sprite.txt")
        if os.path.isfile(candidate):
            return candidate
        for root, dirs, files in os.walk(base_dir):
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
        _FILE_FIND_CACHE.clear()
        self.modified_entries.clear()
        self.current_sprite = None
        self.load_sprite_table()
        self.update_display()
        self.clear_properties()

    # ------------------------------------------------------------------
    # UI CREATION
    # ------------------------------------------------------------------
    def create_widgets(self) -> None:
        # ---- Menubar ----
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Resources Folder...", command=self.change_resource_folder,
                              accelerator="Ctrl+Shift+F")
        file_menu.add_command(label="Refresh Tree", command=self.refresh, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Export Sprite (with adjustments)...", command=self.export_sprite,
                              accelerator="Ctrl+E")
        file_menu.add_command(label="Save Raw Crop...", command=self.save_raw_crop)
        file_menu.add_command(label="Save Modified Table Copy...", command=self.save_table_copy,
                              accelerator="Ctrl+S")
        file_menu.add_command(label="Batch Export Visible...", command=self.batch_export,
                              accelerator="Ctrl+B")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        menubar.add_cascade(label="File", menu=file_menu)

        # ---- Main pane ----
        self.main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        # ================== LEFT PANEL ==================
        left_frame = ttk.Frame(self.main_pane, width=255)
        self.main_pane.add(left_frame, weight=0)

        # Filter row
        flt = ttk.Frame(left_frame)
        flt.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4, 2))
        ttk.Label(flt, text="Filter:").pack(side=tk.LEFT)
        self.filter_entry = ttk.Entry(flt, textvariable=self.filter_text)
        self.filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(3, 0))

        # Sort row
        srt = ttk.Frame(left_frame)
        srt.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(0, 3))
        ttk.Label(srt, text="Sort:").pack(side=tk.LEFT)
        self.sort_combo = ttk.Combobox(
            srt, textvariable=self.sort_key,
            values=['Name','File','U','V','W','H','TW','TH','Flags','Area','Aspect'],
            state='readonly', width=8)
        self.sort_combo.pack(side=tk.LEFT, padx=(3, 0))
        ttk.Checkbutton(srt, text="Desc", variable=self.sort_desc).pack(side=tk.LEFT, padx=(3, 0))

        # Tree + scrollbar
        tree_frame = ttk.Frame(left_frame)
        tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tree_frame, selectmode='browse', show='tree')
        self.tree.heading('#0', text='Sprites', anchor='w')
        self.tree.tag_configure('modified', foreground='#f0c050', background='#3a3a20')
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.tree.bind("<Button-3>", self.on_tree_context_menu)

        self.tree_context = tk.Menu(self.root, tearoff=0)
        self.tree_context.add_command(label="Copy Name",       command=self.copy_sprite_name)
        self.tree_context.add_command(label="Copy File",       command=self.copy_sprite_file)
        self.tree_context.add_separator()
        self.tree_context.add_command(label="Open Texture",    command=self.open_image_file)
        self.tree_context.add_command(label="Open Folder",     command=self.open_file_location)
        self.tree_context.add_separator()
        self.tree_context.add_command(label="Export (adj)...", command=self.export_sprite)
        self.tree_context.add_command(label="Save Raw Crop...",command=self.save_raw_crop)

        # ================== RIGHT PANEL ==================
        right_pane = ttk.PanedWindow(self.main_pane, orient=tk.HORIZONTAL)
        self.main_pane.add(right_pane, weight=1)

        canvas_frame = ttk.Frame(right_pane)
        right_pane.add(canvas_frame, weight=1)

        # -- Compact toolbar --
        toolbar = ttk.Frame(canvas_frame)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=2, pady=2)

        for text, cmd in [("In", self.zoom_in), ("Out", self.zoom_out),
                          ("Fit", self.set_zoom_fit), ("100%", self.set_zoom_100),
                          ("Ctr", self.center_image)]:
            ttk.Button(toolbar, text=text, command=cmd, style="Toolbar.TButton", width=4).pack(side=tk.LEFT, padx=1)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=4, fill=tk.Y)
        self.zoom_label = ttk.Label(toolbar, text="100%", width=5, anchor="center")
        self.zoom_label.pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=4, fill=tk.Y)
        ttk.Checkbutton(toolbar, text="AA",   variable=self.antialias, command=self.update_display).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(toolbar, text="Grid", variable=self.grid_alpha, command=self.update_display).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="BG", command=self.choose_solid_color, style="Toolbar.TButton", width=3).pack(side=tk.LEFT, padx=1)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=4, fill=tk.Y)
        ttk.Button(toolbar, text="Export", command=self.export_sprite, style="Toolbar.TButton").pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="Raw",    command=self.save_raw_crop, style="Toolbar.TButton").pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="Batch",  command=self.batch_export, style="Toolbar.TButton").pack(side=tk.LEFT, padx=1)

        # -- Canvas + scrollbars --
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

        self.canvas.bind("<MouseWheel>",    self.on_mousewheel)
        self.canvas.bind("<Button-4>",      self.on_mousewheel)
        self.canvas.bind("<Button-5>",      self.on_mousewheel)
        self.canvas.bind("<ButtonPress-1>", self.on_pan_start)
        self.canvas.bind("<B1-Motion>",     self.on_pan_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_pan_end)
        self.canvas.bind("<Configure>",     lambda e: self.update_display())

        # ================== SIDE NOTEBOOK ==================
        side_notebook = ttk.Notebook(right_pane, width=255)
        right_pane.add(side_notebook, weight=0)

        # ---- Properties tab ----
        prop_frame = ttk.Frame(side_notebook)
        side_notebook.add(prop_frame, text="Properties")
        prop_frame.columnconfigure(0, weight=1)
        prop_frame.columnconfigure(1, weight=1)

        # File path + quick-open buttons
        pf = ttk.Frame(prop_frame)
        pf.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(5, 2))
        pf.columnconfigure(0, weight=1)
        self.file_path_var = tk.StringVar(value="")
        ttk.Entry(pf, textvariable=self.file_path_var, state='readonly').grid(row=0, column=0, sticky="ew")
        ttk.Button(pf, text="▶", command=self.open_image_file,  width=2).grid(row=0, column=1, padx=(2, 0))
        ttk.Button(pf, text="📂", command=self.open_file_location, width=2).grid(row=0, column=2, padx=(2, 0))

        ttk.Separator(prop_frame, orient=tk.HORIZONTAL).grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=3)

        # UVWH + TW/TH in compact 2-col grid
        self.prop_vars: Dict[str, tk.StringVar] = {}
        spinbox_fields = [
            (2, 0, "U:", "u"),  (2, 1, "V:", "v"),
            (3, 0, "W:", "w"),  (3, 1, "H:", "h"),
            (4, 0, "TW:", "tw"), (4, 1, "TH:", "th"),
        ]
        for row_i, col_i, lbl, key in spinbox_fields:
            f = ttk.Frame(prop_frame)
            f.grid(row=row_i, column=col_i, padx=(4, 2), pady=1, sticky="ew")
            ttk.Label(f, text=lbl, width=3, anchor="e").pack(side=tk.LEFT)
            var = tk.StringVar()
            self.prop_vars[key] = var
            sp = ttk.Spinbox(f, textvariable=var, from_=0, to=99999, increment=1, width=6)
            sp.pack(side=tk.LEFT, fill=tk.X, expand=True)
            def make_callback(k: str):
                def cb(*_):
                    if not self._updating_props:
                        self._schedule_property_update(k)
                return cb
            sp.bind("<KeyRelease>", make_callback(key))
            sp.bind("<FocusOut>", lambda e, k=key: self.on_property_edit(k, final=True))
            var.trace_add("write", make_callback(key))

        # Flags field (full width)
        ff = ttk.Frame(prop_frame)
        ff.grid(row=5, column=0, columnspan=2, padx=4, pady=1, sticky="ew")
        ttk.Label(ff, text="Flags:", width=5, anchor="e").pack(side=tk.LEFT)
        var = tk.StringVar()
        self.prop_vars['flags'] = var
        fl_ent = ttk.Entry(ff, textvariable=var)
        fl_ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
        def flags_callback(*_):
            if not self._updating_props:
                self._schedule_property_update('flags')
        fl_ent.bind("<KeyRelease>", flags_callback)
        fl_ent.bind("<FocusOut>",   lambda e: self.on_property_edit('flags', final=True))
        var.trace_add("write", flags_callback)

        # Pixel size info
        self.size_info_var = tk.StringVar(value="")
        ttk.Label(prop_frame, textvariable=self.size_info_var, foreground="#f0c050", font=("Segoe UI", 9, "bold")).grid(
            row=6, column=0, columnspan=2, padx=4, pady=(2, 0), sticky="w")

        ttk.Separator(prop_frame, orient=tk.HORIZONTAL).grid(row=7, column=0, columnspan=2, sticky="ew", padx=4, pady=4)

        # Action buttons - compact 2x2
        bf = ttk.Frame(prop_frame)
        bf.grid(row=8, column=0, columnspan=2, padx=4, pady=2, sticky="ew")
        bf.columnconfigure(0, weight=1)
        bf.columnconfigure(1, weight=1)
        ttk.Button(bf, text="Reset Props",  command=self.reset_properties).grid(row=0, column=0, padx=(0, 2), sticky="ew")
        ttk.Button(bf, text="Save Entry",   command=self.save_entry_to_table, style="Accent.TButton").grid(row=0, column=1, padx=(2, 0), sticky="ew")

        bf2 = ttk.Frame(prop_frame)
        bf2.grid(row=9, column=0, columnspan=2, padx=4, pady=(2, 5), sticky="ew")
        bf2.columnconfigure(0, weight=1)
        bf2.columnconfigure(1, weight=1)
        ttk.Button(bf2, text="Export Adj.", command=self.export_sprite).grid(row=0, column=0, padx=(0, 2), sticky="ew")
        ttk.Button(bf2, text="Raw Crop",    command=self.save_raw_crop).grid(row=0, column=1, padx=(2, 0), sticky="ew")

        # ---- Adjustments tab ----
        adj_frame = ttk.Frame(side_notebook)
        side_notebook.add(adj_frame, text="Adjust")
        adj_frame.columnconfigure(1, weight=1)

        sliders = [
            ("Bright",  self.brightness_var, 0.0,  3.0),
            ("Contrast",self.contrast_var,   0.0,  3.0),
            ("Saturate",self.saturation_var, 0.0,  3.0),
            ("Gamma",   self.gamma_var,      0.1,  5.0),
            ("Hue",     self.hue_var,       -180, 180),
        ]
        for i, (lbl, var, mn, mx) in enumerate(sliders):
            self._create_adj_widget(adj_frame, lbl, var, mn, mx, i)

        n = len(sliders)
        ttk.Separator(adj_frame, orient=tk.HORIZONTAL).grid(row=n, column=0, columnspan=3, sticky="ew", padx=6, pady=4)
        ttk.Checkbutton(adj_frame, text="Invert Colors", variable=self.invert_var).grid(row=n+1, column=0, columnspan=3, padx=6, sticky="w")
        ttk.Button(adj_frame, text="Reset All", command=self.reset_adjustments).grid(row=n+2, column=0, columnspan=3, padx=6, pady=(4, 6), sticky="ew")

        # ---- Save tab ----
        save_frame = ttk.Frame(side_notebook)
        side_notebook.add(save_frame, text="Save")
        self._create_save_tab(save_frame)

    # ------------------------------------------------------------------
    def _create_save_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        row = 0

        def section(text: str, r: int):
            ttk.Label(parent, text=text, foreground="#888888", font=("Segoe UI", 9, "bold")).grid(
                row=r, column=0, padx=6, pady=(8, 2), sticky="w")

        def btn(text: str, cmd: Callable, r: int, accent: bool = False):
            style = "Accent.TButton" if accent else "TButton"
            ttk.Button(parent, text=text, command=cmd, style=style).grid(
                row=r, column=0, padx=6, pady=2, sticky="ew")

        section("Current Sprite", row); row += 1
        btn("Export with Adjustments...",        self.export_sprite,              row); row += 1
        btn("Save Raw Crop (no adjustments)...", self.save_raw_crop,              row); row += 1
        btn("Copy Image to Clipboard",           self.copy_image_to_clipboard,    row); row += 1

        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(row=row, column=0, sticky="ew", padx=6, pady=5); row += 1

        section("Sprite Table", row); row += 1
        btn("Save Modified Entry to Table...",   self.save_entry_to_table,        row, accent=True); row += 1
        btn("Save Full Modified Table Copy...",  self.save_table_copy,            row, accent=True); row += 1

        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(row=row, column=0, sticky="ew", padx=6, pady=5); row += 1

        section("Batch Export", row); row += 1
        btn("Batch Export Visible Sprites...",   self.batch_export,               row); row += 1
        btn("Batch Export Current File Group...",self.batch_export_file_group,    row); row += 1

        ttk.Separator(parent, orient=tk.HORIZONTAL).grid(row=row, column=0, sticky="ew", padx=6, pady=5); row += 1

        self.mod_count_var = tk.StringVar(value="No modifications")
        ttk.Label(parent, textvariable=self.mod_count_var, foreground="#888888").grid(
            row=row, column=0, padx=6, pady=(2, 4), sticky="w")
        ttk.Button(parent, text="↺ Reset All Modifications", command=self.reset_all_modifications, style="TButton").grid(row=row+1, column=0, padx=6, pady=(0, 6), sticky="ew")

    def reset_all_modifications(self) -> None:
        if not self.modified_entries:
            return
        if messagebox.askyesno("Reset All", "Discard all unsaved modifications?"):
            self.modified_entries.clear()
            self.rebuild_tree()
            self.update_display()
            self.status.config(text="All modifications reset.")

    # ------------------------------------------------------------------
    def _create_adj_widget(self, parent: ttk.Frame, label: str, variable: tk.DoubleVar,
                          min_val: float, max_val: float, row_idx: int) -> None:
        ttk.Label(parent, text=label, width=8, anchor="e").grid(row=row_idx, column=0, padx=(6, 2), pady=2, sticky="e")
        scale = ttk.Scale(parent, from_=min_val, to=max_val, variable=variable, orient=tk.HORIZONTAL)
        scale.grid(row=row_idx, column=1, padx=2, pady=2, sticky="ew")
        val_lbl = ttk.Label(parent, width=5, anchor="w")
        val_lbl.grid(row=row_idx, column=2, padx=(2, 6), pady=2, sticky="w")
        def upd(*_):
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
    def on_tree_context_menu(self, event: tk.Event) -> None:
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.tree_context.tk_popup(event.x_root, event.y_root)

    def copy_sprite_name(self) -> None:
        if self.current_sprite:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_sprite['name'])

    def copy_sprite_file(self) -> None:
        if self.current_sprite:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_sprite['file'])

    def load_sprite_table(self) -> None:
        try:
            entries = parse_sprite_table(self.sprite_table_path)
        except Exception as e:
            logger.error(f"Parse failed: {e}")
            messagebox.showerror("Error", f"Failed to parse sprite table:\n{e}")
            return
        self.sprite_entries = entries
        self.file_groups = {}
        for ent in entries:
            self.file_groups.setdefault(ent['file'].lower(), []).append(ent)
        self.rebuild_tree()
        self.status.config(text=f"Loaded {len(entries)} sprites from {len(self.file_groups)} files.")

    def _sort_key_func(self, key_name: str, desc: bool) -> Callable[[Dict], Any]:
        key_map = {
            'Name':   lambda e: e['name'].lower(),
            'File':   lambda e: e['file'].lower(),
            'U':      lambda e: e['u'],
            'V':      lambda e: e['v'],
            'W':      lambda e: e['w'],
            'H':      lambda e: e['h'],
            'TW':     lambda e: e['tw'],
            'TH':     lambda e: e['th'],
            'Flags':  lambda e: e['flags'],
            'Area':   lambda e: e['w'] * e['h'],
            'Aspect': lambda e: (e['w'] / e['h']) if e['h'] != 0 else 0.0,
        }
        base_func = key_map.get(key_name, key_map['Name'])
        if desc:
            return lambda e: (-base_func(e) if isinstance(base_func(e), (int, float)) else base_func(e))
        return base_func

    def rebuild_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        filter_lower = self.filter_text.get().lower()
        sort_name = self.sort_key.get()
        desc = self.sort_desc.get()

        for fname in sorted(self.file_groups.keys()):
            file_entries = self.file_groups[fname]
            if filter_lower:
                file_entries = [e for e in file_entries if filter_lower in e['name'].lower()]
            if not file_entries:
                continue

            file_node = self.tree.insert('', 'end', text=f"{fname} ({len(file_entries)})", values=('file', fname))

            def build_hierarchy(entries: List[Dict]) -> Dict:
                root_node = {"sprite_entries": [], "subdirs": {}}
                for ent in entries:
                    parts = re.split(r'[\\/]', ent['name'])
                    cur = root_node
                    for part in parts[:-1]:
                        if part not in cur['subdirs']:
                            cur['subdirs'][part] = {"sprite_entries": [], "subdirs": {}}
                        cur = cur['subdirs'][part]
                    cur['sprite_entries'].append((parts[-1], ent))
                return root_node

            def populate_tree(parent_node: str, node: Dict, file_key: str) -> None:
                for subdir in sorted(node['subdirs'].keys()):
                    sub_node = self.tree.insert(parent_node, 'end', text=subdir, values=('folder',))
                    populate_tree(sub_node, node['subdirs'][subdir], file_key)
                key_func = self._sort_key_func(sort_name, desc)
                for sprite_name, ent in sorted(node['sprite_entries'], key=lambda x: key_func(x[1])):
                    is_mod = (file_key, ent['name']) in self.modified_entries
                    tag = ('modified',) if is_mod else ()
                    self.tree.insert(parent_node, 'end', text=sprite_name, values=('sprite', ent['name'], file_key), tags=tag)

            hierarchy = build_hierarchy(file_entries)
            populate_tree(file_node, hierarchy, fname)

        for item in self.tree.get_children():
            self.tree.item(item, open=True)

    # ------------------------------------------------------------------
    # IMAGE LOADING
    # ------------------------------------------------------------------
    def get_image(self, file_name_lower: str) -> Optional[Image.Image]:
        cached = self.image_cache.get(file_name_lower)
        if cached is not None:
            return cached
        if file_name_lower not in self.file_paths:
            self.file_paths[file_name_lower] = find_image_file(self.resources_path, file_name_lower)
        original_path = self.file_paths.get(file_name_lower)
        if original_path is None:
            self.image_cache.put(file_name_lower, None)
            return None
        try:
            img = Image.open(original_path).convert("RGBA")
            self.image_cache.put(file_name_lower, img)
            return img
        except Exception as e:
            logger.warning(f"Load failed {original_path}: {e}")
            if os.path.isfile(TEXCONV_PATH):
                self.status.config(text=f"Converting {file_name_lower}...")
                self.root.update_idletasks()
                png_path = texconv_convert(original_path, CACHE_DIR)
                if png_path:
                    try:
                        img = Image.open(png_path).convert("RGBA")
                        self.image_cache.put(file_name_lower, img)
                        self.file_paths[file_name_lower] = png_path
                        self.status.config(text=f"Converted {file_name_lower}")
                        return img
                    except Exception as e2:
                        logger.error(f"Converted load failed: {e2}")
        self.image_cache.put(file_name_lower, None)
        return None

    def get_sprite_image(self, entry: Dict[str, Any]) -> Optional[Image.Image]:
        if entry is None:
            return None
        file_key = entry['file'].lower()
        source_img = self.get_image(file_key)
        if source_img is None:
            return None
        img_w, img_h = source_img.size
        tw, th = entry['tw'], entry['th']
        u, v, w, h = entry['u'], entry['v'], entry['w'], entry['h']
        left   = round(u * img_w / tw) if tw > 0 else 0
        top    = round(v * img_h / th) if th > 0 else 0
        right  = round((u + w) * img_w / tw) if tw > 0 else img_w
        bottom = round((v + h) * img_h / th) if th > 0 else img_h
        left   = max(0, min(left, img_w))
        top    = max(0, min(top, img_h))
        right  = max(0, min(right, img_w))
        bottom = max(0, min(bottom, img_h))
        if right <= left or bottom <= top:
            return None
        return source_img.crop((left, top, right, bottom))

    def apply_adjustments(self, img: Image.Image) -> Image.Image:
        if img is None:
            return None
        im = img.copy()
        b, c, s = self.brightness_var.get(), self.contrast_var.get(), self.saturation_var.get()
        if b != 1.0: im = ImageEnhance.Brightness(im).enhance(b)
        if c != 1.0: im = ImageEnhance.Contrast(im).enhance(c)
        if s != 1.0: im = ImageEnhance.Color(im).enhance(s)

        g = self.gamma_var.get()
        if g != 1.0:
            inv_g = 1.0 / g
            table = [int(255 * (i / 255) ** inv_g) for i in range(256)]
            if im.mode == 'RGBA':
                r, g_ch, b_ch, a = im.split()
                im = Image.merge('RGBA', (r.point(table), g_ch.point(table), b_ch.point(table), a))
            else:
                im = im.point(table)

        hue = self.hue_var.get()
        if hue != 0.0:
            hsv = im.convert('HSV')
            h_ch, s_v, v_ch = hsv.split()
            shift = int(hue * 255 / 360.0)
            h_ch = h_ch.point(lambda p: (p + shift) % 256)
            im = Image.merge('HSV', (h_ch, s_v, v_ch)).convert('RGBA')

        if self.invert_var.get():
            if im.mode == 'RGBA':
                r, g_ch, b_ch, a = im.split()
                im = Image.merge('RGBA', (ImageOps.invert(r), ImageOps.invert(g_ch), ImageOps.invert(b_ch), a))
            else:
                im = ImageOps.invert(im)
        return im

    def get_active_entry(self) -> Optional[Dict[str, Any]]:
        if self.current_sprite is None:
            return None
        key = (self.current_sprite['file'].lower(), self.current_sprite['name'])
        return self.modified_entries.get(key, self.current_sprite)

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
            self._draw_checkerboard(cw, ch)
        else:
            self.canvas.configure(bg=self.solid_color)

        if hasattr(self, 'zoom_label'):
            self.zoom_label.configure(text=f"{int(self.zoom_factor * 100)}%")

        if self.current_sprite is None:
            self.status.config(text="No sprite selected.")
            return

        entry = self.get_active_entry()
        sprite_img = self.get_sprite_image(entry)
        if sprite_img is None:
            self.canvas.create_text(cw / 2, ch / 2, text="Image not found or unsupported format", fill="red", font=("", 12, "bold"))
            self.status.config(text=f"Missing: {entry['file']}")
            return

        adjusted = self.apply_adjustments(sprite_img)
        if adjusted is None:
            return

        new_w = max(1, int(adjusted.width * self.zoom_factor))
        new_h = max(1, int(adjusted.height * self.zoom_factor))
        filt = Image.NEAREST if not self.antialias.get() else Image.LANCZOS
        resized = adjusted.resize((new_w, new_h), filt)
        self._tk_image = ImageTk.PhotoImage(resized)
        self.canvas.create_image(self.pan_x, self.pan_y, anchor='nw', image=self._tk_image)
        self.canvas.configure(scrollregion=(0, 0, max(new_w, cw), max(new_h, ch)))

        if hasattr(self, 'size_info_var'):
            self.size_info_var.set(f"{sprite_img.width} × {sprite_img.height} px")
        if hasattr(self, 'mod_count_var'):
            mc = len(self.modified_entries)
            self.mod_count_var.set(f"{mc} modification{'s' if mc != 1 else ''}" if mc else "No modifications")

        self.status.config(text=f"{entry['name']} | {sprite_img.width}×{sprite_img.height}px | Zoom: {int(self.zoom_factor * 100)}% | {entry['file']}")

    def _draw_checkerboard(self, width: int, height: int) -> None:
        self.canvas.delete("checker")
        sq = 16
        for y in range(0, height, sq):
            for x in range(0, width, sq):
                color = "#555555" if ((x // sq) + (y // sq)) % 2 == 0 else "#2b2b2b"
                self.canvas.create_rectangle(x, y, x + sq, y + sq, fill=color, outline='', tags="checker")
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
        if not self.current_sprite:
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
        self.zoom_factor = min(self.zoom_factor * 1.2, 16.0)
        self.update_display()

    def zoom_out(self) -> None:
        self.zoom_mode = "custom"
        self.zoom_factor = max(self.zoom_factor / 1.2, 0.1)
        self.update_display()

    def center_image(self) -> None:
        if not self.current_sprite:
            return
        img = self.get_sprite_image(self.get_active_entry())
        if img is None:
            return
        adj = self.apply_adjustments(img)
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 2 or ch < 2:
            return
        self.pan_x = (cw - adj.width * self.zoom_factor) / 2
        self.pan_y = (ch - adj.height * self.zoom_factor) / 2
        self.update_display()

    def on_pan_start(self, event: tk.Event) -> None:
        self._pan_start_x = event.x
        self._pan_start_y = event.y
        self._pan_orig_x = self.pan_x
        self._pan_orig_y = self.pan_y

    def on_pan_move(self, event: tk.Event) -> None:
        self.pan_x = self._pan_orig_x + (event.x - self._pan_start_x)
        self.pan_y = self._pan_orig_y + (event.y - self._pan_start_y)
        self.update_display()

    def on_pan_end(self, event: tk.Event) -> None:
        pass

    def on_mousewheel(self, event: tk.Event) -> None:
        delta = event.delta if event.delta else (120 if event.num == 4 else -120 if event.num == 5 else 0)
        if not delta:
            return
        factor = 1.1 if delta > 0 else 0.9
        new_zoom = max(0.1, min(self.zoom_factor * factor, 16.0))
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        x = cx - self.pan_x
        y = cy - self.pan_y
        self.pan_x = cx - x * (new_zoom / self.zoom_factor)
        self.pan_y = cy - y * (new_zoom / self.zoom_factor)
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
    def on_tree_select(self, event: Optional[tk.Event]) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], 'values')
        if not values or values[0] != 'sprite':
            return
        sprite_name = values[1]
        file_key = values[2]
        entry = next((e for e in self.file_groups.get(file_key, []) if e['name'] == sprite_name), None)
        if entry:
            key = (file_key, sprite_name)
            self.current_sprite = self.modified_entries.get(key, entry)
            self.update_properties_panel()
            self.apply_zoom_mode()

    def update_properties_panel(self) -> None:
        if not self.current_sprite:
            self.clear_properties()
            return
        self._updating_props = True
        try:
            entry = self.get_active_entry()
            file_key = entry['file'].lower()
            if file_key not in self.file_paths:
                self.file_paths[file_key] = find_image_file(self.resources_path, file_key)
            path = self.file_paths.get(file_key)
            self.file_path_var.set(path if path else "Not found")
            for key in ['u', 'v', 'w', 'h', 'tw', 'th', 'flags']:
                var = self.prop_vars.get(key)
                if var:
                    var.set(str(entry[key]))
        finally:
            self._updating_props = False

    def clear_properties(self) -> None:
        self._updating_props = True
        try:
            self.file_path_var.set("")
            for var in self.prop_vars.values():
                var.set("")
            if hasattr(self, 'size_info_var'):
                self.size_info_var.set("")
        finally:
            self._updating_props = False

    def _schedule_property_update(self, key: str) -> None:
        if self._edit_after_id:
            self.root.after_cancel(self._edit_after_id)
        self._edit_after_id = self.root.after(150, lambda: self.on_property_edit(key, final=True))

    def on_property_edit(self, key: str, final: bool = False) -> None:
        if self._updating_props or self.current_sprite is None:
            return
        orig = self.current_sprite
        mod_key = (orig['file'].lower(), orig['name'])
        if mod_key not in self.modified_entries:
            self.modified_entries[mod_key] = dict(orig)
        mod_entry = self.modified_entries[mod_key]
        var = self.prop_vars.get(key)
        if not var:
            return
        value_str = var.get().strip()
        if key != 'flags':
            try:
                mod_entry[key] = int(value_str)
            except ValueError:
                return
        else:
            mod_entry['flags'] = value_str
        self.current_sprite = mod_entry
        if final:
            self.update_display()

    def reset_properties(self) -> None:
        if self.current_sprite is None:
            return
        key = (self.current_sprite['file'].lower(), self.current_sprite['name'])
        if key in self.modified_entries:
            del self.modified_entries[key]
        orig = next((e for e in self.file_groups.get(key[0], []) if e['name'] == key[1]), None)
        if orig:
            self.current_sprite = orig
            self.update_properties_panel()
            self.update_display()
            self.rebuild_tree()

    # ------------------------------------------------------------------
    # SAVE / EXPORT
    # ------------------------------------------------------------------
    def export_sprite(self) -> None:
        if not self.current_sprite:
            return
        raw = self.get_sprite_image(self.get_active_entry())
        if raw is None:
            messagebox.showerror("Error", "Cannot export — image not available.")
            return
        adjusted = self.apply_adjustments(raw)
        name_clean = re.sub(r'[\\/:]', '_', self.current_sprite['name'])
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("TGA", "*.tga"), ("BMP", "*.bmp"), ("All files", "*.*")],
            initialfile=f"{name_clean}.png",
            title="Export Sprite with Adjustments")
        if path:
            try:
                adjusted.save(path)
                self.status.config(text=f"Exported: {os.path.basename(path)}")
            except Exception as e:
                logger.error(f"Export failed: {e}")
                messagebox.showerror("Export failed", str(e))

    def save_raw_crop(self) -> None:
        if not self.current_sprite:
            return
        raw = self.get_sprite_image(self.get_active_entry())
        if raw is None:
            messagebox.showerror("Error", "Cannot save — image not available.")
            return
        name_clean = re.sub(r'[\\/:]', '_', self.current_sprite['name'])
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("TGA", "*.tga"), ("BMP", "*.bmp"), ("All files", "*.*")],
            initialfile=f"{name_clean}_raw.png",
            title="Save Raw Sprite Crop (no adjustments)")
        if path:
            try:
                raw.save(path)
                self.status.config(text=f"Saved raw crop: {os.path.basename(path)}")
            except Exception as e:
                logger.error(f"Save failed: {e}")
                messagebox.showerror("Save failed", str(e))

    def copy_image_to_clipboard(self) -> None:
        if not self.current_sprite:
            return
        raw = self.get_sprite_image(self.get_active_entry())
        if raw is None:
            messagebox.showwarning("Not available", "No image to copy.")
            return
        adjusted = self.apply_adjustments(raw)
        try:
            if platform.system() == "Windows":
                try:
                    import win32clipboard
                    bg = Image.new("RGB", adjusted.size, (128, 128, 128))
                    mask = adjusted.split()[3] if adjusted.mode == 'RGBA' else None
                    bg.paste(adjusted, mask=mask)
                    buf = io.BytesIO()
                    bg.save(buf, format='BMP')
                    data = buf.getvalue()[14:]
                    buf.close()
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                    win32clipboard.CloseClipboard()
                    self.status.config(text="Image copied to clipboard.")
                    return
                except ImportError:
                    logger.info("win32clipboard not available, using fallback")
            tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            adjusted.save(tmp.name)
            tmp.close()
            self.root.clipboard_clear()
            self.root.clipboard_append(tmp.name)
            self.status.config(text=f"Temp path copied: {tmp.name}")
        except Exception as e:
            logger.error(f"Clipboard error: {e}")
            messagebox.showerror("Clipboard error", str(e))

    def save_entry_to_table(self) -> None:
        if not self.current_sprite:
            messagebox.showinfo("Nothing to save", "No sprite selected.")
            return
        key = (self.current_sprite['file'].lower(), self.current_sprite['name'])
        if key not in self.modified_entries:
            messagebox.showinfo("Nothing to save", "No modifications on current sprite.\nEdit U/V/W/H/TW/TH/Flags first.")
            return
        self.save_table_copy(only_key=key)

    def save_table_copy(self, only_key: Optional[Tuple[str, str]] = None) -> None:
        if not self.sprite_table_path:
            return
        if not self.modified_entries:
            messagebox.showinfo("Nothing to save", "No modifications have been made.")
            return

        mods = ({only_key: self.modified_entries[only_key]} if only_key and only_key in self.modified_entries else self.modified_entries)
        if not mods:
            messagebox.showinfo("Nothing to save", "No applicable modifications.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="sprite_modified.txt",
            title="Save Modified Sprite Table Copy")
        if not path:
            return

        try:
            with open(self.sprite_table_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            mod_lookup = {name: entry for (_, name), entry in mods.items()}
            PATTERN = re.compile(r'^"([^"]+)"\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+)')
            out = []
            for line in lines:
                stripped = line.strip()
                m = PATTERN.match(stripped)
                if m and m.group(1) in mod_lookup:
                    e = mod_lookup[m.group(1)]
                    indent = ' ' * (len(line) - len(line.lstrip()))
                    out.append(f'{indent}"{e["name"]}" {e["file"]} {e["u"]} {e["v"]} {e["w"]} {e["h"]} {e["tw"]} {e["th"]} {e["flags"]}\n')
                else:
                    out.append(line)
            with open(path, 'w', encoding='utf-8') as f:
                f.writelines(out)
            mc = len(mods)
            msg = f"Saved with {mc} modification{'s' if mc != 1 else ''}:\n{os.path.basename(path)}"
            self.status.config(text=f"Table saved: {os.path.basename(path)}")
            messagebox.showinfo("Saved", msg)
        except Exception as e:
            logger.error(f"Save table failed: {e}")
            messagebox.showerror("Save failed", str(e))

    def batch_export(self) -> None:
        filter_lower = self.filter_text.get().lower()
        to_export = [e for entries in self.file_groups.values() for e in entries if not filter_lower or filter_lower in e['name'].lower()]
        if not to_export:
            messagebox.showinfo("Nothing", "No sprites match the current filter.")
            return
        self._do_batch_export(to_export)

    def batch_export_file_group(self) -> None:
        if not self.current_sprite:
            messagebox.showinfo("No selection", "Select a sprite first.")
            return
        file_key = self.current_sprite['file'].lower()
        entries = self.file_groups.get(file_key, [])
        if not entries:
            messagebox.showinfo("Nothing", "No sprites in current file group.")
            return
        self._do_batch_export(entries)

    def _do_batch_export(self, entries: List[Dict[str, Any]]) -> None:
        folder = filedialog.askdirectory(title=f"Select output folder for {len(entries)} sprites")
        if not folder:
            return
        apply_adj = messagebox.askyesno("Apply Adjustments?", "Apply current brightness/contrast/gamma/etc. to exported sprites?")

        # Progress dialog
        progress_win = tk.Toplevel(self.root)
        progress_win.title("Batch Export")
        progress_win.geometry("300x100")
        progress_win.transient(self.root)
        progress_win.grab_set()
        ttk.Label(progress_win, text="Exporting...").pack(pady=10)
        pb = ttk.Progressbar(progress_win, mode='determinate', maximum=len(entries))
        pb.pack(pady=5, padx=20, fill=tk.X)
        status_lbl = ttk.Label(progress_win, text="0 / 0")
        status_lbl.pack()
        progress_win.update()

        success = fail = 0
        for i, e in enumerate(entries):
            try:
                img = self.get_sprite_image(e)
                if img is None:
                    fail += 1
                else:
                    if apply_adj:
                        img = self.apply_adjustments(img)
                    name_clean = re.sub(r'[\\/:]', '_', e['name'])
                    img.save(os.path.join(folder, f"{name_clean}.png"))
                    success += 1
            except Exception as ex:
                logger.error(f"Batch export error [{e['name']}]: {ex}")
                fail += 1
            pb['value'] = i + 1
            status_lbl.config(text=f"{i+1} / {len(entries)}")
            progress_win.update()

        progress_win.destroy()
        self.status.config(text=f"Batch done: {success} exported, {fail} failed.")
        messagebox.showinfo("Batch Export Done", f"Exported {success} sprite{'s' if success != 1 else ''}.\n{fail} failed.\n\nOutput folder:\n{folder}")

    # ------------------------------------------------------------------
    # FILE OPEN HELPERS
    # ------------------------------------------------------------------
    def open_image_file(self) -> None:
        if not self.current_sprite:
            return
        path = self.file_paths.get(self.current_sprite['file'].lower())
        if path and os.path.isfile(path):
            self._open_file_with_default(path)
        else:
            messagebox.showwarning("Not found", "Image file not found on disk.")

    def open_file_location(self) -> None:
        if not self.current_sprite:
            return
        path = self.file_paths.get(self.current_sprite['file'].lower())
        if path and os.path.isfile(path):
            self._open_file_explorer(path)
        else:
            messagebox.showwarning("Not found", "Image file not found on disk.")

    def _open_file_with_default(self, path: str) -> None:
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", path], check=True)
            else:
                subprocess.run(["xdg-open", path], check=True)
        except Exception as e:
            logger.error(f"Open failed: {e}")

    def _open_file_explorer(self, path: str) -> None:
        try:
            if platform.system() == "Windows":
                subprocess.run(["explorer", "/select,", path], check=True)
            elif platform.system() == "Darwin":
                subprocess.run(["open", os.path.dirname(path)], check=True)
            else:
                subprocess.run(["xdg-open", os.path.dirname(path)], check=True)
        except Exception as e:
            logger.error(f"Explorer open failed: {e}")

    def change_resource_folder(self) -> None:
        self.ask_resource_folder()
        if self.resources_path and self.sprite_table_path:
            self.refresh()


# ----------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SpriteViewer(root)
    root.mainloop()