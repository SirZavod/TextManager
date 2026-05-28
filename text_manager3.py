import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

# --- HIGH DPI / 4K MONITOR FIX ---
try:
    if sys.platform.startswith('win'):
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass
# ---------------------------------

# ============================================================
#  THEME DEFINITIONS
# ============================================================
THEMES = {
    "light": {
        "bg":            "#f0f0f0",
        "panel_bg":      "#f0f0f0",
        "canvas_bg":     "#ffffff",
        "row_bg":        "#ffffff",
        "row_changed":   "#fff8c0",   # yellow
        "row_saved":     "#d4edda",   # green
        "row_error":     "#f8d7da",   # red
        "entry_bg":      "#ffffff",
        "entry_fg":      "#1a1a1a",
        "label_fg":      "#1a1a1a",
        "label_accent":  "#1a4a8a",
        "listbox_bg":    "#f9f9f9",
        "listbox_fg":    "#333333",
        "listbox_sel":   "#4a90e2",
        "img_canvas_bg": "#e1e1e1",
        "statusbar_bg":  "#dcdcdc",
        "statusbar_fg":  "#333333",
        "sep_color":     "#cccccc",
        "theme_btn_txt": "🌙 Dark",
    },
    "dark": {
        "bg":            "#000000",
        "panel_bg":      "#111111",
        "canvas_bg":     "#121212",
        "row_bg":        "#1e1e1e",
        "row_changed":   "#3a3000",
        "row_saved":     "#0a2a0a",
        "row_error":     "#2a0a0a",
        "entry_bg":      "#1e1e1e",
        "entry_fg":      "#e8e8e8",
        "label_fg":      "#e8e8e8",
        "label_accent":  "#a0c4ff",
        "listbox_bg":    "#1a1a1a",
        "listbox_fg":    "#e0e0e0",
        "listbox_sel":   "#4a90e2",
        "img_canvas_bg": "#1a1a1a",
        "statusbar_bg":  "#0a0a0a",
        "statusbar_fg":  "#aaaaaa",
        "sep_color":     "#333333",
        "theme_btn_txt": "☀️ Light",
    }
}

FONT_SIZE_DEFAULT = 11
FONT_SIZE_MIN     = 8
FONT_SIZE_MAX     = 24
FONT_SIZE_STEP    = 1


class TextManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Text Manager")
        self.root.geometry("1200x780")
        self.root.minsize(950, 550)

        # ---- data ----
        self.text_cache      = {}
        self.disk_snapshots  = {}
        self.saved_set       = set()   # fnames saved to output this session
        self.file_data       = []
        self.entry_widgets   = {}   # fname -> ttk.Entry
        self.row_frames      = {}   # fname -> tk.Frame  (for colour updates)

        # Img+Txt
        self.image_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')
        self.image_list       = []
        self.current_img_index = -1
        self.tk_img           = None

        # UI state
        self.current_theme    = "light"
        self.font_size        = FONT_SIZE_DEFAULT
        # Lists of plain tk widgets that need manual bg updates on theme change
        self.plain_frames     = []   # list of tk.Frame
        self.plain_buttons    = []   # list of (tk.Button, role) where role in ("panel","canvas")

        self.setup_ui()
        self.bind_shortcuts()
        self.apply_theme(self.current_theme)

    # ============================================================
    #  UI CONSTRUCTION
    # ============================================================
    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')

        # ---- root grid so status bar stays at bottom ----
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)
        self.root.columnconfigure(0, weight=1)

        # ---- main paned window ----
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 4))

        # ======== LEFT PANEL ========
        left_frame = ttk.Frame(main_paned, width=320, padding=10)
        main_paned.add(left_frame, weight=1)

        # Theme toggle (top-right of left panel)
        top_bar = tk.Frame(left_frame)
        top_bar.pack(fill=tk.X, pady=(0, 4))
        self.plain_frames.append(top_bar)
        ttk.Label(top_bar, text="Select Mode:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, anchor=tk.W)
        self.btn_theme = tk.Button(top_bar, text="🌙 Dark", width=10,
                                   relief=tk.FLAT, cursor="hand2",
                                   command=self.toggle_theme)
        self.btn_theme.pack(side=tk.RIGHT)

        mode_frame = ttk.Frame(left_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 12))
        self.mode_var = tk.StringVar(value="batch")
        self.btn_mode1 = ttk.Radiobutton(mode_frame, text="1: Batch",
                                          variable=self.mode_var, value="batch",
                                          command=self.switch_mode, style="Toolbutton")
        self.btn_mode1.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        self.btn_mode2 = ttk.Radiobutton(mode_frame, text="2: Img+Txt",
                                          variable=self.mode_var, value="img_txt",
                                          command=self.switch_mode, style="Toolbutton")
        self.btn_mode2.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))

        # Input folder
        ttk.Label(left_frame, text="Input folder (source files):",
                  font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0, 4))
        in_path_frame = ttk.Frame(left_frame)
        in_path_frame.pack(fill=tk.X, pady=(0, 8))
        self.in_path_entry = ttk.Entry(in_path_frame)
        self.in_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(in_path_frame, text="Select...", command=self.browse_input).pack(side=tk.RIGHT)
        self._bind_drag_drop(self.in_path_entry)

        # Output folder
        ttk.Label(left_frame, text="Output folder (save):",
                  font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(4, 4))
        out_path_frame = ttk.Frame(left_frame)
        out_path_frame.pack(fill=tk.X, pady=(0, 12))
        self.out_path_entry = ttk.Entry(out_path_frame)
        self.out_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(out_path_frame, text="Select...", command=self.browse_output).pack(side=tk.RIGHT)
        self._bind_drag_drop(self.out_path_entry)

        # Sorting
        ttk.Label(left_frame, text="File Sorting:",
                  font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(4, 4))
        self.sort_var = tk.StringVar(value="name")
        ttk.Radiobutton(left_frame, text="By filename",
                        variable=self.sort_var, value="name").pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(left_frame, text="By date of change",
                        variable=self.sort_var, value="date").pack(anchor=tk.W, padx=5, pady=(0, 12))

        # Import
        self.btn_import = ttk.Button(left_frame, text="📥 IMPORT FILES",
                                     command=self.import_files)
        self.btn_import.pack(fill=tk.X, ipady=6, pady=(0, 12))

        # Font size controls
        font_ctrl_frame = tk.Frame(left_frame)
        font_ctrl_frame.pack(fill=tk.X, pady=(0, 8))
        self.plain_frames.append(font_ctrl_frame)
        ttk.Label(font_ctrl_frame, text="Text size:", font=('Arial', 9)).pack(side=tk.LEFT)
        self.lbl_font_size = ttk.Label(font_ctrl_frame,
                                        text=str(self.font_size),
                                        font=('Arial', 9, 'bold'), width=3)
        self.lbl_font_size.pack(side=tk.LEFT, padx=4)
        self.btn_font_minus = tk.Button(font_ctrl_frame, text="−", width=2, relief=tk.FLAT, cursor="hand2",
                  command=lambda: self.change_font_size(-FONT_SIZE_STEP))
        self.btn_font_minus.pack(side=tk.LEFT, padx=2)
        self.btn_font_plus = tk.Button(font_ctrl_frame, text="+", width=2, relief=tk.FLAT, cursor="hand2",
                  command=lambda: self.change_font_size(+FONT_SIZE_STEP))
        self.btn_font_plus.pack(side=tk.LEFT, padx=2)
        self.plain_buttons.extend([(self.btn_font_minus, "panel"), (self.btn_font_plus, "panel")])

        # File list
        self.lbl_found_files = ttk.Label(left_frame, text="Found files:",
                                          font=('Arial', 9, 'italic'))
        self.lbl_found_files.pack(anchor=tk.W)
        self.files_listbox = tk.Listbox(left_frame, height=12,
                                         bg="#f9f9f9", fg="#333333",
                                         selectbackground="#4a90e2")
        self.files_listbox.pack(fill=tk.BOTH, expand=True, pady=(5, 12))
        self.files_listbox.bind('<<ListboxSelect>>', self.on_listbox_select)

        # Export
        self.btn_export = ttk.Button(left_frame, text="💾 EXPORT EDITS",
                                     command=self.export_files, state=tk.DISABLED)
        self.btn_export.pack(fill=tk.X, ipady=10)

        # ======== RIGHT PANEL ========
        self.right_container = ttk.Frame(main_paned, padding=10)
        main_paned.add(self.right_container, weight=3)

        # ---- BATCH FRAME ----
        self.batch_layout_frame = ttk.Frame(self.right_container)

        # Header row: title + search bar
        self.batch_header = tk.Frame(self.batch_layout_frame)
        batch_header = self.batch_header
        batch_header.pack(fill=tk.X, pady=(0, 5))
        self.plain_frames.append(batch_header)
        ttk.Label(batch_header, text="File Content Editor (Line-by-Line):",
                  font=('Arial', 11, 'bold')).pack(side=tk.LEFT)

        # Search bar (right side of header)
        search_bar = tk.Frame(batch_header)
        search_bar.pack(side=tk.RIGHT)
        self.plain_frames.append(search_bar)
        ttk.Label(search_bar, text="🔍 Filter:").pack(side=tk.LEFT, padx=(0, 4))
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", self._on_filter_change)
        self.filter_entry = ttk.Entry(search_bar, textvariable=self.filter_var, width=24)
        self.filter_entry.pack(side=tk.LEFT, padx=(0, 4))
        self.filter_color_var = tk.StringVar(value="#ffe066")
        self.color_btn = tk.Button(search_bar, text="Color", font=('Arial', 9),
                                   relief=tk.GROOVE, cursor="hand2", padx=6,
                                   command=self._pick_highlight_color)
        self.color_btn.pack(side=tk.LEFT, padx=2)
        self.plain_buttons.append((self.color_btn, "panel"))
        ttk.Button(search_bar, text="✕ Clear", width=8,
                   command=lambda: self.filter_var.set("")).pack(side=tk.LEFT, padx=2)

        self.work_frame = ttk.Frame(self.batch_layout_frame, relief=tk.SUNKEN, borderwidth=1)
        self.work_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.canvas = tk.Canvas(self.work_frame, borderwidth=0,
                                highlightthickness=0, bg="#ffffff")
        self.scrollbar = ttk.Scrollbar(self.work_frame, orient="vertical",
                                       command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#ffffff")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Batch Replace Panel
        replace_frame = ttk.LabelFrame(self.batch_layout_frame,
                                       text=" Batch Replace Panel ", padding=10)
        replace_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        ttk.Label(replace_frame, text="Search for:").grid(row=0, column=0,
                                                           sticky=tk.W, padx=5, pady=5)
        self.search_entry = ttk.Entry(replace_frame, width=22)
        self.search_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(replace_frame, text="Replace to:").grid(row=0, column=2,
                                                           sticky=tk.W, padx=5, pady=5)
        self.replace_entry = ttk.Entry(replace_frame, width=22)
        self.replace_entry.grid(row=0, column=3, padx=5, pady=5)
        self.btn_replace = ttk.Button(replace_frame, text="🔄 Apply the replacement",
                                      command=self.apply_mass_replace, state=tk.DISABLED)
        self.btn_replace.grid(row=0, column=4, padx=15, pady=5)

        # ---- IMG+TXT FRAME ----
        self.img_txt_layout_frame = ttk.Frame(self.right_container)

        self.lbl_img_filename = ttk.Label(self.img_txt_layout_frame, text="FILENAME.png",
                                           font=('Arial', 12, 'bold'), anchor=tk.CENTER)
        self.lbl_img_filename.pack(fill=tk.X, pady=(0, 5))

        self.img_view_frame = ttk.Frame(self.img_txt_layout_frame,
                                        relief=tk.SUNKEN, borderwidth=1)
        self.img_view_frame.pack(fill=tk.BOTH, expand=True)

        self.img_canvas = tk.Canvas(self.img_view_frame, bg="#e1e1e1",
                                    highlightthickness=0, takefocus=True)
        self.img_canvas.pack(fill=tk.BOTH, expand=True)
        self.img_canvas.bind("<Configure>", self.on_img_canvas_configure)
        # Clicking the image canvas grabs focus so arrow keys work immediately
        self.img_canvas.bind("<Button-1>", lambda e: self.img_canvas.focus_set())

        self.lbl_txt_filename = ttk.Label(self.img_txt_layout_frame, text="FILENAME.txt",
                                           font=('Arial', 10, 'italic'), anchor=tk.CENTER)
        self.lbl_txt_filename.pack(fill=tk.X, pady=(10, 5))

        self.prompt_text_frame = ttk.Frame(self.img_txt_layout_frame)
        self.prompt_text_frame.pack(fill=tk.X, pady=(0, 8))

        self.prompt_text = tk.Text(self.prompt_text_frame, height=6,
                                   font=('Arial', self.font_size), wrap=tk.WORD)
        self.prompt_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._bind_context_menu(self.prompt_text)

        pt_scroll = ttk.Scrollbar(self.prompt_text_frame, orient="vertical",
                                  command=self.prompt_text.yview)
        pt_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.prompt_text.configure(yscrollcommand=pt_scroll.set)

        nav_frame = ttk.Frame(self.img_txt_layout_frame, padding=5)
        nav_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(nav_frame, text="💾 SAVE",
                   command=self.save_current_img_txt).pack(side=tk.LEFT, padx=5)
        ttk.Label(nav_frame, text="PREV IMAGE (F1 / ⬅)",
                  font=('Arial', 10, 'bold')).pack(side=tk.LEFT, expand=True)
        ttk.Label(nav_frame, text="NEXT IMAGE (F2 / ➡)",
                  font=('Arial', 10, 'bold')).pack(side=tk.RIGHT, expand=True)

        # ======== STATUS BAR ========
        self.statusbar = tk.Frame(self.root, height=22)
        self.statusbar.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
        self.statusbar.columnconfigure(0, weight=1)

        self.lbl_status = tk.Label(self.statusbar, text="Ready.",
                                   anchor=tk.W, font=('Arial', 9))
        self.lbl_status.grid(row=0, column=0, sticky="ew", padx=8)

        self.switch_mode()

    # ============================================================
    #  THEME
    # ============================================================
    def toggle_theme(self):
        new = "dark" if self.current_theme == "light" else "light"
        self.apply_theme(new)

    def apply_theme(self, theme_name):
        self.current_theme = theme_name
        t = THEMES[theme_name]

        style = ttk.Style()
        style.configure("TFrame",       background=t["panel_bg"])
        style.configure("TLabel",       background=t["panel_bg"], foreground=t["label_fg"])
        style.configure("TLabelframe",  background=t["panel_bg"])
        style.configure("TLabelframe.Label", background=t["panel_bg"], foreground=t["label_fg"])
        style.configure("TRadiobutton", background=t["panel_bg"], foreground=t["label_fg"])
        style.configure("TCheckbutton", background=t["panel_bg"], foreground=t["label_fg"])
        style.configure("TSeparator",   background=t["sep_color"])
        style.configure("Toolbutton",   background=t["panel_bg"], foreground=t["label_fg"])
        style.map("Toolbutton",
                  background=[("selected", t["listbox_sel"]), ("active", t["canvas_bg"])],
                  foreground=[("selected", "#ffffff"),        ("active", t["label_fg"])])
        style.configure("TPanedwindow", background=t["bg"])
        style.configure("Sash",         sashpad=4, relief=tk.FLAT, sashrelief=tk.FLAT)
        style.configure("Vertical.TScrollbar", background=t["panel_bg"],
                        troughcolor=t["canvas_bg"], arrowcolor=t["label_fg"])
        style.configure("TButton",      background=t["panel_bg"], foreground=t["label_fg"])
        style.map("TButton",
                  background=[("active", t["canvas_bg"]), ("disabled", t["panel_bg"])],
                  foreground=[("disabled", t["sep_color"])])

        self.root.configure(bg=t["bg"])
        self.statusbar.configure(bg=t["statusbar_bg"])
        self.lbl_status.configure(bg=t["statusbar_bg"], fg=t["statusbar_fg"])

        self.canvas.configure(bg=t["canvas_bg"])
        self.scrollable_frame.configure(bg=t["canvas_bg"])
        self.img_canvas.configure(bg=t["img_canvas_bg"])

        self.files_listbox.configure(bg=t["listbox_bg"], fg=t["listbox_fg"],
                                      selectbackground=t["listbox_sel"])

        self.btn_theme.configure(text=t["theme_btn_txt"],
                                  bg=t["panel_bg"], fg=t["label_fg"],
                                  activebackground=t["canvas_bg"],
                                  activeforeground=t["label_fg"])

        self.prompt_text.configure(bg=t["entry_bg"], fg=t["entry_fg"],
                                   insertbackground=t["entry_fg"])

        # Repaint all batch rows (row bg + labels + buttons + entries)
        for fname in list(self.row_frames.keys()):
            self._update_row_color(fname)

        self._refresh_batch_row_widgets()

        # Paint all registered plain tk.Frame widgets
        for frame in self.plain_frames:
            try:
                frame.configure(bg=t["panel_bg"])
            except tk.TclError:
                pass

        # Paint registered plain tk.Button widgets
        for btn, role in self.plain_buttons:
            bg = t["panel_bg"] if role == "panel" else t["canvas_bg"]
            try:
                btn.configure(bg=bg, fg=t["label_fg"],
                              activebackground=t["canvas_bg"],
                              activeforeground=t["label_fg"])
            except tk.TclError:
                pass

        # Global ttk.Entry field colour (applies to all ttk.Entry via named style)
        style = ttk.Style()
        style.configure("TEntry",
                        fieldbackground=t["entry_bg"],
                        foreground=t["entry_fg"],
                        insertcolor=t["entry_fg"])

        # Re-apply active filter so highlight colour is not wiped by theme repaint
        if hasattr(self, 'filter_var') and self.filter_var.get().strip():
            self._on_filter_change()

    def _refresh_batch_row_widgets(self):
        """Re-apply colours to ALL child widgets inside batch rows after theme switch."""
        t = THEMES[self.current_theme]
        for fname, row_frame in self.row_frames.items():
            try:
                current  = self.text_cache.get(fname, "").strip()
                original = self.disk_snapshots.get(fname, "").strip()
                if fname in self.saved_set and current != original:
                    row_bg = t["row_saved"]
                elif current != original:
                    row_bg = t["row_changed"]
                else:
                    row_bg = t["row_bg"]

                for child in row_frame.winfo_children():
                    if isinstance(child, tk.Label):
                        is_accent = '[' in child.cget("text")
                        child.configure(bg=row_bg,
                                        fg=t["label_accent"] if is_accent else t["label_fg"])
                    elif isinstance(child, tk.Button):
                        child.configure(bg=row_bg, fg=t["label_fg"],
                                        activebackground=t["canvas_bg"],
                                        activeforeground=t["label_fg"])
                    elif isinstance(child, ttk.Entry):
                        child.configure(foreground=t["entry_fg"],
                                        fieldbackground=t["entry_bg"])
            except tk.TclError:
                pass

    # ============================================================
    #  FONT SIZE
    # ============================================================
    def change_font_size(self, delta):
        new_size = max(FONT_SIZE_MIN, min(FONT_SIZE_MAX, self.font_size + delta))
        if new_size == self.font_size:
            return
        self.font_size = new_size
        self.lbl_font_size.configure(text=str(self.font_size))
        # Update prompt_text
        self.prompt_text.configure(font=('Arial', self.font_size))
        # Update all batch entries
        for ent in self.entry_widgets.values():
            try:
                ent.configure(font=('Arial', self.font_size))
            except tk.TclError:
                pass

    def _on_ctrl_mousewheel(self, event):
        if event.state & 0x0004:   # Ctrl held
            delta = FONT_SIZE_STEP if event.delta > 0 else -FONT_SIZE_STEP
            self.change_font_size(delta)
            return "break"

    # ============================================================
    #  DRAG & DROP (Windows explorer → Entry field)
    # ============================================================
    def _bind_drag_drop(self, entry_widget):
        """Try to enable drag-and-drop for folder paths. Requires tkinterdnd2 (optional)."""
        try:
            from tkinterdnd2 import DND_FILES
            entry_widget.drop_target_register(DND_FILES)
            def _drop(event):
                path = event.data.strip().strip('{}')
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, path)
            entry_widget.dnd_bind('<<Drop>>', _drop)
        except Exception:
            pass  # tkinterdnd2 not installed — silently skip

    # ============================================================
    #  CONTEXT MENU
    # ============================================================
    def _bind_context_menu(self, widget):
        menu = tk.Menu(widget, tearoff=0)
        is_text = isinstance(widget, tk.Text)

        def do_cut():
            try: widget.event_generate("<<Cut>>")
            except tk.TclError: pass

        def do_copy():
            try: widget.event_generate("<<Copy>>")
            except tk.TclError: pass

        def do_paste():
            try: widget.event_generate("<<Paste>>")
            except tk.TclError: pass

        def do_select_all():
            if is_text:
                widget.tag_add(tk.SEL, "1.0", tk.END)
            else:
                widget.select_range(0, tk.END)
            widget.focus_set()

        menu.add_command(label="Cut",        command=do_cut)
        menu.add_command(label="Copy",       command=do_copy)
        menu.add_command(label="Paste",      command=do_paste)
        menu.add_separator()
        menu.add_command(label="Select All", command=do_select_all)

        def show_menu(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        widget.bind("<Button-3>", show_menu)

    # ============================================================
    #  SHORTCUTS
    # ============================================================
    def bind_shortcuts(self):
        self.root.bind("<F1>",         lambda e: self.navigate_img(-1))
        self.root.bind("<F2>",         lambda e: self.navigate_img(1))
        # Use keycode-based binding so arrows work regardless of keyboard layout (RU/EN/JP)
        self.root.bind("<KeyPress>",   self._on_key_press)
        self.root.bind("<MouseWheel>", self._on_ctrl_mousewheel)

    # Windows virtual-key codes for arrow keys (layout-independent)
    _VK_LEFT  = 37
    _VK_RIGHT = 39

    def _is_text_widget_focused(self):
        focused = self.root.focus_get()
        if focused is None:
            return False
        return isinstance(focused, (tk.Text, ttk.Entry, tk.Entry))

    def _on_key_press(self, event):
        """Handle arrow keys by keycode so RU/JP layouts work correctly."""
        kc = event.keycode
        if kc == self._VK_LEFT:
            if not self._is_text_widget_focused():
                self.navigate_img(-1)
        elif kc == self._VK_RIGHT:
            if not self._is_text_widget_focused():
                self.navigate_img(1)

    # Keep legacy named bindings as no-ops (prevents default Tk behaviour conflicts)
    def _on_left_arrow(self, event):
        pass

    def _on_right_arrow(self, event):
        pass

    # ============================================================
    #  SEARCH / FILTER (Batch)
    # ============================================================
    def _on_filter_change(self, *_):
        query = self.filter_var.get().strip().lower()
        t = THEMES[self.current_theme]
        hl_color = self.filter_color_var.get()

        for fname, row_frame in self.row_frames.items():
            try:
                if query and query in fname.lower():
                    row_frame.configure(bg=hl_color)
                    for child in row_frame.winfo_children():
                        if isinstance(child, tk.Label):
                            child.configure(bg=hl_color)
                elif query and self.text_cache.get(fname, "").lower().find(query) != -1:
                    row_frame.configure(bg=hl_color)
                    for child in row_frame.winfo_children():
                        if isinstance(child, tk.Label):
                            child.configure(bg=hl_color)
                else:
                    self._update_row_color(fname)
            except tk.TclError:
                pass

    def _pick_highlight_color(self):
        from tkinter.colorchooser import askcolor
        color = askcolor(color=self.filter_color_var.get(),
                         title="Pick highlight colour")[1]
        if color:
            self.filter_color_var.set(color)
            self._on_filter_change()

    # ============================================================
    #  ROW COLOUR MANAGEMENT
    # ============================================================
    def _update_row_color(self, fname):
        """Sets row background based on change state (uses in-memory saved_set)."""
        if fname not in self.row_frames:
            return
        t = THEMES[self.current_theme]
        row_frame = self.row_frames[fname]

        current  = self.text_cache.get(fname, "").strip()
        original = self.disk_snapshots.get(fname, "").strip()

        if fname in self.saved_set and current != original:
            bg = t["row_saved"]
        elif current != original:
            bg = t["row_changed"]
        else:
            bg = t["row_bg"]

        try:
            row_frame.configure(bg=bg)
            for child in row_frame.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=bg)
        except tk.TclError:
            pass

    def _mark_row_saved(self, fname):
        if fname not in self.row_frames:
            return
        t = THEMES[self.current_theme]
        row_frame = self.row_frames[fname]
        try:
            row_frame.configure(bg=t["row_saved"])
            for child in row_frame.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=t["row_saved"])
        except tk.TclError:
            pass

    def _mark_row_error(self, fname):
        if fname not in self.row_frames:
            return
        t = THEMES[self.current_theme]
        row_frame = self.row_frames[fname]
        try:
            row_frame.configure(bg=t["row_error"])
            for child in row_frame.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=t["row_error"])
        except tk.TclError:
            pass

    # ============================================================
    #  STATUS BAR
    # ============================================================
    def _update_status(self):
        total     = len(self.file_data) if self.mode_var.get() == "batch" else len(self.image_list)
        changed   = 0
        saved     = len(self.saved_set)

        for fname, current in self.text_cache.items():
            original = self.disk_snapshots.get(fname, "")
            if current.strip() != original.strip():
                changed += 1

        mode_label = "Batch" if self.mode_var.get() == "batch" else "Img+Txt"
        self.lbl_status.configure(
            text=f"Mode: {mode_label}  │  Files: {total}  │  "
                 f"Modified: {changed}  │  Saved: {saved}")

    # ============================================================
    #  CACHE HELPERS
    # ============================================================
    def save_batch_fields_to_cache(self):
        for fname, entry_widget in self.entry_widgets.items():
            try:
                if entry_widget.winfo_exists():
                    self.text_cache[fname] = entry_widget.get()
            except tk.TclError:
                pass

    def save_img_txt_field_to_cache(self):
        if self.image_list and self.current_img_index >= 0:
            img_path = self.image_list[self.current_img_index]
            txt_name = os.path.splitext(os.path.basename(img_path))[0] + ".txt"
            self.text_cache[txt_name] = self.prompt_text.get("1.0", tk.END).strip()

    # ============================================================
    #  AUTO OUTPUT FOLDER
    # ============================================================
    def _resolve_output_dir(self):
        """Returns output path. Auto-creates '<input>-output' if field is empty."""
        out_dir = self.out_path_entry.get().strip()
        if out_dir:
            return out_dir

        in_dir = self.in_path_entry.get().strip()
        if not in_dir:
            messagebox.showerror("Error", "Specify the Output folder (or set an Input folder for auto-naming).")
            return None

        parent  = os.path.dirname(in_dir.rstrip("/\\"))
        folder  = os.path.basename(in_dir.rstrip("/\\"))
        auto    = os.path.join(parent, folder + "-output")

        if os.path.exists(auto):
            messagebox.showerror(
                "Output folder exists",
                f"Auto output folder already exists:\n{auto}\n\n"
                "Please specify a different Output folder manually.")
            return None

        try:
            os.makedirs(auto)
        except Exception as e:
            messagebox.showerror("Error", f"Could not create output folder:\n{e}")
            return None

        self.out_path_entry.delete(0, tk.END)
        self.out_path_entry.insert(0, auto)
        return auto

    # ============================================================
    #  MODE SWITCH
    # ============================================================
    def switch_mode(self):
        current_mode = self.mode_var.get()

        if current_mode == "batch":
            self.save_img_txt_field_to_cache()
            self.img_txt_layout_frame.pack_forget()
            self.batch_layout_frame.pack(fill=tk.BOTH, expand=True)
            self.btn_export.config(state=tk.NORMAL if self.file_data else tk.DISABLED)
            self.lbl_found_files.config(text="Found .txt files:")
            for fname, entry_widget in self.entry_widgets.items():
                if fname in self.text_cache:
                    entry_widget.delete(0, tk.END)
                    entry_widget.insert(0, self.text_cache[fname])
        else:
            self.save_batch_fields_to_cache()
            if self.check_unsaved_changes() == "cancel":
                self.mode_var.set("batch")
                return
            self.batch_layout_frame.pack_forget()
            self.img_txt_layout_frame.pack(fill=tk.BOTH, expand=True)
            self.btn_export.config(state=tk.DISABLED)
            self.lbl_found_files.config(text="Found image files:")

        self.refresh_listbox()
        self._update_status()

    # ============================================================
    #  SCROLL / CANVAS
    # ============================================================
    def _on_mousewheel(self, event):
        if event.state & 0x0004:   # Ctrl — font zoom
            return
        if self.mode_var.get() == "batch":
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    # ============================================================
    #  BROWSE
    # ============================================================
    def browse_input(self):
        path = filedialog.askdirectory()
        if path:
            self.in_path_entry.delete(0, tk.END)
            self.in_path_entry.insert(0, path)

    def browse_output(self):
        path = filedialog.askdirectory()
        if path:
            self.out_path_entry.delete(0, tk.END)
            self.out_path_entry.insert(0, path)

    # ============================================================
    #  IMPORT
    # ============================================================
    def import_files(self):
        in_dir = self.in_path_entry.get().strip()
        if not in_dir or not os.path.exists(in_dir):
            messagebox.showerror("Error", "Please specify an existing input folder!")
            return

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.file_data      = []
        self.entry_widgets  = {}
        self.row_frames     = {}
        self.image_list     = []
        self.text_cache     = {}
        self.disk_snapshots = {}
        self.saved_set      = set()
        self.current_img_index = -1
        self.filter_var.set("")

        try:
            all_files = os.listdir(in_dir)
        except Exception as e:
            messagebox.showerror("Error", f"Unable to read files: {e}")
            return

        if self.sort_var.get() == "name":
            def sort_key_name(x):
                stem = os.path.splitext(x)[0]
                try:
                    return (0, int(stem), "")
                except ValueError:
                    return (1, 0, stem.lower())
            all_files.sort(key=sort_key_name)
        else:
            all_files.sort(
                key=lambda x: os.path.getmtime(os.path.join(in_dir, x)),
                reverse=True)

        txt_files = [f for f in all_files if f.lower().endswith('.txt')]
        img_files = [f for f in all_files if f.lower().endswith(self.image_extensions)]

        for fname in txt_files:
            fpath   = os.path.join(in_dir, fname)
            content = ""
            for enc in ['utf-8', 'cp1251', 'latin-1']:
                try:
                    with open(fpath, 'r', encoding=enc) as f:
                        content = f.read().rstrip('\r\n')
                    break
                except UnicodeDecodeError:
                    continue
            self.text_cache[fname]     = content
            self.disk_snapshots[fname] = content
            self.file_data.append({'name': fname, 'content': content})

        for fname in img_files:
            self.image_list.append(os.path.join(in_dir, fname))
            t_name = os.path.splitext(fname)[0] + ".txt"
            if t_name not in self.disk_snapshots:
                self.disk_snapshots[t_name] = ""
                self.text_cache[t_name]     = ""

        t = THEMES[self.current_theme]

        for item in self.file_data:
            fname     = item['name']
            row_frame = tk.Frame(self.scrollable_frame, bg=t["row_bg"], pady=3)
            row_frame.pack(fill=tk.X, expand=True, padx=5)
            self.row_frames[fname] = row_frame

            # 💾 per-row save button
            save_btn = tk.Button(
                row_frame, text="💾", width=2, relief=tk.FLAT, cursor="hand2",
                bg=t["row_bg"], fg=t["label_fg"],
                activebackground=t["canvas_bg"],
                command=lambda fn=fname: self._save_single_row(fn))
            save_btn.pack(side=tk.LEFT, padx=(4, 2))

            lbl = tk.Label(row_frame, text=f"[{fname}]", width=14,
                           font=('Courier', 10, 'bold'),
                           bg=t["row_bg"], fg=t["label_accent"])
            lbl.pack(side=tk.LEFT, padx=(2, 6))

            arrow_lbl = tk.Label(row_frame, text="−",
                                 bg=t["row_bg"], fg=t["label_fg"])
            arrow_lbl.pack(side=tk.LEFT, padx=(0, 6))

            ent = ttk.Entry(row_frame, font=('Arial', self.font_size))
            ent.insert(0, item['content'])
            ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
            self._bind_context_menu(ent)
            ent.bind("<KeyRelease>", lambda e, fn=fname: self._on_entry_edit(fn))

            self.entry_widgets[fname] = ent

            sep = ttk.Separator(self.scrollable_frame, orient=tk.HORIZONTAL)
            sep.pack(fill=tk.X, padx=5, pady=1)

        if self.file_data or self.image_list:
            self.btn_replace.config(state=tk.NORMAL)
            if self.mode_var.get() == "batch" and self.file_data:
                self.btn_export.config(state=tk.NORMAL)
            if self.image_list:
                self.current_img_index = 0
            self.refresh_listbox()
            messagebox.showinfo(
                "Success",
                f"Loaded: {len(txt_files)} text files, {len(img_files)} images.")
        else:
            messagebox.showinfo("Information", "No matching files found.")

        self._update_status()

    def _on_entry_edit(self, fname):
        """Called on every keystroke in a batch entry — updates cache + row colour."""
        ent = self.entry_widgets.get(fname)
        if ent:
            self.text_cache[fname] = ent.get()
        self._update_row_color(fname)
        self._update_status()

    # ============================================================
    #  PER-ROW SAVE
    # ============================================================
    def _save_single_row(self, fname):
        out_dir = self._resolve_output_dir()
        if not out_dir:
            return

        in_dir = self.in_path_entry.get().strip()
        if os.path.abspath(in_dir) == os.path.abspath(out_dir):
            messagebox.showerror("Error", "Input and output folders are the SAME!")
            return

        # Sync entry → cache first
        ent = self.entry_widgets.get(fname)
        if ent and ent.winfo_exists():
            self.text_cache[fname] = ent.get()

        content = self.text_cache.get(fname, "")
        out_path = os.path.join(out_dir, fname)
        try:
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.disk_snapshots[fname] = content
            self.saved_set.add(fname)
            self._mark_row_saved(fname)
            self._update_status()
        except Exception as e:
            self._mark_row_error(fname)
            messagebox.showerror("Error", f"Could not save {fname}:\n{e}")

    # ============================================================
    #  LISTBOX / REFRESH
    # ============================================================
    def refresh_listbox(self):
        self.files_listbox.delete(0, tk.END)
        if self.mode_var.get() == "batch":
            for item in self.file_data:
                self.files_listbox.insert(tk.END, item['name'])
        else:
            for path in self.image_list:
                self.files_listbox.insert(tk.END, os.path.basename(path))
            if self.current_img_index >= 0:
                self.files_listbox.activate(self.current_img_index)
                self.load_current_image_data()

    def on_listbox_select(self, event):
        selection = self.files_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        if self.mode_var.get() == "img_txt":
            if index != self.current_img_index:
                self.save_img_txt_field_to_cache()
                if self.check_unsaved_changes() == "cancel":
                    self.files_listbox.selection_clear(0, tk.END)
                    self.files_listbox.selection_set(self.current_img_index)
                    return
                self.current_img_index = index
                self.load_current_image_data()

    # ============================================================
    #  IMG+TXT LOGIC
    # ============================================================
    def load_current_image_data(self):
        if not self.image_list or self.current_img_index < 0:
            return
        img_path  = self.image_list[self.current_img_index]
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        txt_name  = base_name + ".txt"

        self.lbl_img_filename.config(text=os.path.basename(img_path))
        self.lbl_txt_filename.config(text=txt_name)

        txt_content = self.text_cache.get(txt_name, "")
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert(tk.END, txt_content)

        self.files_listbox.selection_clear(0, tk.END)
        self.files_listbox.selection_set(self.current_img_index)
        self.files_listbox.see(self.current_img_index)

        self.display_image()
        self._update_status()

    def display_image(self):
        if not self.image_list or self.current_img_index < 0:
            return
        img_path = self.image_list[self.current_img_index]
        try:
            img      = Image.open(img_path)
            canvas_w = self.img_canvas.winfo_width()
            canvas_h = self.img_canvas.winfo_height()
            if canvas_w < 10: canvas_w = 500
            if canvas_h < 10: canvas_h = 350

            img_w, img_h = img.size
            ratio  = min(canvas_w / img_w, canvas_h / img_h)
            new_w  = max(1, int(img_w * ratio))
            new_h  = max(1, int(img_h * ratio))

            img_resized  = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.tk_img  = ImageTk.PhotoImage(img_resized)

            self.img_canvas.delete("all")
            self.img_canvas.create_image(
                canvas_w // 2, canvas_h // 2,
                anchor=tk.CENTER, image=self.tk_img)
        except Exception as e:
            self.img_canvas.delete("all")
            self.img_canvas.create_text(
                50, 50, text=f"Error displaying image:\n{e}",
                fill="red", anchor=tk.NW)

    def on_img_canvas_configure(self, event):
        self.display_image()

    def navigate_img(self, direction):
        if self.mode_var.get() != "img_txt" or not self.image_list:
            return
        self.save_img_txt_field_to_cache()
        if self.check_unsaved_changes() == "cancel":
            return
        new_index = self.current_img_index + direction
        if 0 <= new_index < len(self.image_list):
            self.current_img_index = new_index
            self.load_current_image_data()

    def check_unsaved_changes(self):
        if self.current_img_index < 0:
            return "no_change"
        img_path = self.image_list[self.current_img_index]
        txt_name = os.path.splitext(os.path.basename(img_path))[0] + ".txt"
        current  = self.text_cache.get(txt_name, "").strip()
        original = self.disk_snapshots.get(txt_name, "").strip()
        if current != original:
            ans = messagebox.askyesnocancel(
                "Save Changes",
                f"Save changes? {txt_name} will be saved to the output folder.")
            if ans is True:
                return "saved" if self.save_current_img_txt() else "cancel"
            elif ans is False:
                self.text_cache[txt_name] = original
                return "ignored"
            else:
                return "cancel"
        return "no_change"

    def save_current_img_txt(self):
        out_dir = self._resolve_output_dir()
        if not out_dir:
            return False
        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create output folder: {e}")
                return False

        img_path = self.image_list[self.current_img_index]
        txt_name = os.path.splitext(os.path.basename(img_path))[0] + ".txt"
        content  = self.text_cache.get(txt_name, "").strip()

        if not content and not self.disk_snapshots.get(txt_name):
            return True

        out_file_path = os.path.join(out_dir, txt_name)
        try:
            with open(out_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.disk_snapshots[txt_name] = content
            self.saved_set.add(txt_name)
            self._update_status()
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Unable to save {txt_name}: {e}")
            return False

    # ============================================================
    #  BATCH REPLACE
    # ============================================================
    def apply_mass_replace(self):
        search_str  = self.search_entry.get()
        replace_str = self.replace_entry.get()
        if not search_str:
            messagebox.showwarning("Error", "The 'Search for' field must not be blank!")
            return

        self.save_batch_fields_to_cache()
        count = 0
        for fname in list(self.text_cache.keys()):
            current = self.text_cache[fname]
            if search_str in current:
                self.text_cache[fname] = current.replace(search_str, replace_str)
                count += 1

        if self.mode_var.get() == "batch":
            for fname, entry_widget in self.entry_widgets.items():
                if fname in self.text_cache:
                    entry_widget.delete(0, tk.END)
                    entry_widget.insert(0, self.text_cache[fname])
                self._update_row_color(fname)

        self._update_status()
        messagebox.showinfo("Success", f"Replaced in {count} file(s).")

    # ============================================================
    #  EXPORT ALL
    # ============================================================
    def export_files(self):
        in_dir  = self.in_path_entry.get().strip()
        out_dir = self._resolve_output_dir()
        if not out_dir:
            return
        if in_dir and os.path.abspath(in_dir) == os.path.abspath(out_dir):
            messagebox.showerror("Error", "Input and output folders are the SAME!")
            return
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        self.save_batch_fields_to_cache()
        success_count = 0

        for fname, content in self.text_cache.items():
            if content.strip() != self.disk_snapshots.get(fname, "").strip():
                out_file_path = os.path.join(out_dir, fname)
                try:
                    with open(out_file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.disk_snapshots[fname] = content
                    self.saved_set.add(fname)
                    self._mark_row_saved(fname)
                    success_count += 1
                except Exception as e:
                    self._mark_row_error(fname)
                    print(f"Error saving {fname}: {e}")

        self._update_status()
        messagebox.showinfo("Success",
                            f"Saved {success_count} modified file(s) to:\n{out_dir}")


# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    app  = TextManagerApp(root)
    root.mainloop()
