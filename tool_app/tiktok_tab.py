import html
import os
import re
import threading
import time
import traceback
from tkinter import filedialog

import customtkinter as ctk
import requests

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
        match = re.match(r"https://www\.tiktok\.com/@([^/?#]+)", channel_url)
        if not match:
            return []
        unique_id = match.group(1)

        video_urls = []
        cursor = 0
        while True:
            response = requests.get(
                "https://www.tikwm.com/api/user/posts",
                params={"unique_id": unique_id, "count": 30, "cursor": cursor},
                headers={"accept": "application/json"},
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") != 0:
                raise RuntimeError(payload.get("msg") or "tikwm khong tra ve danh sach video.")

            data = payload.get("data") or {}
            for video in data.get("videos") or []:
                video_id = video.get("video_id")
                if video_id:
                    video_urls.append(f"https://www.tiktok.com/@{unique_id}/video/{video_id}")

            if not data.get("hasMore"):
                break
            cursor = data.get("cursor") or 0
            time.sleep(1)  # tikwm free gioi han ~1 request/giay

        return video_urls

    def format_view_count(self, view_count):
        try:
            count = int(view_count or 0)
        except (TypeError, ValueError):
            return "0"

        if count >= 1_000_000_000:
            value = count / 1_000_000_000
            suffix = "B"
        elif count >= 1_000_000:
            value = count / 1_000_000
            suffix = "M"
        elif count >= 1_000:
            value = count / 1_000
            suffix = "K"
        else:
            return str(count)

        if value >= 10 or value.is_integer():
            return f"{int(value)}{suffix}"
        return f"{value:.1f}{suffix}"

    def parse_count_value(self, value):
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            cleaned = re.sub(r"[,\s]", "", value.strip())
            if cleaned.isdigit():
                return int(cleaned)
        return 0

    def extract_title_and_view_count(self, info):
        info = info or {}
        title_candidates = [
            info.get("title"),
            info.get("description"),
            info.get("fulltitle"),
            info.get("alt_title"),
            info.get("id"),
        ]
        title = next((item for item in title_candidates if isinstance(item, str) and item.strip()), "tiktok_video")

        stats = info.get("stats") if isinstance(info.get("stats"), dict) else {}
        view_candidates = [
            info.get("view_count"),
            info.get("play_count"),
            stats.get("viewCount"),
            stats.get("playCount"),
            stats.get("view_count"),
            stats.get("play_count"),
        ]
        view_count = 0
        for candidate in view_candidates:
            view_count = self.parse_count_value(candidate)
            if view_count > 0:
                break

        return title, view_count

    def build_download_file_path(self, video_url):
        try:
            info = self.get_video_info(video_url)
            title, view_count = self.extract_title_and_view_count(info)

            safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).rstrip()
            formatted_views = self.format_view_count(view_count)
            file_name = sanitize_filename(f"{formatted_views}_{safe_title}") + ".mp4"
        except Exception as exc:
            self.append_log(f"Khong lay duoc thong tin video, dung ten mac dinh: {exc}")
            file_name = "tiktok_video.mp4"

        return ensure_unique_filepath(os.path.join(self.download_dir, file_name))

    def get_video_info(self, video_url):
        response = requests.get(
            "https://www.tikwm.com/api/",
            params={"url": video_url},
            headers={"accept": "application/json"},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(payload.get("msg") or "tikwm khong tra ve du lieu video.")

        data = payload.get("data") or {}
        author = data.get("author") or {}
        return {
            "id": data.get("id"),
            "title": data.get("title"),
            "description": data.get("title"),
            "view_count": data.get("play_count"),
            "duration": data.get("duration"),
            "uploader": author.get("nickname"),
            "channel": author.get("unique_id"),
            "tags": [],
        }

    def download_stream_to_file(self, download_link, file_path, video_key):
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

    def parse_snaptik_hd_link(self, html_text):
        cleaned_html = html.unescape(html_text or "")
        match = re.search(
            r'<a[^>]+href="([^"]+)"[^>]*>\s*(?:<i[^>]*></i>)?\s*Download\s+MP4\s+HD\s*</a>',
            cleaned_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if match:
            return match.group(1)

        fallback = re.search(
            r'<a[^>]+href="([^"]+)"[^>]*>\s*(?:<i[^>]*></i>)?\s*Download\s+MP4',
            cleaned_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if fallback:
            return fallback.group(1)

        return None

    def request_snaptik_download_link(self, video_url):
        endpoint = "https://snaptik.biz/api/ajaxSearch"
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "origin": "https://snaptik.biz",
            "referer": "https://snaptik.biz/en",
            "x-requested-with": "XMLHttpRequest",
        }
        payloads = [
            {"url": video_url},
            {"q": video_url},
            {"query": video_url},
            {"url": video_url, "lang": "en"},
            {"q": video_url, "lang": "en"},
        ]

        last_error = None
        for payload in payloads:
            try:
                response = requests.post(endpoint, headers=headers, data=payload, timeout=60)
                response.raise_for_status()
                data = response.json()
                if data.get("status") != "ok":
                    last_error = data.get("msg") or data.get("message") or "SnapTik tra ve trang thai khong hop le."
                    continue

                download_link = self.parse_snaptik_hd_link(data.get("data", ""))
                if download_link:
                    return download_link
                last_error = "Khong tim thay link Download MP4 HD trong response SnapTik."
            except Exception as exc:
                last_error = str(exc)

        raise RuntimeError(last_error or "Khong lay duoc link tai tu SnapTik.")

    def download_by_snaptik(self, video_url):
        video_key = None
        try:
            self.append_log(f"Thu tai bang SnapTik: {video_url}")

            file_path = self.build_download_file_path(video_url)
            video_key = file_path
            self.create_video_progress(video_key, f"Tai (SnapTik): {os.path.basename(file_path)}")

            download_link = self.request_snaptik_download_link(video_url)
            self.download_stream_to_file(download_link, file_path, video_key)

            self.finish_video_progress(video_key, "Hoan tat")
            self.append_log(f"Da tai xong bang SnapTik: {os.path.basename(file_path)}")
            return True
        except Exception:
            if video_key:
                self.fail_video_progress(video_key, "Tai that bai")
            self.append_log(f"Loi SnapTik: {traceback.format_exc()}")
            return False

    def download_tiktok_by_ttdownloader(self, video_url):
        video_key = None
        try:
            self.append_log(f"Dang xu ly: {video_url}")

            file_path = self.build_download_file_path(video_url)
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
                return False

            self.download_stream_to_file(download_link, file_path, video_key)

            self.finish_video_progress(video_key, "Hoan tat")
            self.append_log(f"Da tai xong: {os.path.basename(file_path)}")
            return True
        except Exception:
            if video_key:
                self.fail_video_progress(video_key, "Tai that bai")
            self.append_log(f"Loi: {traceback.format_exc()}")
            return False

    def download_video_with_fallback(self, video_url):
        if self.download_tiktok_by_ttdownloader(video_url):
            return True

        self.append_log("Thu fallback sang SnapTik...")
        return self.download_by_snaptik(video_url)

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
                    self.download_video_with_fallback(url)
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
                        self.download_video_with_fallback(video_url)
                    self.append_log("Da tai xong tat ca video.")
            except Exception:
                self.append_log(f"Loi chinh: {traceback.format_exc()}")

        threading.Thread(target=task, daemon=True).start()
