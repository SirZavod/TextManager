import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

# --- HIGH DPI / 4K MONITOR FIX ---
# This ensures crisp text and UI elements on high-resolution displays
try:
    if sys.platform.startswith('win'):
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass  # Fallback if the OS doesn't support DPI scaling settings via ctypes
# ---------------------------------

class TextManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Text Manager")
        self.root.geometry("1150x750")
        self.root.minsize(950, 550)
        
        # GLOBAL DATA CACHE (Shared between both modes)
        self.text_cache = {}        # Holds current texts: {'name.txt': 'current text'}
        self.disk_snapshots = {}    # Holds pristine disk contents for change tracking: {'name.txt': 'original'}
        self.file_data = []         # List to maintain file order in Batch mode
        self.entry_widgets = {}     # Entry widgets for Batch mode
        
        # Img+Txt Mode Data
        self.image_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')
        self.image_list = []        # Full paths to images
        self.current_img_index = -1
        self.tk_img = None          # Reference to the current PhotoImage object for Canvas
        
        self.setup_ui()
        self.bind_shortcuts()
        
    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main Layout split container
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # --- LEFT PANEL (CONTROL SIDE) ---
        left_frame = ttk.Frame(main_paned, width=320, padding=10)
        main_paned.add(left_frame, weight=1)
        
        # MODE SELECTION (Tabs 1 and 2)
        ttk.Label(left_frame, text="Select Mode:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0,2))
        mode_frame = ttk.Frame(left_frame)
        mode_frame.pack(fill=tk.X, pady=(0,15))
        
        self.mode_var = tk.StringVar(value="batch")
        self.btn_mode1 = ttk.Radiobutton(mode_frame, text="1: Batch", variable=self.mode_var, value="batch", command=self.switch_mode, style="Toolbutton")
        self.btn_mode1.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        self.btn_mode2 = ttk.Radiobutton(mode_frame, text="2: Img+Txt", variable=self.mode_var, value="img_txt", command=self.switch_mode, style="Toolbutton")
        self.btn_mode2.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2,0))
        
        # Input folder
        ttk.Label(left_frame, text="Input folder (source files):", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0,5))
        in_path_frame = ttk.Frame(left_frame)
        in_path_frame.pack(fill=tk.X, pady=(0,10))
        self.in_path_entry = ttk.Entry(in_path_frame)
        self.in_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        ttk.Button(in_path_frame, text="Select...", command=self.browse_input).pack(side=tk.RIGHT)
        
        # Output folder
        ttk.Label(left_frame, text="Output folder (save):", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(5,5))
        out_path_frame = ttk.Frame(left_frame)
        out_path_frame.pack(fill=tk.X, pady=(0,15))
        self.out_path_entry = ttk.Entry(out_path_frame)
        self.out_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        ttk.Button(out_path_frame, text="Select...", command=self.browse_output).pack(side=tk.RIGHT)
        
        # Sorting
        ttk.Label(left_frame, text="File Sorting:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(5,5))
        self.sort_var = tk.StringVar(value="name")
        ttk.Radiobutton(left_frame, text="By filename", variable=self.sort_var, value="name").pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(left_frame, text="By date of change", variable=self.sort_var, value="date").pack(anchor=tk.W, padx=5, pady=(0,15))
        
        # Import Button
        self.btn_import = ttk.Button(left_frame, text="📥 IMPORT FILES", command=self.import_files)
        self.btn_import.pack(fill=tk.X, ipady=6, pady=(0,15))
        
        # File list box
        self.lbl_found_files = ttk.Label(left_frame, text="Found files:", font=('Arial', 9, 'italic'))
        self.lbl_found_files.pack(anchor=tk.W)
        self.files_listbox = tk.Listbox(left_frame, height=12, bg="#f9f9f9", fg="#333333", selectbackground="#4a90e2")
        self.files_listbox.pack(fill=tk.BOTH, expand=True, pady=(5,15))
        self.files_listbox.bind('<<ListboxSelect>>', self.on_listbox_select)
        
        # Export Button (Active for Batch mode processing)
        self.btn_export = ttk.Button(left_frame, text="💾 EXPORT EDITS", command=self.export_files, state=tk.DISABLED)
        self.btn_export.pack(fill=tk.X, ipady=10)
        
        # --- RIGHT PANEL (WORKSPACE WORK VIEW) ---
        self.right_container = ttk.Frame(main_paned, padding=10)
        main_paned.add(self.right_container, weight=3)
        
        # 1. BATCH MODE LAYOUT FRAME
        self.batch_layout_frame = ttk.Frame(self.right_container)
        
        ttk.Label(self.batch_layout_frame, text="File Content Editor (Line-by-Line):", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(0,5))
        
        self.work_frame = ttk.Frame(self.batch_layout_frame, relief=tk.SUNKEN, borderwidth=1)
        self.work_frame.pack(fill=tk.BOTH, expand=True, pady=(0,10))
        
        self.canvas = tk.Canvas(self.work_frame, borderwidth=0, highlightthickness=0, bg="#ffffff")
        self.scrollbar = ttk.Scrollbar(self.work_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#ffffff")
        
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Mass Replace Panel
        replace_frame = ttk.LabelFrame(self.batch_layout_frame, text=" Batch Replace Panel ", padding=10)
        replace_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(5,0))
        ttk.Label(replace_frame, text="Search for:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.search_entry = ttk.Entry(replace_frame, width=22)
        self.search_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(replace_frame, text="Replace to:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.replace_entry = ttk.Entry(replace_frame, width=22)
        self.replace_entry.grid(row=0, column=3, padx=5, pady=5)
        self.btn_replace = ttk.Button(replace_frame, text="🔄 Apply the replacement", command=self.apply_mass_replace, state=tk.DISABLED)
        self.btn_replace.grid(row=0, column=4, padx=15, pady=5)
        
        # 2. IMG+TXT MODE LAYOUT FRAME
        self.img_txt_layout_frame = ttk.Frame(self.right_container)
        
        self.lbl_img_filename = ttk.Label(self.img_txt_layout_frame, text="FILENAME.png", font=('Arial', 12, 'bold'), anchor=tk.CENTER)
        self.lbl_img_filename.pack(fill=tk.X, pady=(0,5))
        
        self.img_view_frame = ttk.Frame(self.img_txt_layout_frame, relief=tk.SUNKEN, borderwidth=1)
        self.img_view_frame.pack(fill=tk.BOTH, expand=True)
        
        self.img_canvas = tk.Canvas(self.img_view_frame, bg="#e1e1e1", highlightthickness=0)
        self.img_canvas.pack(fill=tk.BOTH, expand=True)
        self.img_canvas.bind("<Configure>", self.on_img_canvas_configure)
        
        self.lbl_txt_filename = ttk.Label(self.img_txt_layout_frame, text="FILENAME.txt", font=('Arial', 10, 'italic'), anchor=tk.CENTER)
        self.lbl_txt_filename.pack(fill=tk.X, pady=(10,5))
        
        self.prompt_text_frame = ttk.Frame(self.img_txt_layout_frame)
        self.prompt_text_frame.pack(fill=tk.X, pady=(0,10))
        
        self.prompt_text = tk.Text(self.prompt_text_frame, height=6, font=('Arial', 11), wrap=tk.WORD)
        self.prompt_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        pt_scroll = ttk.Scrollbar(self.prompt_text_frame, orient="vertical", command=self.prompt_text.yview)
        pt_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.prompt_text.configure(yscrollcommand=pt_scroll.set)
        
        nav_frame = ttk.Frame(self.img_txt_layout_frame, padding=5)
        nav_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Button(nav_frame, text="💾 SAVE", command=self.save_current_img_txt).pack(side=tk.LEFT, padx=5)
        ttk.Label(nav_frame, text="PREV IMAGE (F1 / ⬅)", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, expand=True)
        ttk.Label(nav_frame, text="NEXT IMAGE (F2 / ➡)", font=('Arial', 10, 'bold')).pack(side=tk.RIGHT, expand=True)
        
        self.switch_mode()

    def bind_shortcuts(self):
        self.root.bind("<F1>", lambda e: self.navigate_img(-1))
        self.root.bind("<F2>", lambda e: self.navigate_img(1))
        self.root.bind("<Left>", lambda e: self.navigate_img(-1))
        self.root.bind("<Right>", lambda e: self.navigate_img(1))

    def save_batch_fields_to_cache(self):
        """Saves current content from Batch mode entry fields into memory text cache"""
        for fname, entry_widget in self.entry_widgets.items():
            if os.path.exists(entry_widget.winfo_id()):
                self.text_cache[fname] = entry_widget.get()

    def save_img_txt_field_to_cache(self):
        """Saves current content from Img+Txt Text frame into memory text cache"""
        if self.image_list and self.current_img_index >= 0:
            img_path = self.image_list[self.current_img_index]
            txt_name = os.path.splitext(os.path.basename(img_path))[0] + ".txt"
            self.text_cache[txt_name] = self.prompt_text.get("1.0", tk.END).strip()

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

    def _on_mousewheel(self, event):
        if self.mode_var.get() == "batch":
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        
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

    def import_files(self):
        in_dir = self.in_path_entry.get().strip()
        if not in_dir or not os.path.exists(in_dir):
            messagebox.showerror("Error", "Please specify an existing input folder!")
            return
            
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.file_data = []
        self.entry_widgets = {}
        self.image_list = []
        self.text_cache = {}
        self.disk_snapshots = {}
        self.current_img_index = -1
        
        try:
            all_files = os.listdir(in_dir)
        except Exception as e:
            messagebox.showerror("Error", f"Unable to read files: {e}")
            return

        if self.sort_var.get() == "name":
            try:
                all_files.sort(key=lambda x: int(os.path.splitext(x)[0]))
            except ValueError:
                all_files.sort()
        else:
            all_files.sort(key=lambda x: os.path.getmtime(os.path.join(in_dir, x)), reverse=True)

        txt_files = [f for f in all_files if f.lower().endswith('.txt')]
        img_files = [f for f in all_files if f.lower().endswith(self.image_extensions)]

        # Read text files to cache
        for fname in txt_files:
            fpath = os.path.join(in_dir, fname)
            content = ""
            for enc in ['utf-8', 'cp1251', 'latin-1']:
                try:
                    with open(fpath, 'r', encoding=enc) as f:
                        content = f.read().rstrip('\r\n')
                    break
                except UnicodeDecodeError:
                    continue
            self.text_cache[fname] = content
            self.disk_snapshots[fname] = content
            self.file_data.append({'name': fname, 'content': content})

        for fname in img_files:
            self.image_list.append(os.path.join(in_dir, fname))
            t_name = os.path.splitext(fname)[0] + ".txt"
            if t_name not in self.disk_snapshots:
                self.disk_snapshots[t_name] = ""
                self.text_cache[t_name] = ""

        # Draw batch lines
        for item in self.file_data:
            fname = item['name']
            row_frame = tk.Frame(self.scrollable_frame, bg="#ffffff", pady=4)
            row_frame.pack(fill=tk.X, expand=True, padx=5)
            
            lbl = ttk.Label(row_frame, text=f"[{fname}]", width=18, font=('Courier', 10, 'bold'), background="#ffffff")
            lbl.pack(side=tk.LEFT, padx=(5,10))
            
            arrow_lbl = ttk.Label(row_frame, text="-", background="#ffffff")
            arrow_lbl.pack(side=tk.LEFT, padx=(0,10))
            
            ent = ttk.Entry(row_frame)
            ent.insert(0, item['content'])
            ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
            
            self.entry_widgets[fname] = ent
            sep = ttk.Separator(self.scrollable_frame, orient=tk.HORIZONTAL)
            sep.pack(fill=tk.X, padx=5, pady=2)

        if self.file_data or self.image_list:
            self.btn_replace.config(state=tk.NORMAL)
            if self.mode_var.get() == "batch" and self.file_data:
                self.btn_export.config(state=tk.NORMAL)
            if self.image_list:
                self.current_img_index = 0
            self.refresh_listbox()
            messagebox.showinfo("Success", f"Loaded: {len(txt_files)} text files, {len(img_files)} images.")
        else:
            messagebox.showinfo("Information", "No matching files found.")

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

    # --- IMG+TXT MODE LOGIC ---
    def load_current_image_data(self):
        if not self.image_list or self.current_img_index < 0:
            return
        
        img_path = self.image_list[self.current_img_index]
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        txt_name = base_name + ".txt"
        
        self.lbl_img_filename.config(text=os.path.basename(img_path))
        self.lbl_txt_filename.config(text=txt_name)
        
        txt_content = self.text_cache.get(txt_name, "")
        
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert(tk.END, txt_content)
        
        self.files_listbox.selection_clear(0, tk.END)
        self.files_listbox.selection_set(self.current_img_index)
        self.files_listbox.see(self.current_img_index)
        
        self.display_image()

    def display_image(self):
        if not self.image_list or self.current_img_index < 0:
            return
        img_path = self.image_list[self.current_img_index]
        try:
            img = Image.open(img_path)
            canvas_w = self.img_canvas.winfo_width()
            canvas_h = self.img_canvas.winfo_height()
            
            if canvas_w < 10: canvas_w = 500
            if canvas_h < 10: canvas_h = 350
            
            img_w, img_h = img.size
            ratio = min(canvas_w / img_w, canvas_h / img_h)
            
            new_w = max(1, int(img_w * ratio))
            new_h = max(1, int(img_h * ratio))
            
            img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.tk_img = ImageTk.PhotoImage(img_resized)
            
            self.img_canvas.delete("all")
            self.img_canvas.create_image(canvas_w // 2, canvas_h // 2, anchor=tk.CENTER, image=self.tk_img)
        except Exception as e:
            self.img_canvas.delete("all")
            self.img_canvas.create_text(50, 50, text=f"Error displaying image:\n{e}", fill="red", anchor=tk.NW)

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
        """Compares cache state against pristine disk copies"""
        if self.current_img_index < 0:
            return "no_change"
            
        img_path = self.image_list[self.current_img_index]
        txt_name = os.path.splitext(os.path.basename(img_path))[0] + ".txt"
        
        current_cached_text = self.text_cache.get(txt_name, "").strip()
        disk_original_text = self.disk_snapshots.get(txt_name, "").strip()
        
        if current_cached_text != disk_original_text:
            # Strictly matches your prompt request string requirement
            ans = messagebox.askyesnocancel("Save Changes", f"Save changes? The updated {txt_name} will be saved in the output folder.")
            if ans is True:
                if self.save_current_img_txt():
                    return "saved"
                else:
                    return "cancel"
            elif ans is False:
                # User discarded edits -> revert local cache line state back to disk snapshot
                self.text_cache[txt_name] = disk_original_text
                return "ignored"
            else:
                return "cancel"
        return "no_change"

    def save_current_img_txt(self):
        out_dir = self.out_path_entry.get().strip()
        if not out_dir:
            messagebox.showerror("Error", "Specify the (Output folder) where you want to save the results!")
            return False
            
        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create output folder: {e}")
                return False

        img_path = self.image_list[self.current_img_index]
        base_name = os.path.splitext(os.path.basename(img_path))[0]
        txt_name = base_name + ".txt"
        
        content_to_save = self.text_cache.get(txt_name, "").strip()
        
        if not content_to_save and not self.disk_snapshots.get(txt_name):
            return True

        out_file_path = os.path.join(out_dir, txt_name)
        try:
            with open(out_file_path, 'w', encoding='utf-8') as f:
                f.write(content_to_save)
            self.disk_snapshots[txt_name] = content_to_save
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Unable to save file {txt_name}: {e}")
            return False

    # --- ACTION MANAGEMENT BACKENDS ---
    def apply_mass_replace(self):
        search_str = self.search_entry.get()
        replace_str = self.replace_entry.get()
        if not search_str:
            messagebox.showwarning("Error", "The 'Search for word' field must not be left blank!")
            return
            
        self.save_batch_fields_to_cache()
        count = 0
        
        for fname in self.text_cache:
            current_text = self.text_cache[fname]
            if search_str in current_text:
                self.text_cache[fname] = current_text.replace(search_str, replace_str)
                count += 1
                
        if self.mode_var.get() == "batch":
            for fname, entry_widget in self.entry_widgets.items():
                if fname in self.text_cache:
                    entry_widget.delete(0, tk.END)
                    entry_widget.insert(0, self.text_cache[fname])
                    
        messagebox.showinfo("Success", f"Replaced in {count} fields. Changes are cached. Switch mode or move images to trigger saving!")

    def export_files(self):
        in_dir = self.in_path_entry.get().strip()
        out_dir = self.out_path_entry.get().strip()
        if not out_dir:
            messagebox.showerror("Error", "Specify the (Output folder) where you want to save the results!")
            return
        if os.path.abspath(in_dir) == os.path.abspath(out_dir):
            messagebox.showerror("Error", "The input and output folders are the SAME!")
            return
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
            
        self.save_batch_fields_to_cache()
        success_count = 0
        
        for fname, content_to_save in self.text_cache.items():
            if content_to_save.strip() != self.disk_snapshots.get(fname, "").strip():
                out_file_path = os.path.join(out_dir, fname)
                try:
                    with open(out_file_path, 'w', encoding='utf-8') as f:
                        f.write(content_to_save)
                    self.disk_snapshots[fname] = content_to_save
                    success_count += 1
                except Exception as e:
                    print(f"Error saving file {fname}: {e}")
                    
        messagebox.showinfo("Success", f"Saved {success_count} modified files to:\n{out_dir}")

if __name__ == "__main__":
    root = tk.Tk()
    app = TextManagerApp(root)
    root.mainloop()