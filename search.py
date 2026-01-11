import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

class TextSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Recursive Text Search")
        self.root.geometry("900x600")
        
        # Top frame
        top_frame = ttk.Frame(root, padding=10)
        top_frame.pack(fill=tk.X)
        
        # Path selection
        ttk.Label(top_frame, text="Path:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.path_var, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Browse", command=self.browse_path).pack(side=tk.LEFT)
        
        # Search text
        ttk.Label(top_frame, text="Search:").pack(side=tk.LEFT, padx=(20, 0))
        self.search_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=5)
        
        # File extensions
        ttk.Label(top_frame, text="Ext:").pack(side=tk.LEFT, padx=(10, 0))
        self.ext_var = tk.StringVar(value="")
        ttk.Entry(top_frame, textvariable=self.ext_var, width=15).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(top_frame, text="Search", command=self.start_search).pack(side=tk.LEFT)
        
        # Case sensitive checkbox
        self.case_var = tk.BooleanVar()
        ttk.Checkbutton(top_frame, text="Case sensitive", variable=self.case_var).pack(side=tk.LEFT, padx=10)
        
        # Status
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(root, textvariable=self.status_var).pack(anchor=tk.W, padx=10)
        
        # Results
        result_frame = ttk.Frame(root)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tree = ttk.Treeview(result_frame, columns=("file", "line", "content"), show="headings")
        self.tree.heading("file", text="File")
        self.tree.heading("line", text="Line")
        self.tree.heading("content", text="Content")
        self.tree.column("file", width=350)
        self.tree.column("line", width=50)
        self.tree.column("content", width=450)
        
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)
    
    def start_search(self):
        path = self.path_var.get()
        search_text = self.search_var.get()
        
        if not path or not search_text:
            messagebox.showwarning("Warning", "Please enter path and search text")
            return
        
        if not os.path.isdir(path):
            messagebox.showerror("Error", "Invalid path")
            return
        
        self.tree.delete(*self.tree.get_children())
        extensions = [e.strip().lower().lstrip('.') for e in self.ext_var.get().split(',') if e.strip()]
        threading.Thread(target=self.search_files, args=(path, search_text, extensions), daemon=True).start()
    
    def search_files(self, path, search_text, extensions):
        count = 0
        case_sensitive = self.case_var.get()
        search_lower = search_text if case_sensitive else search_text.lower()
        
        for root_dir, _, files in os.walk(path):
            for file in files:
                # Filter by extension if specified
                if extensions:
                    file_ext = file.rsplit('.', 1)[-1].lower() if '.' in file else ''
                    if file_ext not in extensions:
                        continue
                
                filepath = os.path.join(root_dir, file)
                self.status_var.set(f"Scanning: {filepath}")
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            compare_line = line if case_sensitive else line.lower()
                            if search_lower in compare_line:
                                count += 1
                                self.tree.insert("", tk.END, values=(
                                    filepath,
                                    line_num,
                                    line.strip()[:200]
                                ))
                except:
                    pass
        
        self.status_var.set(f"Done. Found {count} matches.")

if __name__ == "__main__":
    root = tk.Tk()
    app = TextSearchApp(root)
    root.mainloop()