import os
import io
import sys
import subprocess
import platform
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
        self.ftp_lock = threading.Lock()  # Prevent concurrent FTP commands
        self.ftp_creds = {}  # Store credentials for auto-reconnect
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

        # Right-click context menu
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """Show right-click context menu on treeview item."""
        item = self.tree.identify_row(event.y)
        if not item:
            return

        # Keep existing selection if right-clicking within it, otherwise select clicked item
        selected = self.tree.selection()
        if item not in selected:
            self.tree.selection_set(item)
            selected = (item,)

        self.context_menu.delete(0, tk.END)

        # Collect info from all selected items
        items_info = []
        for sel in selected:
            values = self.tree.item(sel, "values")
            if values:
                items_info.append({"filepath": values[0], "line": values[1], "content": values[2]})

        if not items_info:
            return

        count = len(items_info)
        filepaths = [info["filepath"] for info in items_info]

        if self.mode_var.get() == "local":
            if count == 1:
                self.context_menu.add_command(
                    label="Open File",
                    command=lambda: self.open_file_local(filepaths[0]))
                self.context_menu.add_command(
                    label="Open Containing Folder",
                    command=lambda: self.open_folder_local(filepaths[0]))
            else:
                self.context_menu.add_command(
                    label=f"Open {count} Files",
                    command=lambda ps=filepaths: [self.open_file_local(p) for p in ps])
            self.context_menu.add_separator()
        else:
            if count == 1:
                self.context_menu.add_command(
                    label="Download & Open File",
                    command=lambda: self.open_file_ftp(filepaths[0]))
            else:
                self.context_menu.add_command(
                    label=f"Download & Open {count} Files",
                    command=lambda ps=filepaths: [self.open_file_ftp(p) for p in ps])
            self.context_menu.add_separator()

        if count == 1:
            self.context_menu.add_command(
                label="Copy File Path",
                command=lambda: self.copy_to_clipboard(filepaths[0]))
            self.context_menu.add_command(
                label="Copy Line Content",
                command=lambda: self.copy_to_clipboard(items_info[0]["content"]))
        else:
            self.context_menu.add_command(
                label=f"Copy {count} File Paths",
                command=lambda ps=filepaths: self.copy_to_clipboard("\n".join(ps)))

        self.context_menu.tk_popup(event.x_root, event.y_root)

    def copy_to_clipboard(self, text):
        """Copy text to system clipboard."""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def open_file_local(self, filepath):
        """Open a local file with the system default application."""
        try:
            if platform.system() == "Windows":
                os.startfile(filepath)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", filepath])
            else:
                subprocess.Popen(["xdg-open", filepath])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file:\n{e}")

    def open_folder_local(self, filepath):
        """Open the containing folder of a local file."""
        folder = os.path.dirname(filepath)
        try:
            if platform.system() == "Windows":
                os.startfile(folder)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder:\n{e}")

    def open_file_ftp(self, remote_path):
        """Download an FTP file, open it for editing, and re-upload if changed."""
        if not self.ftp:
            messagebox.showwarning("Warning", "Not connected to FTP server")
            return

        def download_edit_upload():
            try:
                filename = os.path.basename(remote_path)
                tmp_dir = tempfile.mkdtemp(prefix="search_ftp_")
                local_path = os.path.join(tmp_dir, filename)

                with self.ftp_lock:
                    self._ensure_ftp()
                    with open(local_path, 'wb') as f:
                        self.ftp.retrbinary(f'RETR {remote_path}', f.write)

                mtime_before = os.path.getmtime(local_path)
                self.open_file_local(local_path)

                # Ask user to confirm when done editing
                self.root.after(0, lambda: self.prompt_ftp_reupload(
                    local_path, remote_path, mtime_before))
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda: messagebox.showerror(
                    "Error", f"Could not download file:\n{err_msg}"))

        threading.Thread(target=download_edit_upload, daemon=True).start()

    def prompt_ftp_reupload(self, local_path, remote_path, mtime_before):
        """Ask user if they want to upload changes back to FTP."""
        result = messagebox.askyesno(
            "Upload Changes?",
            f"File opened for editing:\n{os.path.basename(local_path)}\n\n"
            f"Click Yes when done editing to upload changes back to:\n{remote_path}\n\n"
            f"Click No to discard changes.")
        if not result:
            return

        def do_upload():
            try:
                mtime_after = os.path.getmtime(local_path)
                if mtime_after == mtime_before:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "No Changes", "File was not modified. Nothing to upload."))
                    return

                with self.ftp_lock:
                    self._ensure_ftp()
                    with open(local_path, 'rb') as f:
                        self.ftp.storbinary(f'STOR {remote_path}', f)

                self.root.after(0, lambda: messagebox.showinfo(
                    "Uploaded", f"Changes uploaded to:\n{remote_path}"))
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda: messagebox.showerror(
                    "Upload Error", f"Could not upload file:\n{err_msg}"))

        threading.Thread(target=do_upload, daemon=True).start()

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
            self.ftp_creds = {"host": host, "port": port, "user": user, "password": password}
            self._ftp_connect(host, port, user, password)

            self.ftp_status_var.set(f"Connected to {host}")
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            messagebox.showinfo("Success", f"Connected to {host}")

        except Exception as e:
            self.ftp = None
            messagebox.showerror("Connection Error", str(e))

    def _ftp_connect(self, host, port, user, password):
        """Low-level FTP connect + login + passive mode."""
        self.ftp = FTP()
        self.ftp.connect(host, port, timeout=30)
        if user:
            self.ftp.login(user, password)
        else:
            self.ftp.login()
        self.ftp.set_pasv(True)

    def _ensure_ftp(self):
        """Check FTP connection is alive, reconnect if needed. Call inside ftp_lock."""
        if not self.ftp:
            raise ConnectionError("Not connected to FTP server")
        try:
            self.ftp.voidcmd("NOOP")
        except Exception:
            # Connection dropped, try to reconnect
            c = self.ftp_creds
            if not c:
                raise ConnectionError("FTP connection lost and no credentials to reconnect")
            self._ftp_connect(c["host"], c["port"], c["user"], c["password"])

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
        if self.mode_var.get() == "ftp":
            self.browse_ftp()
        else:
            path = filedialog.askdirectory()
            if path:
                self.path_var.set(path)

    def browse_ftp(self):
        """Show a dialog to browse FTP directories."""
        if not self.ftp:
            messagebox.showwarning("Warning", "Connect to FTP server first")
            return

        current = self.path_var.get().strip() or "/"

        try:
            with self.ftp_lock:
                self._ensure_ftp()
                self.ftp.cwd(current)
                items = []
                self.ftp.retrlines('LIST', items.append)
        except Exception as e:
            messagebox.showerror("Error", f"Could not list directory:\n{e}")
            return

        dirs = []
        for item in items:
            parts = item.split(None, 8)
            if len(parts) >= 9 and item.startswith('d'):
                name = parts[8]
                if name not in ('.', '..'):
                    dirs.append(name)
        dirs.sort()

        if not dirs:
            messagebox.showinfo("Browse FTP", f"No subdirectories in {current}")
            return

        # Simple selection dialog
        win = tk.Toplevel(self.root)
        win.title("Browse FTP Directory")
        win.geometry("400x350")
        win.transient(self.root)
        win.grab_set()

        ttk.Label(win, text=f"Current: {current}").pack(padx=10, pady=(10, 5), anchor="w")

        listbox = tk.Listbox(win, selectmode=tk.SINGLE)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Add parent directory option
        if current != "/":
            listbox.insert(tk.END, "..")
        for d in dirs:
            listbox.insert(tk.END, d)

        def on_select():
            sel = listbox.curselection()
            if not sel:
                return
            chosen = listbox.get(sel[0])
            if chosen == "..":
                new_path = "/".join(current.rstrip("/").split("/")[:-1]) or "/"
            else:
                new_path = f"{current.rstrip('/')}/{chosen}"
            self.path_var.set(new_path)
            win.destroy()

        ttk.Button(win, text="Select", command=on_select).pack(side=tk.LEFT, padx=10, pady=10)
        ttk.Button(win, text="Cancel", command=win.destroy).pack(side=tk.RIGHT, padx=10, pady=10)
        listbox.bind("<Double-1>", lambda e: on_select())

    def sort_column(self, col):
        """Sort treeview by column when header is clicked."""
        # Get all items with their full values
        items = [self.tree.item(item)["values"] for item in self.tree.get_children("")]

        # Sort - use numeric sort for line numbers
        col_index = ["file", "line", "content"].index(col)
        if col == "line":
            items.sort(key=lambda x: int(x[col_index]) if str(x[col_index]).isdigit() else 0,
                       reverse=self.sort_reverse[col])
        else:
            items.sort(key=lambda x: str(x[col_index]).lower(), reverse=self.sort_reverse[col])

        # Delete all and reinsert in sorted order (O(n) vs O(n²) for move)
        self.tree.delete(*self.tree.get_children(""))
        for values in items:
            self.tree.insert("", tk.END, values=values)

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
                with self.ftp_lock:
                    self._ensure_ftp()
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
                with self.ftp_lock:
                    self._ensure_ftp()
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
