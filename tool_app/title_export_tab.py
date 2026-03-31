import os
import re
import threading
from tkinter import filedialog

import customtkinter as ctk

from .config import VIDEO_EXTENSIONS
from .helpers import append_textbox


class TitleExportTab:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self.source_dir = os.getcwd()
        self.output_file = os.path.join(os.getcwd(), "video_titles.txt")

        self._build_ui()
        self.append_log(f"Thu muc nguon mac dinh: {self.source_dir}")
        self.append_log(f"File xuat mac dinh: {self.output_file}")

    def _build_ui(self):
        title = ctk.CTkLabel(
            self.parent,
            text="Export tieu de video",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.pack(pady=(16, 10))

        note = ctk.CTkLabel(
            self.parent,
            text="Chon thu muc chua video, tool se lay tieu de tu ten file va xuat ra mot file danh sach.",
            wraplength=820,
            justify="left",
        )
        note.pack(padx=20, pady=(0, 10), anchor="w")

        source_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        source_frame.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(source_frame, text="Thu muc video", width=120, anchor="w").pack(side="left")
        self.source_entry = ctk.CTkEntry(source_frame, width=620)
        self.source_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.source_entry.insert(0, self.source_dir)
        ctk.CTkButton(source_frame, text="Chon nguon", command=self.choose_source_dir, width=120).pack(side="left")

        output_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        output_frame.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(output_frame, text="File xuat", width=120, anchor="w").pack(side="left")
        self.output_entry = ctk.CTkEntry(output_frame, width=620)
        self.output_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.output_entry.insert(0, self.output_file)
        ctk.CTkButton(output_frame, text="Chon file", command=self.choose_output_file, width=120).pack(side="left")

        ctk.CTkButton(self.parent, text="Export tieu de", command=self.start_export, width=220).pack(pady=8)

        self.log_box = ctk.CTkTextbox(self.parent, height=360, width=860)
        self.log_box.pack(padx=20, pady=(10, 20), fill="both", expand=True)

    def append_log(self, text):
        append_textbox(self.app, self.log_box, text)

    def set_entry_value(self, entry, value):
        entry.delete(0, "end")
        entry.insert(0, value)

    def choose_source_dir(self):
        selected = filedialog.askdirectory(initialdir=self.source_dir)
        if selected:
            self.source_dir = selected
            self.set_entry_value(self.source_entry, selected)
            self.append_log(f"Thu muc video: {selected}")

    def choose_output_file(self):
        selected = filedialog.asksaveasfilename(
            initialdir=os.path.dirname(self.output_file),
            initialfile=os.path.basename(self.output_file),
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("Markdown", "*.md")],
        )
        if selected:
            self.output_file = selected
            self.set_entry_value(self.output_entry, selected)
            self.append_log(f"File xuat: {selected}")

    def list_videos(self, folder_path):
        return sorted(
            os.path.join(folder_path, name)
            for name in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, name)) and name.lower().endswith(VIDEO_EXTENSIONS)
        )

    def clean_title_from_filename(self, file_path):
        stem = os.path.splitext(os.path.basename(file_path))[0]
        stem = re.sub(r"[_\-\s]?\d+$", "", stem)
        stem = re.sub(r"^\d+\s*views[_\-\s]*", "", stem, flags=re.IGNORECASE)
        stem = re.sub(r"\s+", " ", stem.replace("_", " ").replace("-", " ")).strip()
        return stem or os.path.basename(file_path)

    def build_export_content(self, titles, source_dir):
        lines = [
            f"Thu muc nguon: {source_dir}",
            f"Tong video: {len(titles)}",
            "",
        ]
        lines.extend(title for title in titles)
        return "\n".join(lines).strip() + "\n"

    def export_titles(self):
        self.source_dir = self.source_entry.get().strip() or self.source_dir
        self.output_file = self.output_entry.get().strip() or self.output_file

        if not self.source_dir or not os.path.isdir(self.source_dir):
            self.append_log("Thu muc video khong hop le.")
            return

        if not self.output_file:
            self.append_log("Vui long chon file xuat.")
            return

        video_files = self.list_videos(self.source_dir)
        if not video_files:
            self.append_log("Khong tim thay video nao trong thu muc.")
            return

        titles = [self.clean_title_from_filename(file_path) for file_path in video_files]
        content = self.build_export_content(titles, self.source_dir)

        os.makedirs(os.path.dirname(self.output_file) or ".", exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as file_obj:
            file_obj.write(content)

        self.append_log(f"Da quet {len(video_files)} video.")
        self.append_log(f"Da xuat file: {self.output_file}")
        for title in titles[:10]:
            self.append_log(f"- {title}")

    def start_export(self):
        threading.Thread(target=self.export_titles, daemon=True).start()
