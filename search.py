import os
import io
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from ftplib import FTP


class TextSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Recursive Text Search")
        self.root.geometry("900x700")

        self.ftp = None  # FTP connection
        self.sort_reverse = {"file": False, "line": False, "content": False}  # Track sort direction

        # Mode selection frame
        mode_frame = ttk.LabelFrame(root, text="Search Mode", padding=10)
        mode_frame.pack(fill=tk.X, padx=10, pady=5)

        self.mode_var = tk.StringVar(value="local")
        ttk.Radiobutton(mode_frame, text="Local", variable=self.mode_var,
                        value="local", command=self.toggle_mode).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="Remote (FTP)", variable=self.mode_var,
                        value="ftp", command=self.toggle_mode).pack(side=tk.LEFT, padx=10)

        # FTP connection frame
        self.ftp_frame = ttk.LabelFrame(root, text="FTP Connection", padding=10)
        self.ftp_frame.pack(fill=tk.X, padx=10, pady=5)

        # FTP Host
        ftp_row1 = ttk.Frame(self.ftp_frame)
        ftp_row1.pack(fill=tk.X, pady=2)
        ttk.Label(ftp_row1, text="Host:", width=10).pack(side=tk.LEFT)
        self.ftp_host_var = tk.StringVar()
        ttk.Entry(ftp_row1, textvariable=self.ftp_host_var, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Label(ftp_row1, text="Port:").pack(side=tk.LEFT, padx=(20, 0))
        self.ftp_port_var = tk.StringVar(value="21")
        ttk.Entry(ftp_row1, textvariable=self.ftp_port_var, width=8).pack(side=tk.LEFT, padx=5)

        # FTP Username/Password
        ftp_row2 = ttk.Frame(self.ftp_frame)
        ftp_row2.pack(fill=tk.X, pady=2)
        ttk.Label(ftp_row2, text="Username:", width=10).pack(side=tk.LEFT)
        self.ftp_user_var = tk.StringVar()
        ttk.Entry(ftp_row2, textvariable=self.ftp_user_var, width=20).pack(side=tk.LEFT, padx=5)
        ttk.Label(ftp_row2, text="Password:").pack(side=tk.LEFT, padx=(20, 0))
        self.ftp_pass_var = tk.StringVar()
        ttk.Entry(ftp_row2, textvariable=self.ftp_pass_var, width=20, show="*").pack(side=tk.LEFT, padx=5)

        # FTP Connect button and status
        ftp_row3 = ttk.Frame(self.ftp_frame)
        ftp_row3.pack(fill=tk.X, pady=5)
        self.connect_btn = ttk.Button(ftp_row3, text="Connect", command=self.connect_ftp)
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        self.disconnect_btn = ttk.Button(ftp_row3, text="Disconnect", command=self.disconnect_ftp, state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=5)
        self.ftp_status_var = tk.StringVar(value="Not connected")
        ttk.Label(ftp_row3, textvariable=self.ftp_status_var, foreground="gray").pack(side=tk.LEFT, padx=20)

        # Initially hide FTP frame
        self.ftp_frame.pack_forget()

        # Path/Search frame
        top_frame = ttk.Frame(root, padding=10)
        top_frame.pack(fill=tk.X)

        # Path selection
        ttk.Label(top_frame, text="Path:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.path_var, width=50).pack(side=tk.LEFT, padx=5)
        self.browse_btn = ttk.Button(top_frame, text="Browse", command=self.browse_path)
        self.browse_btn.pack(side=tk.LEFT)

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
        self.tree.heading("file", text="File", command=lambda: self.sort_column("file"))
        self.tree.heading("line", text="Line", command=lambda: self.sort_column("line"))
        self.tree.heading("content", text="Content", command=lambda: self.sort_column("content"))
        self.tree.column("file", width=350)
        self.tree.column("line", width=50)
        self.tree.column("content", width=450)

        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def toggle_mode(self):
        """Show/hide FTP options based on selected mode."""
        if self.mode_var.get() == "ftp":
            self.ftp_frame.pack(fill=tk.X, padx=10, pady=5, after=self.root.winfo_children()[0])
            self.browse_btn.config(state=tk.DISABLED)
            self.path_var.set("/")  # Default FTP root
        else:
            self.ftp_frame.pack_forget()
            self.browse_btn.config(state=tk.NORMAL)
            self.path_var.set("")
            self.disconnect_ftp()

    def connect_ftp(self):
        """Connect to FTP server."""
        host = self.ftp_host_var.get().strip()
        port = self.ftp_port_var.get().strip()
        user = self.ftp_user_var.get().strip()
        password = self.ftp_pass_var.get()

        if not host:
            messagebox.showwarning("Warning", "Please enter FTP host")
            return

        try:
            port = int(port) if port else 21
            self.ftp = FTP()
            self.ftp.connect(host, port, timeout=30)

            if user:
                self.ftp.login(user, password)
            else:
                self.ftp.login()  # Anonymous login

            self.ftp_status_var.set(f"Connected to {host}")
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            messagebox.showinfo("Success", f"Connected to {host}")

        except Exception as e:
            self.ftp = None
            messagebox.showerror("Connection Error", str(e))

    def disconnect_ftp(self):
        """Disconnect from FTP server."""
        if self.ftp:
            try:
                self.ftp.quit()
            except:
                pass
            self.ftp = None

        self.ftp_status_var.set("Not connected")
        self.connect_btn.config(state=tk.NORMAL)
        self.disconnect_btn.config(state=tk.DISABLED)

    def browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)

    def sort_column(self, col):
        """Sort treeview by column when header is clicked."""
        # Get all items
        items = [(self.tree.set(item, col), item) for item in self.tree.get_children("")]

        # Sort - use numeric sort for line numbers
        if col == "line":
            items.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0, reverse=self.sort_reverse[col])
        else:
            items.sort(key=lambda x: x[0].lower(), reverse=self.sort_reverse[col])

        # Rearrange items in sorted order
        for index, (_, item) in enumerate(items):
            self.tree.move(item, "", index)

        # Toggle sort direction for next click
        self.sort_reverse[col] = not self.sort_reverse[col]

    def start_search(self):
        path = self.path_var.get()
        search_text = self.search_var.get()

        if not path or not search_text:
            messagebox.showwarning("Warning", "Please enter path and search text")
            return

        if self.mode_var.get() == "local":
            if not os.path.isdir(path):
                messagebox.showerror("Error", "Invalid path")
                return
            self.tree.delete(*self.tree.get_children())
            extensions = [e.strip().lower().lstrip('.') for e in self.ext_var.get().split(',') if e.strip()]
            threading.Thread(target=self.search_files_local, args=(path, search_text, extensions), daemon=True).start()
        else:
            # FTP mode
            if not self.ftp:
                messagebox.showwarning("Warning", "Please connect to FTP server first")
                return
            self.tree.delete(*self.tree.get_children())
            extensions = [e.strip().lower().lstrip('.') for e in self.ext_var.get().split(',') if e.strip()]
            threading.Thread(target=self.search_files_ftp, args=(path, search_text, extensions), daemon=True).start()

    def search_files_local(self, path, search_text, extensions):
        """Search files on local filesystem using parallel processing."""
        case_sensitive = self.case_var.get()
        search_lower = search_text if case_sensitive else search_text.lower()

        # Collect all files first
        all_files = []
        for root_dir, _, files in os.walk(path):
            for file in files:
                if extensions:
                    file_ext = file.rsplit('.', 1)[-1].lower() if '.' in file else ''
                    if file_ext not in extensions:
                        continue
                all_files.append(os.path.join(root_dir, file))

        total_files = len(all_files)
        results = []
        results_lock = threading.Lock()

        def is_binary(filepath):
            """Quick check for binary files by looking for null bytes."""
            try:
                with open(filepath, 'rb') as f:
                    chunk = f.read(8192)
                    return b'\x00' in chunk
            except:
                return True

        def search_single_file(filepath):
            """Search a single file and return matches."""
            matches = []
            if is_binary(filepath):
                return matches
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        compare_line = line if case_sensitive else line.lower()
                        if search_lower in compare_line:
                            matches.append((filepath, line_num, line.strip()[:200]))
            except:
                pass
            return matches

        processed = [0]

        def update_progress():
            self.status_var.set(f"Scanning: {processed[0]}/{total_files} files...")

        # Use thread pool for parallel file searching
        max_workers = min(32, (os.cpu_count() or 1) * 4)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {executor.submit(search_single_file, f): f for f in all_files}

            batch = []
            batch_size = 100

            for future in as_completed(future_to_file):
                processed[0] += 1
                if processed[0] % 50 == 0:
                    self.root.after(0, update_progress)

                file_matches = future.result()
                if file_matches:
                    batch.extend(file_matches)

                    # Insert in batches to reduce UI overhead
                    if len(batch) >= batch_size:
                        batch_to_insert = batch[:]
                        batch.clear()
                        self.root.after(0, lambda b=batch_to_insert: self._insert_batch(b))

            # Insert remaining results
            if batch:
                self.root.after(0, lambda b=batch: self._insert_batch(b))

        total_matches = sum(1 for _ in self.tree.get_children())
        self.status_var.set(f"Done. Found {total_matches} matches in {total_files} files.")

    def _insert_batch(self, batch):
        """Insert a batch of results into the treeview."""
        for filepath, line_num, content in batch:
            self.tree.insert("", tk.END, values=(filepath, line_num, content))

    def search_files_ftp(self, path, search_text, extensions):
        """Search files on FTP server recursively with batched UI updates."""
        case_sensitive = self.case_var.get()
        search_lower = search_text if case_sensitive else search_text.lower()
        batch = []
        batch_size = 50
        match_count = [0]

        def list_files_recursive(ftp_path):
            """Recursively list all files in FTP directory."""
            files = []
            try:
                items = []
                self.ftp.cwd(ftp_path)
                self.ftp.retrlines('LIST', items.append)

                for item in items:
                    parts = item.split(None, 8)
                    if len(parts) < 9:
                        continue

                    name = parts[8]
                    if name in ('.', '..'):
                        continue

                    full_path = f"{ftp_path.rstrip('/')}/{name}"

                    if item.startswith('d'):
                        files.extend(list_files_recursive(full_path))
                    else:
                        files.append(full_path)
            except:
                pass
            return files

        def flush_batch():
            """Send current batch to UI."""
            if batch:
                batch_copy = batch[:]
                batch.clear()
                self.root.after(0, lambda b=batch_copy: self._insert_batch(b))

        def search_ftp_file(filepath, file_idx, total):
            """Download and search a single FTP file."""
            if file_idx % 10 == 0:
                self.root.after(0, lambda: self.status_var.set(f"Scanning: {file_idx}/{total} files..."))

            try:
                content = io.BytesIO()
                self.ftp.retrbinary(f'RETR {filepath}', content.write)
                raw_data = content.getvalue()

                # Skip binary files (check for null bytes)
                if b'\x00' in raw_data[:8192]:
                    return

                text = raw_data.decode('utf-8', errors='ignore')
                lines = text.split('\n')

                for line_num, line in enumerate(lines, 1):
                    compare_line = line if case_sensitive else line.lower()
                    if search_lower in compare_line:
                        match_count[0] += 1
                        batch.append((filepath, line_num, line.strip()[:200]))

                        if len(batch) >= batch_size:
                            flush_batch()
            except:
                pass

        try:
            self.status_var.set("Listing FTP files...")
            all_files = list_files_recursive(path)

            if extensions:
                all_files = [f for f in all_files
                           if '.' in f and f.rsplit('.', 1)[-1].lower() in extensions]

            total = len(all_files)
            self.status_var.set(f"Found {total} files. Searching...")

            for idx, filepath in enumerate(all_files):
                search_ftp_file(filepath, idx, total)

            # Flush remaining results
            flush_batch()

            self.status_var.set(f"Done. Found {match_count[0]} matches in {total} files.")

        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = TextSearchApp(root)
    root.mainloop()
