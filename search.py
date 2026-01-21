import os
import io
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import tempfile
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

        # Update header to show sort direction
        arrow = " ▼" if not self.sort_reverse[col] else " ▲"
        headers = {"file": "File", "line": "Line", "content": "Content"}
        for c in headers:
            text = headers[c] + (arrow if c == col else "")
            self.tree.heading(c, text=text)

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
        """Search files on local filesystem."""
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

    def search_files_ftp(self, path, search_text, extensions):
        """Search files on FTP server recursively."""
        count = [0]  # Use list for mutability in nested function
        case_sensitive = self.case_var.get()
        search_lower = search_text if case_sensitive else search_text.lower()

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

                    # Check if it's a directory
                    if item.startswith('d'):
                        files.extend(list_files_recursive(full_path))
                    else:
                        files.append(full_path)
            except Exception as e:
                pass

            return files

        def search_ftp_file(filepath):
            """Download and search a single FTP file."""
            try:
                self.status_var.set(f"Scanning: {filepath}")

                # Download file content to memory
                content = io.BytesIO()
                self.ftp.retrbinary(f'RETR {filepath}', content.write)
                content.seek(0)

                # Try to decode as text
                try:
                    text = content.read().decode('utf-8', errors='ignore')
                except:
                    return

                lines = text.split('\n')
                for line_num, line in enumerate(lines, 1):
                    compare_line = line if case_sensitive else line.lower()
                    if search_lower in compare_line:
                        count[0] += 1
                        self.root.after(0, lambda fp=filepath, ln=line_num, l=line:
                            self.tree.insert("", tk.END, values=(
                                fp,
                                ln,
                                l.strip()[:200]
                            ))
                        )
            except Exception as e:
                pass

        try:
            self.status_var.set("Listing FTP files...")
            all_files = list_files_recursive(path)

            # Filter by extensions if specified
            if extensions:
                all_files = [f for f in all_files
                           if '.' in f and f.rsplit('.', 1)[-1].lower() in extensions]

            self.status_var.set(f"Found {len(all_files)} files. Searching...")

            for filepath in all_files:
                search_ftp_file(filepath)

            self.status_var.set(f"Done. Found {count[0]} matches in {len(all_files)} files.")

        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = TextSearchApp(root)
    root.mainloop()
