import os
import threading
from tkinter import filedialog

import customtkinter as ctk

from .config import VIDEO_EXTENSIONS
from .helpers import append_textbox, sanitize_filename


class AutoCreateVideoTab:
    def __init__(self, app, parent, downloader, searcher, splitter, merger):
        self.app = app
        self.parent = parent
        self.downloader = downloader
        self.searcher = searcher
        self.splitter = splitter
        self.merger = merger
        self.output_root = os.path.join(os.getcwd(), "auto_created_videos")

        self._build_ui()
        self.append_log(f"Thu muc xuat mac dinh: {self.output_root}")

    def _build_ui(self):
        title = ctk.CTkLabel(
            self.parent,
            text="Tao video tu chu de",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.pack(pady=(16, 10))

        note = ctk.CTkLabel(
            self.parent,
            text=(
                "Nhap chu de, tool se tu tim video TikTok, loc view/noi dung AI, tai ve, "
                "split canh bang AI TransNetV2, roi ghep thanh video theo rule hien co."
            ),
            wraplength=820,
            justify="left",
        )
        note.pack(padx=20, pady=(0, 10), anchor="w")

        keyword_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        keyword_frame.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(keyword_frame, text="Chu de", width=120, anchor="w").pack(side="left")
        self.keyword_entry = ctk.CTkEntry(
            keyword_frame,
            width=620,
            placeholder_text="Vi du: dog play with ball",
        )
        self.keyword_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)

        settings_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        settings_frame.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(settings_frame, text="Video nguon", width=120, anchor="w").pack(side="left")
        self.source_count_entry = ctk.CTkEntry(settings_frame, width=120)
        self.source_count_entry.pack(side="left")
        self.source_count_entry.insert(0, "10")

        ctk.CTkLabel(settings_frame, text="Video tao", width=100, anchor="w").pack(side="left", padx=(20, 0))
        self.output_count_entry = ctk.CTkEntry(settings_frame, width=120)
        self.output_count_entry.pack(side="left")
        self.output_count_entry.insert(0, "5")

        view_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        view_frame.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(view_frame, text="Min view", width=120, anchor="w").pack(side="left")
        self.min_view_entry = ctk.CTkEntry(view_frame, width=120)
        self.min_view_entry.pack(side="left")
        self.min_view_entry.insert(0, "200000")

        output_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        output_frame.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(output_frame, text="Thu muc xuat", width=120, anchor="w").pack(side="left")
        self.output_entry = ctk.CTkEntry(output_frame, width=620)
        self.output_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.output_entry.insert(0, self.output_root)
        ctk.CTkButton(output_frame, text="Chon dich", command=self.choose_output_root, width=120).pack(side="left")

        self.create_button = ctk.CTkButton(self.parent, text="Tao video", command=self.start_create, width=220)
        self.create_button.pack(pady=8)

        self.log_box = ctk.CTkTextbox(self.parent, height=330, width=860)
        self.log_box.pack(padx=20, pady=(10, 20), fill="both", expand=True)

    def append_log(self, text):
        append_textbox(self.app, self.log_box, text)

    def set_button_state(self, text, state):
        def _update():
            self.create_button.configure(text=text, state=state)

        self.app.after(0, _update)

    def set_entry_value(self, entry, value):
        entry.delete(0, "end")
        entry.insert(0, value)

    def choose_output_root(self):
        selected = filedialog.askdirectory(initialdir=self.output_root)
        if selected:
            self.output_root = selected
            self.set_entry_value(self.output_entry, selected)
            self.append_log(f"Thu muc xuat: {selected}")

    def parse_positive_int(self, entry, default_value, label):
        try:
            value = int(entry.get().strip() or str(default_value))
        except ValueError:
            raise ValueError(f"{label} phai la so.")
        if value <= 0:
            raise ValueError(f"{label} phai lon hon 0.")
        return value

    def list_videos(self, folder_path):
        return sorted(
            os.path.join(folder_path, name)
            for name in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, name)) and name.lower().endswith(VIDEO_EXTENSIONS)
        )

    def download_selected_videos(self, video_items, download_dir):
        previous_dir = self.downloader.download_dir
        self.downloader.download_dir = download_dir
        self.downloader.set_entry_value(self.downloader.download_dir_entry, download_dir)
        downloaded_files = []

        try:
            for index, (video_url, view_count) in enumerate(video_items, start=1):
                before_files = set(self.list_videos(download_dir))
                self.append_log(
                    f"[Tai {index}/{len(video_items)}] {self.downloader.format_view_count(view_count)} | {video_url}"
                )
                if not self.downloader.download_video_with_fallback(video_url):
                    self.append_log("Tai that bai, bo qua video nay.")
                    continue
                after_files = set(self.list_videos(download_dir))
                new_files = sorted(after_files - before_files)
                if new_files:
                    downloaded_files.extend(new_files)
        finally:
            self.downloader.download_dir = previous_dir
            self.downloader.set_entry_value(self.downloader.download_dir_entry, previous_dir)

        return downloaded_files

    def filter_candidate_urls(self, video_urls, min_view_count, target_count):
        selected_items = []
        for index, video_url in enumerate(video_urls, start=1):
            try:
                info = self.downloader.get_video_info(video_url)
                view_count = int(info.get("view_count") or 0)
                if self.searcher.is_ai_content(info):
                    self.append_log(f"[Loc {index}] Bo qua noi dung AI | {video_url}")
                    continue
                if view_count < min_view_count:
                    self.append_log(
                        f"[Loc {index}] Bo qua view thap: {self.downloader.format_view_count(view_count)} | {video_url}"
                    )
                    continue

                selected_items.append((video_url, view_count))
                self.append_log(
                    f"[Loc {index}] Dat: {self.downloader.format_view_count(view_count)} | {video_url}"
                )
                if len(selected_items) >= target_count:
                    break
            except Exception as exc:
                self.append_log(f"[Loc {index}] Khong doc duoc metadata, bo qua: {video_url} | {exc}")
        return selected_items

    def split_downloaded_videos(self, video_files, split_dir):
        created_segments = []
        for index, file_path in enumerate(video_files, start=1):
            self.append_log(f"[Split {index}/{len(video_files)}] {os.path.basename(file_path)}")
            try:
                created = self.splitter.split_video_by_scenes(file_path, split_dir)
                created_segments.extend(created)
                self.append_log(f"Da split: {len(created)} canh")
            except Exception as exc:
                self.append_log(f"Loi split {os.path.basename(file_path)}: {exc}")
        return created_segments

    def merge_segments(self, split_dir, merge_dir, output_count):
        source_groups = self.merger.build_source_groups(split_dir)
        if not source_groups:
            self.append_log("Khong co canh hop le de ghep.")
            return 0

        global_used = set()
        created_outputs = 0
        for output_index in range(1, output_count + 1):
            selected_clips = self.merger.select_clips_for_output(source_groups, global_used)
            if not selected_clips:
                self.append_log("Khong du canh de tao them video moi theo rule hien tai.")
                break

            output_name = f"{output_index}.mp4"
            output_path = os.path.join(merge_dir, output_name)
            self.append_log(f"[Merge {output_index}/{output_count}] {output_name}")
            self.merger.log_selected_clips(output_name, selected_clips)
            self.merger.merge_with_ffmpeg(selected_clips, output_path)
            created_outputs += 1
            for clip in selected_clips:
                global_used.add(clip.file_path)
            self.append_log(f"Da tao: {output_name}")

        return created_outputs

    def create_videos(self):
        self.set_button_state("Dang tao video...", "disabled")
        keyword = self.keyword_entry.get().strip()
        self.output_root = self.output_entry.get().strip() or self.output_root

        try:
            if not keyword:
                self.append_log("Vui long nhap chu de.")
                return

            source_count = self.parse_positive_int(self.source_count_entry, 10, "Video nguon")
            output_count = self.parse_positive_int(self.output_count_entry, 5, "Video tao")
            min_view_count = self.parse_positive_int(self.min_view_entry, 200000, "Min view")

            if not self.splitter.has_ffmpeg_tools() or not self.merger.has_ffmpeg_tools():
                self.append_log("Khong tim thay ffmpeg/ffprobe.")
                return

            safe_topic = sanitize_filename(keyword) or "chu_de"
            run_root = os.path.join(self.output_root, safe_topic)
            download_dir = os.path.join(run_root, "download")
            split_dir = os.path.join(run_root, "export")
            merge_dir = os.path.join(run_root, "merged")
            for folder in (download_dir, split_dir, merge_dir):
                os.makedirs(folder, exist_ok=True)

            self.append_log(f"Bat dau tao video cho chu de: {keyword}")
            self.append_log(f"Download: {download_dir}")
            self.append_log(f"Split: {split_dir}")
            self.append_log(f"Merged: {merge_dir}")

            html_text, final_url = self.searcher.fetch_search_page(keyword, source_count)
            self.append_log(f"Da mo search TikTok: {final_url}")
            candidate_urls = self.searcher.extract_video_links_from_html(html_text, max(source_count * 8, 40))
            if not candidate_urls:
                self.append_log("Khong tim thay link video nao.")
                return

            selected_items = self.filter_candidate_urls(
                candidate_urls,
                min_view_count,
                source_count,
            )
            if not selected_items:
                self.append_log("Khong co video nao dat dieu kien loc.")
                return
            if len(selected_items) < source_count:
                self.append_log(f"Chi loc duoc {len(selected_items)}/{source_count} video dat dieu kien.")

            downloaded_files = self.download_selected_videos(selected_items, download_dir)
            if not downloaded_files:
                self.append_log("Khong tai duoc video nao.")
                return
            self.append_log(f"Da tai {len(downloaded_files)} video.")

            segments = self.split_downloaded_videos(downloaded_files, split_dir)
            if not segments:
                self.append_log("Khong split duoc canh nao.")
                return
            self.append_log(f"Da split tong {len(segments)} canh.")

            created_outputs = self.merge_segments(split_dir, merge_dir, output_count)
            self.append_log(f"Hoan tat pipeline. Da tao {created_outputs} video.")
        except Exception as exc:
            self.append_log(f"Loi pipeline: {exc}")
        finally:
            self.set_button_state("Tao video", "normal")

    def start_create(self):
        threading.Thread(target=self.create_videos, daemon=True).start()
