import os
import sys
import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

VENV_SITE_PACKAGES = (
    Path(__file__).resolve().parents[1]
    / "venv"
    / "lib"
    / f"python{sys.version_info.major}.{sys.version_info.minor}"
    / "site-packages"
)
if VENV_SITE_PACKAGES.exists() and str(VENV_SITE_PACKAGES) not in sys.path:
    sys.path.append(str(VENV_SITE_PACKAGES))

import yt_dlp

from .helpers import append_textbox


class YouTubeDownloadTab:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self.download_dir = os.getcwd()
        self.video_progress_widgets = {}
        self.current_video_key = None

        self._build_ui()
        self.append_log(f"Thu muc luu mac dinh: {self.download_dir}")

    def _build_ui(self):
        title = ctk.CTkLabel(
            self.parent,
            text="Tai video YouTube",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.pack(pady=(16, 10))

        self.link_entry = ctk.CTkEntry(
            self.parent,
            placeholder_text="Nhap link YouTube...",
            width=820,
        )
        self.link_entry.pack(pady=10, padx=20)

        dir_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        dir_frame.pack(fill="x", padx=20, pady=10)

        self.download_dir_entry = ctk.CTkEntry(dir_frame, width=680)
        self.download_dir_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.download_dir_entry.insert(0, self.download_dir)

        ctk.CTkButton(
            dir_frame,
            text="Chon thu muc luu",
            command=self.choose_download_dir,
            width=140,
        ).pack(side="left")

        self.download_button = ctk.CTkButton(
            self.parent,
            text="Bat dau tai",
            command=self.start_download,
            width=220,
        )
        self.download_button.pack(pady=10)

        self.log_box = ctk.CTkTextbox(self.parent, height=180, width=860)
        self.log_box.pack(padx=20, pady=(10, 10), fill="x")

        self.progress_container = ctk.CTkScrollableFrame(self.parent, width=860, height=250)
        self.progress_container.pack(padx=20, pady=(0, 20), fill="both", expand=True)

    def append_log(self, text):
        append_textbox(self.app, self.log_box, text)

    def set_button_state(self, text, state):
        def _update():
            self.download_button.configure(text=text, state=state)

        self.app.after(0, _update)

    def set_entry_value(self, entry, value):
        entry.delete(0, "end")
        entry.insert(0, value)

    def create_video_progress(self, video_key, title_text):
        def _create():
            if video_key in self.video_progress_widgets:
                return

            frame = ctk.CTkFrame(self.progress_container)
            frame.pack(fill="x", padx=5, pady=5)

            title_label = ctk.CTkLabel(frame, text=title_text, anchor="w")
            title_label.pack(fill="x", padx=10, pady=(8, 2))

            progress_bar = ctk.CTkProgressBar(frame, width=780)
            progress_bar.pack(padx=10, pady=5, fill="x")
            progress_bar.set(0)

            info_label = ctk.CTkLabel(frame, text="0 MB / ? MB (0%)", anchor="w")
            info_label.pack(fill="x", padx=10, pady=(0, 8))

            self.video_progress_widgets[video_key] = {
                "progress_bar": progress_bar,
                "info_label": info_label,
            }

        self.app.after(0, _create)

    def update_video_progress(self, video_key, progress_value, info_text):
        def _update():
            widgets = self.video_progress_widgets.get(video_key)
            if not widgets:
                return
            widgets["progress_bar"].set(max(0, min(1, progress_value)))
            widgets["info_label"].configure(text=info_text)

        self.app.after(0, _update)

    def finish_video_progress(self, video_key, info_text="Hoan tat"):
        def _finish():
            widgets = self.video_progress_widgets.get(video_key)
            if not widgets:
                return
            widgets["progress_bar"].set(1)
            widgets["info_label"].configure(text=info_text)

        self.app.after(0, _finish)

    def fail_video_progress(self, video_key, info_text="Tai that bai"):
        def _fail():
            widgets = self.video_progress_widgets.get(video_key)
            if not widgets:
                return
            widgets["info_label"].configure(text=info_text)

        self.app.after(0, _fail)

    def choose_download_dir(self):
        selected = filedialog.askdirectory(initialdir=self.download_dir)
        if selected:
            self.download_dir = selected
            self.set_entry_value(self.download_dir_entry, selected)
            self.append_log(f"Thu muc luu: {selected}")

    def format_bytes(self, byte_count):
        try:
            size = float(byte_count or 0)
        except (TypeError, ValueError):
            size = 0.0

        if size >= 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024 * 1024):.2f} GB"
        return f"{size / (1024 * 1024):.2f} MB"

    def progress_hook(self, data):
        video_key = self.current_video_key
        if not video_key:
            return

        status = data.get("status")
        if status == "downloading":
            downloaded = data.get("downloaded_bytes") or 0
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            speed = data.get("_speed_str", "").strip() or "?"
            eta = data.get("_eta_str", "").strip() or "?"

            if total:
                progress = downloaded / total
                info_text = (
                    f"{self.format_bytes(downloaded)} / {self.format_bytes(total)} "
                    f"({progress * 100:.1f}%) | {speed} | ETA {eta}"
                )
            else:
                progress = 0
                info_text = f"{self.format_bytes(downloaded)} / ? | {speed} | ETA {eta}"

            self.update_video_progress(video_key, progress, info_text)
        elif status == "finished":
            filename = os.path.basename(data.get("filename", ""))
            self.update_video_progress(video_key, 1, f"Da tai xong stream, dang xu ly file: {filename}")

    def download_video(self):
        self.set_button_state("Dang tai...", "disabled")
        video_url = self.link_entry.get().strip()
        self.download_dir = self.download_dir_entry.get().strip() or self.download_dir

        try:
            if not video_url:
                self.append_log("Vui long nhap link YouTube.")
                return

            os.makedirs(self.download_dir, exist_ok=True)
            self.append_log(f"Bat dau tai YouTube: {video_url}")
            self.current_video_key = video_url
            self.create_video_progress(self.current_video_key, f"Tai YouTube: {video_url}")

            ydl_opts = {
                "format": "bv*+ba/b",
                "merge_output_format": "mp4",
                "outtmpl": os.path.join(self.download_dir, "%(title).200s [%(id)s].%(ext)s"),
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "progress_hooks": [self.progress_hook],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)

            title = info.get("title") or "video"
            self.finish_video_progress(self.current_video_key, "Hoan tat")
            self.append_log(f"Hoan tat: {title}")
        except Exception as exc:
            if self.current_video_key:
                self.fail_video_progress(self.current_video_key, "Tai that bai")
            self.append_log(f"Loi tai YouTube: {exc}")
        finally:
            self.current_video_key = None
            self.set_button_state("Bat dau tai", "normal")

    def start_download(self):
        threading.Thread(target=self.download_video, daemon=True).start()
