import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import csv
from pathlib import Path

SAMPLE_DATA = [
    {"title": "Freefall Over Alps", "type": "Video", "date": "2025-06-15", "altitude": "14,000 ft", "tags": "scenery, group", "rating": 5, "favorite": True},
    {"title": "Solo Jump #42", "type": "Video", "date": "2025-08-03", "altitude": "12,500 ft", "tags": "solo, sunset", "rating": 4, "favorite": False},
    {"title": "Team Formation", "type": "Photo", "date": "2025-09-20", "altitude": "13,000 ft", "tags": "formation, team", "rating": 5, "favorite": True},
    {"title": "Opening Shot", "type": "Photo", "date": "2025-10-01", "altitude": "10,000 ft", "tags": "canopy, landscape", "rating": 3, "favorite": False},
    {"title": "Night Jump", "type": "Video", "date": "2025-11-12", "altitude": "15,000 ft", "tags": "night, lights", "rating": 4, "favorite": False},
]


class SkyMediaHub(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SkyDive Media Hub")
        self.geometry("1000x650")
        self.configure(bg="#0d1117")
        self.resizable(True, True)

        self.media_items = list(SAMPLE_DATA)
        self.filter_var = tk.StringVar(value="All")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh_list())

        self._build_ui()
        self.refresh_list()

    def _build_ui(self):
        # Menu bar
        menubar = tk.Menu(self, bg="#161b22", fg="#c9d1d9")
        self.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, bg="#161b22", fg="#c9d1d9", tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export to CSV", command=self.export_csv)
        file_menu.add_command(label="Import from CSV", command=self.import_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        
        view_menu = tk.Menu(menubar, bg="#161b22", fg="#c9d1d9", tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Show Statistics", command=self.show_stats)

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

        columns = ("title", "type", "date", "altitude", "rating", "favorite", "tags")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")

        for col, heading, width in [
            ("title", "Title", 180), ("type", "Type", 70), ("date", "Date", 100),
            ("altitude", "Altitude", 100), ("rating", "Rating", 60), ("favorite", "★", 40), ("tags", "Tags", 170)
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
            fav_icon = "★" if item.get("favorite", False) else "☆"
            rating = item.get("rating", 0)
            self.tree.insert("", "end", values=(
                item["title"], item["type"], item["date"], item["altitude"],
                f"{rating}/5", fav_icon, item["tags"]
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

    def export_csv(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"skydive_media_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        if not file_path:
            return
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ["title", "type", "date", "altitude", "rating", "favorite", "tags"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.media_items)
            messagebox.showinfo("Success", f"Data exported to {Path(file_path).name}")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")

    def import_csv(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                imported = list(reader)
                for item in imported:
                    item["rating"] = int(item.get("rating", 0))
                    item["favorite"] = item.get("favorite", "").lower() == "true"
                self.media_items.extend(imported)
            messagebox.showinfo("Success", f"Imported {len(imported)} items")
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("Error", f"Import failed: {e}")

    def show_stats(self):
        StatsWindow(self, self.media_items)


class StatsWindow(tk.Toplevel):
    def __init__(self, parent, media_items):
        super().__init__(parent)
        self.title("Statistics & Analytics")
        self.geometry("450x400")
        self.configure(bg="#161b22")
        self.resizable(False, False)

        # Calculate stats
        total = len(media_items)
        videos = sum(1 for m in media_items if m["type"] == "Video")
        photos = total - videos
        avg_rating = sum(m.get("rating", 0) for m in media_items) / total if total > 0 else 0
        favorites = sum(1 for m in media_items if m.get("favorite", False))
        
        tags_list = []
        for m in media_items:
            tags_list.extend([t.strip() for t in m["tags"].split(",")])
        popular_tags = sorted(set(tags_list), key=lambda x: tags_list.count(x), reverse=True)[:5]

        # Display stats
        stats_frame = tk.Frame(self, bg="#161b22")
        stats_frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(stats_frame, text="📊 Collection Statistics", font=("Helvetica", 14, "bold"),
                fg="#58a6ff", bg="#161b22").pack(anchor="w", pady=(0, 12))

        stats = [
            (f"Total Items", f"{total}"),
            (f"Videos", f"{videos}"),
            (f"Photos", f"{photos}"),
            (f"Average Rating", f"{avg_rating:.1f} / 5"),
            (f"Favorite Items", f"{favorites}"),
        ]

        for label, value in stats:
            row = tk.Frame(stats_frame, bg="#161b22")
            row.pack(fill="x", pady=6)
            tk.Label(row, text=label, fg="#8b949e", bg="#161b22", width=20, anchor="w").pack(side="left")
            tk.Label(row, text=value, fg="#79c0ff", bg="#161b22", font=("Helvetica", 11, "bold")).pack(side="left")

        tk.Label(stats_frame, text="🏷️ Top Tags", font=("Helvetica", 12, "bold"),
                fg="#56d364", bg="#161b22").pack(anchor="w", pady=(16, 8))
        
        for tag in popular_tags:
            count = tags_list.count(tag)
            tk.Label(stats_frame, text=f"  • {tag} ({count})", fg="#c9d1d9", bg="#161b22").pack(anchor="w")


class AddDialog(tk.Toplevel):
    def __init__(self, parent: SkyMediaHub):
        super().__init__(parent)
        self.parent = parent
        self.title("Add Media")
        self.geometry("380x380")
        self.configure(bg="#161b22")
        self.resizable(False, False)
        self.grab_set()

        fields = [
            ("Title", "title", None),
            ("Type", "type", ["Video", "Photo"]),
            ("Date (YYYY-MM-DD)", "date", None),
            ("Altitude", "altitude", None),
            ("Rating (1-5)", "rating", [str(i) for i in range(1, 6)]),
            ("Favorite", "favorite", ["No", "Yes"]),
            ("Tags (comma-separated)", "tags", None),
        ]

        self.vars: dict[str, tk.StringVar] = {}
        for i, (label, key, options) in enumerate(fields):
            tk.Label(self, text=label, fg="#8b949e", bg="#161b22", anchor="w").grid(
                row=i, column=0, padx=16, pady=6, sticky="w"
            )
            if key == "favorite":
                var = tk.StringVar(value="No")
            elif key == "rating":
                var = tk.StringVar(value="5")
            else:
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
        data["rating"] = int(data.get("rating", 5))
        data["favorite"] = data.get("favorite") == "Yes"
        self.parent.media_items.append(data)
        self.parent.refresh_list()
        self.destroy()


if __name__ == "__main__":
    app = SkyMediaHub()
    app.mainloop()
