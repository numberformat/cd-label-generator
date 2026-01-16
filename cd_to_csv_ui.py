import os
import string
import sys
import tkinter as tk
from tkinter import ttk


def detect_drives():
    """Return a list of mounted drives/roots on the current platform."""
    if sys.platform.startswith("win"):
        drives = []
        for letter in string.ascii_uppercase:
            path = f"{letter}:\\"
            if os.path.exists(path):
                drives.append(path)
        return drives

    if sys.platform == "darwin":
        base = "/Volumes"
        if os.path.isdir(base):
            return [os.path.join(base, name) for name in sorted(os.listdir(base))]
        return ["/"]

    # Linux and other UNIX-like systems
    mount_points = ["/", "/mnt", "/media"]
    drives = []
    for root in mount_points:
        if os.path.isdir(root):
            drives.append(root)
            for name in sorted(os.listdir(root)):
                drives.append(os.path.join(root, name))
    return drives


class CDToCSVModal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CD Label Generator")
        self.resizable(True, True)

        self._init_geometry()
        self._init_widgets()
        self.after(0, self._bring_to_front)

    def _init_geometry(self):
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = screen_w // 2
        height = screen_h // 2
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _init_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        container = ttk.Frame(self, padding=16)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        top_bar = ttk.Frame(container)
        top_bar.grid(row=0, column=0, sticky="ne")
        top_bar.columnconfigure(1, weight=1)

        ttk.Label(top_bar, text="Drive:").grid(row=0, column=0, padx=(0, 8), pady=4, sticky="w")
        self.drive_var = tk.StringVar(value="Select a drive")
        self.drive_combo = ttk.Combobox(
            top_bar,
            textvariable=self.drive_var,
            values=[],
            state="readonly",
            width=40,
        )
        self.drive_combo.grid(row=0, column=1, sticky="e", pady=4)

        ttk.Label(top_bar, text="Printer:").grid(row=1, column=0, padx=(0, 8), pady=4, sticky="w")
        self.printer_var = tk.StringVar(value="Select a printer")
        self.printer_combo = ttk.Combobox(
            top_bar,
            textvariable=self.printer_var,
            values=[],
            state="readonly",
            width=40,
        )
        self.printer_combo.grid(row=1, column=1, sticky="e", pady=4)

        ttk.Label(top_bar, text="Discog ID:").grid(row=2, column=0, padx=(0, 8), pady=4, sticky="w")
        self.discog_var = tk.StringVar()
        discog_entry = ttk.Entry(top_bar, textvariable=self.discog_var, width=40)
        discog_entry.grid(row=2, column=1, sticky="e", pady=4)

        ttk.Label(top_bar, text="Email:").grid(row=3, column=0, padx=(0, 8), pady=4, sticky="w")
        self.email_var = tk.StringVar(value="you@example.com")
        email_entry = ttk.Entry(top_bar, textvariable=self.email_var, width=40)
        email_entry.grid(row=3, column=1, sticky="e", pady=4)

        form = ttk.Frame(container)
        form.grid(row=1, column=0, sticky="ew", pady=(12, 8))
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)
        form.columnconfigure(4, weight=0)

        self.artist_var = tk.StringVar()
        self.album_var = tk.StringVar()
        self.year_var = tk.StringVar()
        self.genre_var = tk.StringVar()

        ttk.Label(form, text="Artist:").grid(row=0, column=0, padx=(0, 8), pady=4, sticky="w")
        ttk.Entry(form, textvariable=self.artist_var).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Year:").grid(row=0, column=2, padx=(16, 8), pady=4, sticky="w")
        ttk.Entry(form, textvariable=self.year_var).grid(row=0, column=3, sticky="ew", pady=4)

        ttk.Label(form, text="Album:").grid(row=1, column=0, padx=(0, 8), pady=4, sticky="w")
        ttk.Entry(form, textvariable=self.album_var).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Genre:").grid(row=1, column=2, padx=(16, 8), pady=4, sticky="w")
        ttk.Entry(form, textvariable=self.genre_var).grid(row=1, column=3, sticky="ew", pady=4)

        self.search_button = ColorButton(
            form,
            text="Search",
            fill="#6b7280",
            hover="#4b5563",
            command=self._on_search,
        )
        self.search_button.grid(row=0, column=4, rowspan=2, padx=(12, 0), pady=4, sticky="e")

        ttk.Label(form, text="MBID:").grid(row=2, column=0, padx=(0, 8), pady=4, sticky="w")
        self.mbid_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.mbid_var).grid(row=2, column=1, columnspan=4, sticky="ew", pady=4)

        ttk.Label(form, text="CSV output:").grid(row=3, column=0, padx=(0, 8), pady=4, sticky="w")
        self.output_var = tk.StringVar(value=os.path.abspath("cd_output.csv"))
        output_entry = ttk.Entry(form, textvariable=self.output_var, state="readonly")
        output_entry.grid(row=3, column=1, columnspan=4, sticky="ew", pady=4)

        ttk.Label(form, text="Output:").grid(row=4, column=0, padx=(0, 8), pady=4, sticky="nw")
        self.output_text = tk.Text(form, height=10, wrap="word")
        self.output_text.grid(row=4, column=1, columnspan=4, sticky="ew", pady=4)

        buttons = ttk.Frame(container)
        buttons.grid(row=2, column=0, sticky="s", pady=(0, 8))

        self.prev_button = ColorButton(
            buttons,
            text="Previous",
            fill="#6b7280",
            hover="#4b5563",
            command=self._on_prev,
        )
        self.prev_button.grid(row=0, column=0, padx=(0, 12))

        self.next_button = ColorButton(
            buttons,
            text="Next",
            fill="#6b7280",
            hover="#4b5563",
            command=self._on_next,
        )
        self.next_button.grid(row=0, column=1, padx=(0, 12))

        self.eject_button = ColorButton(
            buttons,
            text="Eject",
            fill="#6b7280",
            hover="#4b5563",
            command=self._on_eject,
        )
        self.eject_button.grid(row=0, column=2, padx=(0, 12))

        self.append_button = ColorButton(
            buttons,
            text="Append",
            fill="#6b7280",
            hover="#4b5563",
            command=self._on_append,
        )
        self.append_button.grid(row=0, column=3, padx=(0, 12))

        self.action_button = ColorButton(
            buttons,
            text="Print",
            fill="#1a8f3c",
            hover="#167a33",
            command=self._on_run,
        )
        self.action_button.grid(row=0, column=4)

        self.after(50, self._populate_drives)

    def _populate_drives(self):
        drives = detect_drives()
        if drives:
            self.drive_combo.configure(values=drives)
            self.drive_var.set(drives[0])
        else:
            self.drive_var.set("No drives found")

    def _bring_to_front(self):
        self.lift()
        try:
            self.attributes("-topmost", True)
            self.after(100, lambda: self.attributes("-topmost", False))
        except tk.TclError:
            pass
        self.focus_force()

    def _on_run(self):
        pass

    def _on_append(self):
        pass

    def _on_eject(self):
        pass

    def _on_prev(self):
        pass

    def _on_next(self):
        pass

    def _on_search(self):
        pass


class ColorButton(ttk.Frame):
    def __init__(self, master, text, fill, hover, command=None):
        super().__init__(master)
        self.command = command
        self.fill = fill
        self.hover = hover
        self.canvas = tk.Canvas(self, width=120, height=42, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Button-1>", self._invoke)
        self.canvas.bind("<Enter>", lambda _event: self._draw(hover=True))
        self.canvas.bind("<Leave>", lambda _event: self._draw(hover=False))
        self._text = text
        self._draw(hover=False)

    def _draw(self, hover):
        self.canvas.delete("all")
        color = self.hover if hover else self.fill
        self.canvas.create_rectangle(0, 0, 120, 42, fill=color, outline=color)
        self.canvas.create_text(
            60,
            21,
            text=self._text,
            fill="white",
            font=("Helvetica", 12, "bold"),
        )

    def _invoke(self, _event):
        if self.command:
            self.command()


if __name__ == "__main__":
    CDToCSVModal().mainloop()
