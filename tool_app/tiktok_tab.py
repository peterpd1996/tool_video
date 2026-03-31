import os
import re
import threading
import time
import traceback
from tkinter import filedialog

import customtkinter as ctk
import requests
import yt_dlp

from .helpers import append_textbox, ensure_unique_filepath, sanitize_filename


class TikTokDownloadTab:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self.download_dir = os.getcwd()
        self.video_progress_widgets = {}

        self._build_ui()
        self.append_log(f"Thu muc luu mac dinh: {self.download_dir}")

    def _build_ui(self):
        self.parent.columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            self.parent,
            text="Tai video TikTok khong watermark",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.pack(pady=(16, 10))

        self.link_entry = ctk.CTkEntry(
            self.parent,
            placeholder_text="Nhap link video hoac channel TikTok...",
            width=820,
        )
        self.link_entry.pack(pady=10, padx=20)

        self.download_type = ctk.StringVar(value="video")
        radio_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        radio_frame.pack(pady=5)
        ctk.CTkRadioButton(
            radio_frame, text="Tai 1 video", variable=self.download_type, value="video"
        ).pack(side="left", padx=10)
        ctk.CTkRadioButton(
            radio_frame, text="Tai toan bo channel", variable=self.download_type, value="channel"
        ).pack(side="left", padx=10)

        dir_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        dir_frame.pack(fill="x", padx=20, pady=10)

        self.download_dir_entry = ctk.CTkEntry(dir_frame, width=680)
        self.download_dir_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.download_dir_entry.insert(0, self.download_dir)

        ctk.CTkButton(
            dir_frame, text="Chon thu muc luu", command=self.choose_download_dir, width=140
        ).pack(side="left")
        ctk.CTkButton(self.parent, text="Bat dau tai", command=self.start_download, width=220).pack(pady=10)

        self.log_box = ctk.CTkTextbox(self.parent, height=180, width=860)
        self.log_box.pack(padx=20, pady=(10, 10), fill="x")

        self.progress_container = ctk.CTkScrollableFrame(self.parent, width=860, height=220)
        self.progress_container.pack(padx=20, pady=(0, 15), fill="both", expand=True)

    def append_log(self, text):
        append_textbox(self.app, self.log_box, text)

    def is_valid_video_url(self, url):
        return re.match(r"https://www\.tiktok\.com/@[^/]+/video/\d+", url)

    def is_valid_channel_url(self, url):
        return re.match(r"https://www\.tiktok\.com/@[^/]+/?$", url)

    def set_entry_value(self, entry, value):
        entry.delete(0, "end")
        entry.insert(0, value)

    def choose_download_dir(self):
        selected = filedialog.askdirectory(initialdir=self.download_dir)
        if selected:
            self.download_dir = selected
            self.set_entry_value(self.download_dir_entry, selected)
            self.append_log(f"Thu muc luu: {selected}")

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

    def get_video_urls_from_channel(self, channel_url):
        ydl_opts = {
            "quiet": True,
            "extract_flat": True,
            "skip_download": True,
            "force_generic_extractor": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(channel_url, download=False)
            if "entries" not in result:
                return []
            video_urls = []
            for entry in result["entries"]:
                if "url" in entry:
                    video_url = entry["url"]
                    if not video_url.startswith("http"):
                        video_url = f"https://www.tiktok.com{video_url}"
                    video_urls.append(video_url)
            return video_urls

    def download_tiktok_by_ttdownloader(self, video_url):
        video_key = None
        try:
            self.append_log(f"Dang xu ly: {video_url}")

            try:
                with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    title = info.get("title", "tiktok_video")
                    view_count = info.get("view_count", 0)

                safe_title = "".join(
                    c for c in title if c.isalnum() or c in (" ", "_", "-")
                ).rstrip()
                file_name = sanitize_filename(f"{view_count}views_{safe_title}") + ".mp4"
            except Exception as exc:
                self.append_log(f"yt_dlp loi, dung ten mac dinh: {exc}")
                file_name = "tiktok_video.mp4"

            file_path = ensure_unique_filepath(os.path.join(self.download_dir, file_name))
            video_key = file_path
            self.create_video_progress(video_key, f"Tai: {os.path.basename(file_path)}")

            res = requests.post(
                "https://www.tikwm.com/api/video/task/submit",
                headers={"accept": "application/json"},
                data={"url": video_url, "web": 1},
                timeout=60,
            )

            if res.status_code != 200:
                self.append_log(f"Loi khi gui request: HTTP {res.status_code}")
                self.fail_video_progress(video_key, f"Loi submit: HTTP {res.status_code}")
                return

            resp_json = res.json()
            if resp_json.get("code") != 0:
                self.append_log(f"API tra ve loi: {resp_json.get('msg')}")
                self.fail_video_progress(video_key, f"API loi: {resp_json.get('msg')}")
                return

            task_id = resp_json.get("data", {}).get("task_id")
            if not task_id:
                self.append_log("Khong tim thay task_id trong response")
                self.fail_video_progress(video_key, "Khong co task_id")
                return

            self.append_log(f"Task submit thanh cong: {task_id}")

            res2 = requests.get(
                f"https://www.tikwm.com/api/video/task/result?task_id={task_id}",
                headers={"accept": "application/json"},
                timeout=60,
            )

            if res2.status_code != 200:
                self.append_log(f"Loi khi goi API result: HTTP {res2.status_code}")
                self.fail_video_progress(video_key, f"Loi result: HTTP {res2.status_code}")
                return

            result = res2.json()
            if result.get("code") != 0:
                self.append_log(f"API result tra ve loi: {result.get('msg')}")
                self.fail_video_progress(video_key, f"Result API loi: {result.get('msg')}")
                return

            detail = result.get("data", {}).get("detail", {})
            download_link = detail.get("download_url")
            if not download_link:
                self.append_log("Khong tim thay download_url trong response")
                self.fail_video_progress(video_key, "Khong co download_url")
                return

            self.append_log(f"Bat dau tai: {os.path.basename(file_path)}")

            with requests.get(download_link, stream=True, timeout=120) as response, open(file_path, "wb") as file_obj:
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))
                downloaded_size = 0
                last_update = 0

                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue

                    file_obj.write(chunk)
                    downloaded_size += len(chunk)

                    now = time.time()
                    if now - last_update >= 0.2:
                        downloaded_mb = downloaded_size / (1024 * 1024)
                        if total_size > 0:
                            total_mb = total_size / (1024 * 1024)
                            percent = downloaded_size / total_size
                            self.update_video_progress(
                                video_key,
                                percent,
                                f"{downloaded_mb:.2f} / {total_mb:.2f} MB ({percent * 100:.1f}%)",
                            )
                        else:
                            self.update_video_progress(video_key, 0, f"{downloaded_mb:.2f} MB / ?")
                        last_update = now

            self.finish_video_progress(video_key, "Hoan tat")
            self.append_log(f"Da tai xong: {os.path.basename(file_path)}")
        except Exception:
            if video_key:
                self.fail_video_progress(video_key, "Tai that bai")
            self.append_log(f"Loi: {traceback.format_exc()}")

    def start_download(self):
        url = self.link_entry.get().strip()
        mode = self.download_type.get()

        if not url:
            self.append_log("Vui long nhap link video hoac channel.")
            return

        def task():
            try:
                if mode == "video":
                    if not self.is_valid_video_url(url):
                        self.append_log("Link khong dung dinh dang video TikTok.")
                        return
                    self.download_tiktok_by_ttdownloader(url)
                else:
                    if not self.is_valid_channel_url(url):
                        self.append_log("Link khong dung dinh dang channel TikTok.")
                        return
                    self.append_log("Dang lay danh sach video tu channel...")
                    video_urls = self.get_video_urls_from_channel(url)
                    if not video_urls:
                        self.append_log("Khong tim thay video.")
                        return
                    self.append_log(f"Tim thay {len(video_urls)} video.")
                    for index, video_url in enumerate(video_urls, start=1):
                        self.append_log(f"Xu ly {index}/{len(video_urls)}")
                        self.download_tiktok_by_ttdownloader(video_url)
                    self.append_log("Da tai xong tat ca video.")
            except Exception:
                self.append_log(f"Loi chinh: {traceback.format_exc()}")

        threading.Thread(target=task, daemon=True).start()

