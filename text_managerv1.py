import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class TextManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Text Manager")
        self.root.geometry("1050x650")
        self.root.minsize(850, 500)
        
        # Хранилище данных
        self.file_data = []      # Список словарей: {'name': ..., 'content': ...}
        self.entry_widgets = {}  # Словарь связи: имя_файла -> виджет ввода Entry
        
        self.setup_ui()
        
    def setup_ui(self):
        # Настройка стиля (классическая чистая тема)
        style = ttk.Style()
        style.theme_use('clam')
        
        # Главный разделитель окон (слева панель управления, справа рабочая зона)
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # --- ЛЕВАЯ ПАНЕЛЬ (УПРАВЛЕНИЕ) ---
        left_frame = ttk.Frame(main_paned, width=320, padding=10)
        main_paned.add(left_frame, weight=1)
        
        # Входная папка
        ttk.Label(left_frame, text="Input folder (source .txt files):", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(0,5))
        in_path_frame = ttk.Frame(left_frame)
        in_path_frame.pack(fill=tk.X, pady=(0,10))
        self.in_path_entry = ttk.Entry(in_path_frame)
        self.in_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        ttk.Button(in_path_frame, text="Select...", command=self.browse_input).pack(side=tk.RIGHT)
        
        # Выходная папка
        ttk.Label(left_frame, text="Output folder (save):", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(5,5))
        out_path_frame = ttk.Frame(left_frame)
        out_path_frame.pack(fill=tk.X, pady=(0,15))
        self.out_path_entry = ttk.Entry(out_path_frame)
        self.out_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        ttk.Button(out_path_frame, text="Select...", command=self.browse_output).pack(side=tk.RIGHT)
        
        # Сортировка
        ttk.Label(left_frame, text="File Sorting:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(5,5))
        self.sort_var = tk.StringVar(value="name")
        ttk.Radiobutton(left_frame, text="By filename", variable=self.sort_var, value="name").pack(anchor=tk.W, padx=5)
        ttk.Radiobutton(left_frame, text="By date of change", variable=self.sort_var, value="date").pack(anchor=tk.W, padx=5, pady=(0,15))
        
        # Кнопка Импортировать
        self.btn_import = ttk.Button(left_frame, text="📥 IMPORT FILES", command=self.import_files)
        self.btn_import.pack(fill=tk.X, ipady=6, pady=(0,15))
        
        # Список файлов для визуального контроля
        ttk.Label(left_frame, text="Found files:", font=('Arial', 9, 'italic')).pack(anchor=tk.W)
        self.files_listbox = tk.Listbox(left_frame, height=12, bg="#f9f9f9", fg="#333333", selectbackground="#4a90e2")
        self.files_listbox.pack(fill=tk.BOTH, expand=True, pady=(5,15))
        
        # Кнопка Экспортировать в самом низу
        self.btn_export = ttk.Button(left_frame, text="💾 EXPORT EDITS", command=self.export_files, state=tk.DISABLED)
        self.btn_export.pack(fill=tk.X, ipady=10)
        
        # --- ПРАВАЯ ПАНЕЛЬ (РАБОЧАЯ ЗОНА) ---
        right_container = ttk.Frame(main_paned, padding=10)
        main_paned.add(right_container, weight=3)
        
        # Заголовок рабочей зоны
        ttk.Label(right_container, text="File Content Editor (Line-by-Line):", font=('Arial', 11, 'bold')).pack(anchor=tk.W, pady=(0,5))
        
        # Прокручиваемая область (Canvas + Скроллбар)
        self.work_frame = ttk.Frame(right_container, relief=tk.SUNKEN, borderwidth=1)
        self.work_frame.pack(fill=tk.BOTH, expand=True, pady=(0,10))
        
        self.canvas = tk.Canvas(self.work_frame, borderwidth=0, highlightthickness=0, bg="#ffffff")
        self.scrollbar = ttk.Scrollbar(self.work_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#ffffff")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Автоматическое растягивание содержимого по ширине окна
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Привязка колесика мыши для удобного скролла
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # --- ПАНЕЛЬ МАССОВОЙ ЗАМЕНЫ (Снизу справа) ---
        replace_frame = ttk.LabelFrame(right_container, text=" Batch Replace Panel ", padding=10)
        replace_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(5,0))
        
        ttk.Label(replace_frame, text="Search for:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.search_entry = ttk.Entry(replace_frame, width=22)
        self.search_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(replace_frame, text="Replace to:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.replace_entry = ttk.Entry(replace_frame, width=22)
        self.replace_entry.grid(row=0, column=3, padx=5, pady=5)
        
        self.btn_replace = ttk.Button(replace_frame, text="🔄 Apply the replacement", command=self.apply_mass_replace, state=tk.DISABLED)
        self.btn_replace.grid(row=0, column=4, padx=15, pady=5)
        
    def _on_mousewheel(self, event):
        # Поддержка прокрутки колесиком мыши
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
    def _on_canvas_configure(self, event):
        # Чтобы строки растягивались на всю ширину канваса
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
            
        # Очистка старых виджетов и данных перед новым импортом
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.file_data = []
        self.entry_widgets = {}
        self.files_listbox.delete(0, tk.END)
        
        try:
            files = [f for f in os.listdir(in_dir) if f.lower().endswith('.txt')]
        except Exception as e:
            messagebox.showerror("Error", f"Unable to read files from the folder: {e}")
            return
            
        if not files:
            messagebox.showinfo("Error", "There are no files with the .txt extension in the selected folder")
            return
            
        # Логика сортировки
        if self.sort_var.get() == "name":
            # Пробуем умную числовую сортировку, если имена файлов — индексы (1.txt, 2.txt...)
            try:
                files.sort(key=lambda x: int(os.path.splitext(x)[0]))
            except ValueError:
                files.sort() # Обычная алфавитная сортировка, если имена текстовые
        else:
            files.sort(key=lambda x: os.path.getmtime(os.path.join(in_dir, x)), reverse=True)
            
        # Чтение содержимого файлов
        for fname in files:
            fpath = os.path.join(in_dir, fname)
            content = ""
            # Пробуем стандартные кодировки во избежание сбоев из-за кириллицы
            for enc in ['utf-8', 'cp1251', 'latin-1']:
                try:
                    with open(fpath, 'r', encoding=enc) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            self.file_data.append({'name': fname, 'content': content})
            self.files_listbox.insert(tk.END, fname)
            
        # Отрисовка динамических строк в правой панели
        for item in self.file_data:
            fname = item['name']
            # Убираем лишние переносы строк на концах для аккуратного построчного редактирования
            content_line = item['content'].rstrip('\r\n') 
            
            row_frame = tk.Frame(self.scrollable_frame, bg="#ffffff", pady=4)
            row_frame.pack(fill=tk.X, expand=True, padx=5)
            
            # Метка с именем файла
            lbl = ttk.Label(row_frame, text=f"[{fname}]", width=18, font=('Courier', 10, 'bold'), background="#ffffff")
            lbl.pack(side=tk.LEFT, padx=(5,10))
            
            # Информационная стрелочка-разделитель
            arrow_lbl = ttk.Label(row_frame, text="-", background="#ffffff")
            arrow_lbl.pack(side=tk.LEFT, padx=(0,10))
            
            # Поле ввода содержимого (доступно для изменения)
            ent = ttk.Entry(row_frame)
            ent.insert(0, content_line)
            ent.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
            
            # Сохраняем ссылку на виджет для последующего сбора данных
            self.entry_widgets[fname] = ent
            
            # Тонкая разделительная черта между строками
            sep = ttk.Separator(self.scrollable_frame, orient=tk.HORIZONTAL)
            sep.pack(fill=tk.X, padx=5, pady=2)
            
        # Активация кнопок управления
        if self.file_data:
            self.btn_export.config(state=tk.NORMAL)
            self.btn_replace.config(state=tk.NORMAL)
            messagebox.showinfo("Success", f"Files loaded: {len(self.file_data)}")
            
    def apply_mass_replace(self):
        search_str = self.search_entry.get()
        replace_str = self.replace_entry.get()
        
        if not search_str:
            messagebox.showwarning("Error", "The 'Search for word' field must not be left blank!")
            return
            
        count = 0
        # Проходим по всем созданным текстовым полям на экране
        for fname, entry_widget in self.entry_widgets.items():
            current_text = entry_widget.get()
            if search_str in current_text:
                new_text = current_text.replace(search_str, replace_str)
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, new_text)
                count += 1
                
        messagebox.showinfo("Replacement successful", f"word '{search_str}' is replaced '{replace_str}' in {count} input fields on the screen.\n\nDon't forget to click the Export button to save your changes to disk!")
        
    def export_files(self):
        in_dir = self.in_path_entry.get().strip()
        out_dir = self.out_path_entry.get().strip()
        
        if not out_dir:
            messagebox.showerror("Error", "Specify the (Output folder) where you want to save the results!")
            return
            
        # Проверка "Защиты от дурака" на совпадение папок
        if os.path.abspath(in_dir) == os.path.abspath(out_dir):
            messagebox.showerror(
                "Protection Against a Fool", 
                "The input and output folders are the SAME!\n\nFor security reasons, please choose a different folder to save your results so that you don't accidentally overwrite the original files."
            )
            return
            
        # Создаем папку, если её физически ещё нет
        if not os.path.exists(out_dir):
            try:
                os.makedirs(out_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create the export folder: {e}")
                return
                
        success_count = 0
        # Запись обновленных данных из виджетов в новые файлы
        for fname, entry_widget in self.entry_widgets.items():
            content_to_save = entry_widget.get()
            out_file_path = os.path.join(out_dir, fname)
            try:
                with open(out_file_path, 'w', encoding='utf-8') as f:
                    f.write(content_to_save)
                success_count += 1
            except Exception as e:
                messagebox.showerror("Error", f"Unable to save changes to the file {fname}: {e}")
                
        messagebox.showinfo(
            "The export was successful!", 
            f"Total number of files saved: {success_count}\n\nSave path:\n{out_dir}"
        )

if __name__ == "__main__":
    root = tk.Tk()
    app = TextManagerApp(root)
    root.mainloop()
