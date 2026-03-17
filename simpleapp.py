import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

SAMPLE_DATA = [
    {"title": "Freefall Over Alps", "type": "Video", "date": "2025-06-15", "altitude": "14,000 ft", "tags": "scenery, group"},
    {"title": "Solo Jump #42", "type": "Video", "date": "2025-08-03", "altitude": "12,500 ft", "tags": "solo, sunset"},
    {"title": "Team Formation", "type": "Photo", "date": "2025-09-20", "altitude": "13,000 ft", "tags": "formation, team"},
    {"title": "Opening Shot", "type": "Photo", "date": "2025-10-01", "altitude": "10,000 ft", "tags": "canopy, landscape"},
    {"title": "Night Jump", "type": "Video", "date": "2025-11-12", "altitude": "15,000 ft", "tags": "night, lights"},
]


class SkyMediaHub(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SkyDive Media Hub")
        self.geometry("900x600")
        self.configure(bg="#0d1117")
        self.resizable(True, True)

        self.media_items = list(SAMPLE_DATA)
        self.filter_var = tk.StringVar(value="All")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh_list())

        self._build_ui()
        self.refresh_list()

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg="#161b22", pady=12)
        header.pack(fill="x")

        tk.Label(
            header, text="SkyDive Media Hub", font=("Helvetica", 20, "bold"),
            fg="#58a6ff", bg="#161b22"
        ).pack(side="left", padx=20)

        tk.Label(
            header, text="Your skydiving memories, organized.", font=("Helvetica", 10),
            fg="#8b949e", bg="#161b22"
        ).pack(side="left", padx=4, pady=6)

        # Toolbar
        toolbar = tk.Frame(self, bg="#0d1117", pady=8)
        toolbar.pack(fill="x", padx=16)

        tk.Label(toolbar, text="Search:", fg="#c9d1d9", bg="#0d1117").pack(side="left")
        search_entry = tk.Entry(
            toolbar, textvariable=self.search_var, width=28,
            bg="#21262d", fg="#c9d1d9", insertbackground="#58a6ff",
            relief="flat", bd=4
        )
        search_entry.pack(side="left", padx=(4, 16))

        tk.Label(toolbar, text="Filter:", fg="#c9d1d9", bg="#0d1117").pack(side="left")
        for label in ("All", "Video", "Photo"):
            tk.Radiobutton(
                toolbar, text=label, variable=self.filter_var, value=label,
                command=self.refresh_list, bg="#0d1117", fg="#c9d1d9",
                selectcolor="#21262d", activebackground="#0d1117",
                activeforeground="#58a6ff"
            ).pack(side="left", padx=4)

        tk.Button(
            toolbar, text="+ Add Media", command=self.add_media,
            bg="#238636", fg="white", relief="flat", padx=10, pady=4,
            cursor="hand2", activebackground="#2ea043"
        ).pack(side="right")

        # Table
        frame = tk.Frame(self, bg="#0d1117")
        frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background="#161b22", foreground="#c9d1d9",
                        fieldbackground="#161b22", rowheight=28, font=("Helvetica", 10))
        style.configure("Treeview.Heading", background="#21262d", foreground="#8b949e",
                        font=("Helvetica", 10, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", "#1f6feb")])

        columns = ("title", "type", "date", "altitude", "tags")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")

        for col, heading, width in [
            ("title", "Title", 220), ("type", "Type", 70), ("date", "Date", 100),
            ("altitude", "Altitude", 100), ("tags", "Tags", 200)
        ]:
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, anchor="w")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<Delete>", lambda _: self.delete_selected())

        # Status bar
        self.status_var = tk.StringVar()
        tk.Label(
            self, textvariable=self.status_var, fg="#8b949e", bg="#161b22",
            anchor="w", padx=16, pady=4
        ).pack(fill="x", side="bottom")

    def refresh_list(self):
        query = self.search_var.get().lower()
        media_filter = self.filter_var.get()

        self.tree.delete(*self.tree.get_children())
        shown = 0
        for item in self.media_items:
            if media_filter != "All" and item["type"] != media_filter:
                continue
            if query and query not in item["title"].lower() and query not in item["tags"].lower():
                continue
            tag = "video" if item["type"] == "Video" else "photo"
            self.tree.insert("", "end", values=(
                item["title"], item["type"], item["date"], item["altitude"], item["tags"]
            ), tags=(tag,))
            shown += 1

        self.tree.tag_configure("video", foreground="#79c0ff")
        self.tree.tag_configure("photo", foreground="#56d364")
        total = len(self.media_items)
        self.status_var.set(f"Showing {shown} of {total} items  •  Press Delete to remove selected")

    def add_media(self):
        AddDialog(self)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        title = values[0]
        if messagebox.askyesno("Delete", f"Remove '{title}' from the hub?"):
            self.media_items = [m for m in self.media_items if m["title"] != title]
            self.refresh_list()


class AddDialog(tk.Toplevel):
    def __init__(self, parent: SkyMediaHub):
        super().__init__(parent)
        self.parent = parent
        self.title("Add Media")
        self.geometry("380x300")
        self.configure(bg="#161b22")
        self.resizable(False, False)
        self.grab_set()

        fields = [
            ("Title", "title", None),
            ("Type", "type", ["Video", "Photo"]),
            ("Date (YYYY-MM-DD)", "date", None),
            ("Altitude", "altitude", None),
            ("Tags (comma-separated)", "tags", None),
        ]

        self.vars: dict[str, tk.StringVar] = {}
        for i, (label, key, options) in enumerate(fields):
            tk.Label(self, text=label, fg="#8b949e", bg="#161b22", anchor="w").grid(
                row=i, column=0, padx=16, pady=6, sticky="w"
            )
            var = tk.StringVar(value="Video" if key == "type" else "")
            self.vars[key] = var
            if options:
                widget = ttk.Combobox(self, textvariable=var, values=options, state="readonly", width=22)
            else:
                widget = tk.Entry(self, textvariable=var, bg="#21262d", fg="#c9d1d9",
                                  insertbackground="#58a6ff", relief="flat", bd=4, width=24)
            widget.grid(row=i, column=1, padx=8, pady=6, sticky="w")

        tk.Button(
            self, text="Add", command=self.submit,
            bg="#238636", fg="white", relief="flat", padx=16, pady=6,
            cursor="hand2", activebackground="#2ea043"
        ).grid(row=len(fields), column=0, columnspan=2, pady=12)

    def submit(self):
        data = {k: v.get().strip() for k, v in self.vars.items()}
        if not data["title"]:
            messagebox.showwarning("Missing", "Title is required.", parent=self)
            return
        if not data["date"]:
            data["date"] = datetime.today().strftime("%Y-%m-%d")
        if not data["altitude"]:
            data["altitude"] = "—"
        self.parent.media_items.append(data)
        self.parent.refresh_list()
        self.destroy()


if __name__ == "__main__":
    app = SkyMediaHub()
    app.mainloop()
