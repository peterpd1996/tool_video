import os
import re
import shutil
import threading
import sys
import tempfile
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from .config import (
    AUTO_END_TRIM_SECONDS,
    AUTO_MIN_SEGMENT_DURATION,
    FFMPEG_BIN,
    FFPROBE_BIN,
    PYSCENE_ADAPTIVE_MIN_CONTENT_VAL,
    PYSCENE_ADAPTIVE_THRESHOLD,
    PYSCENE_ADAPTIVE_WINDOW_WIDTH,
    PYSCENE_MIN_SCENE_LEN_FRAMES,
    PYSCENE_THRESHOLD,
    SCDET_MIN_SCORE,
    SCDET_NEIGHBOR_WINDOW,
    SCDET_SCORE_PERCENTILE,
    TRANSNETV2_THRESHOLD,
    VIDEO_EXTENSIONS,
)
from .helpers import append_textbox, ensure_unique_filepath, run_command, sanitize_filename

VENV_SITE_PACKAGES = (
    Path(__file__).resolve().parents[1]
    / "venv"
    / "lib"
    / f"python{sys.version_info.major}.{sys.version_info.minor}"
    / "site-packages"
)
if VENV_SITE_PACKAGES.exists() and str(VENV_SITE_PACKAGES) not in sys.path:
    sys.path.append(str(VENV_SITE_PACKAGES))

try:
    from scenedetect import AdaptiveDetector, ContentDetector, detect, split_video_ffmpeg
except Exception:
    AdaptiveDetector = None
    ContentDetector = None
    detect = None
    split_video_ffmpeg = None

try:
    from transnetv2_pytorch import TransNetV2
except Exception:
    TransNetV2 = None


class SceneSplitTab:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self.source_dir = os.getcwd()
        self.output_dir = os.getcwd()
        self._transnet_model = None

        self._build_ui()
        self.append_log(f"Thu muc nguon mac dinh: {self.source_dir}")
        self.append_log(f"Thu muc xuat mac dinh: {self.output_dir}")

    def _build_ui(self):
        title = ctk.CTkLabel(
            self.parent,
            text="Split canh hang loat theo thu muc",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.pack(pady=(16, 10))

        note = ctk.CTkLabel(
            self.parent,
            text="Moi video se duoc tu dong nhan dien chuyen canh va cat thanh nhieu file nho, ten giu nguyen va them _1, _2, ... Hien uu tien AI TransNetV2 de split canh sat hon.",
            wraplength=820,
            justify="left",
        )
        note.pack(padx=20, pady=(0, 10), anchor="w")

        source_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        source_frame.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(source_frame, text="Thu muc nguon", width=120, anchor="w").pack(side="left")
        self.source_entry = ctk.CTkEntry(source_frame, width=620)
        self.source_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.source_entry.insert(0, self.source_dir)
        ctk.CTkButton(source_frame, text="Chon nguon", command=self.choose_source_dir, width=120).pack(side="left")

        output_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        output_frame.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(output_frame, text="Thu muc xuat", width=120, anchor="w").pack(side="left")
        self.output_entry = ctk.CTkEntry(output_frame, width=620)
        self.output_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.output_entry.insert(0, self.output_dir)
        ctk.CTkButton(output_frame, text="Chon dich", command=self.choose_output_dir, width=120).pack(side="left")

        auto_frame = ctk.CTkFrame(self.parent)
        auto_frame.pack(fill="x", padx=20, pady=12)
        ctk.CTkLabel(
            auto_frame,
            text="Tab nay chi dung AI TransNetV2 de bat shot boundary va split canh. Moi canh qua ngan se duoc gom lai, va moi clip xuat ra se cat 0.25 giay o cuoi.",
            wraplength=820,
            justify="left",
        ).pack(anchor="w", padx=12, pady=12)

        ctk.CTkButton(self.parent, text="Bat dau split", command=self.start_split_videos, width=220).pack(pady=6)

        self.log_box = ctk.CTkTextbox(self.parent, height=320, width=860)
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
            self.append_log(f"Thu muc video nguon: {selected}")

    def choose_output_dir(self):
        selected = filedialog.askdirectory(initialdir=self.output_dir)
        if selected:
            self.output_dir = selected
            self.set_entry_value(self.output_entry, selected)
            self.append_log(f"Thu muc xuat: {selected}")

    def has_ffmpeg_tools(self):
        try:
            ffmpeg_ok = run_command([FFMPEG_BIN, "-version"]).returncode == 0
            ffprobe_ok = run_command([FFPROBE_BIN, "-version"]).returncode == 0
            return ffmpeg_ok and ffprobe_ok
        except FileNotFoundError:
            return False

    def has_pyscenedetect(self):
        return detect is not None and ContentDetector is not None

    def has_pyscenedetect_splitter(self):
        return self.has_pyscenedetect() and split_video_ffmpeg is not None

    def has_transnetv2(self):
        return TransNetV2 is not None

    def get_transnet_model(self):
        if not self.has_transnetv2():
            raise RuntimeError("Khong tim thay TransNetV2.")
        if self._transnet_model is None:
            self._transnet_model = TransNetV2()
        return self._transnet_model

    def export_ranges(self, file_path, output_dir, ranges, error_message):
        ranges = self.merge_short_ranges(ranges, AUTO_MIN_SEGMENT_DURATION)
        stem, ext = os.path.splitext(os.path.basename(file_path))
        safe_stem = sanitize_filename(stem)
        created_files = []

        for index, (start, end) in enumerate(ranges, start=1):
            trimmed_end = max(start, end - AUTO_END_TRIM_SECONDS)
            if trimmed_end - start < 0.1:
                continue

            output_name = f"{safe_stem}_{index}{ext}"
            output_path = ensure_unique_filepath(os.path.join(output_dir, output_name))
            result = run_command(
                [
                    FFMPEG_BIN,
                    "-y",
                    "-hide_banner",
                    "-ss",
                    f"{start:.3f}",
                    "-to",
                    f"{trimmed_end:.3f}",
                    "-i",
                    file_path,
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a?",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "18",
                    "-c:a",
                    "aac",
                    output_path,
                ]
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or error_message.format(index=index))
            created_files.append(output_path)

        if not created_files:
            raise RuntimeError("Khong xuat duoc file canh nao.")

        return created_files

    def merge_short_ranges(self, ranges, min_segment_duration):
        normalized = []
        for start, end in ranges:
            start_value = float(start)
            end_value = float(end)
            if end_value - start_value > 0:
                normalized.append((start_value, end_value))

        if not normalized:
            return []

        merged = normalized[:]
        index = 0
        while index < len(merged):
            start, end = merged[index]
            if end - start >= min_segment_duration:
                index += 1
                continue

            if len(merged) == 1:
                break

            if index == 0:
                next_start, next_end = merged[index + 1]
                merged[index + 1] = (start, next_end)
                merged.pop(index)
                continue

            prev_start, prev_end = merged[index - 1]
            merged[index - 1] = (prev_start, end)
            merged.pop(index)
            index -= 1

        return merged

    def get_video_duration(self, file_path):
        result = run_command(
            [
                FFPROBE_BIN,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                file_path,
            ]
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Khong lay duoc thoi luong video.")
        return float(result.stdout.strip())

    def get_scene_score_samples(self, file_path):
        result = run_command(
            [
                FFMPEG_BIN,
                "-hide_banner",
                "-i",
                file_path,
                "-filter:v",
                "scdet=t=0,metadata=print:file=-",
                "-an",
                "-f",
                "null",
                "-",
            ]
        )
        if result.returncode not in (0, 255):
            raise RuntimeError(result.stderr.strip() or "Khong the phan tich chuyen canh.")

        samples = []
        current_time = None
        combined_output = "\n".join([result.stdout, result.stderr])

        for line in combined_output.splitlines():
            time_match = re.search(r"pts_time:([0-9]+(?:\.[0-9]+)?)", line)
            if time_match:
                current_time = float(time_match.group(1))
                continue

            score_match = re.search(r"lavfi\.scd\.score=([0-9]+(?:\.[0-9]+)?)", line)
            if not score_match or current_time is None:
                continue
            samples.append((current_time, float(score_match.group(1))))

        return samples

    def percentile(self, values, ratio):
        if not values:
            return 0.0
        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * ratio))))
        return ordered[index]

    def pick_scene_points_from_scores(self, samples, duration):
        if not samples:
            return []

        scores = [score for _, score in samples]
        average_score = sum(scores) / len(scores)
        peak_threshold = max(
            SCDET_MIN_SCORE,
            average_score * 2.2,
            self.percentile(scores, SCDET_SCORE_PERCENTILE),
        )

        candidates = []
        for index, (time_value, score) in enumerate(samples):
            if score < peak_threshold:
                continue

            left = max(0, index - SCDET_NEIGHBOR_WINDOW)
            right = min(len(samples), index + SCDET_NEIGHBOR_WINDOW + 1)
            local_scores = [samples[pos][1] for pos in range(left, right)]
            if score < max(local_scores):
                continue

            if time_value <= 0 or duration - time_value <= 0:
                continue

            candidates.append((time_value, score))

        merged_points = []
        for time_value, score in candidates:
            if not merged_points:
                merged_points.append([time_value, score])
                continue

            prev_time, prev_score = merged_points[-1]
            if time_value - prev_time < AUTO_MIN_SEGMENT_DURATION:
                if score > prev_score:
                    merged_points[-1] = [time_value, score]
                continue

            merged_points.append([time_value, score])

        return [time_value for time_value, _ in merged_points]

    def auto_detect_scene_changes(self, file_path, duration):
        samples = self.get_scene_score_samples(file_path)
        return self.pick_scene_points_from_scores(samples, duration)

    def build_segment_ranges(self, duration, scene_points, min_segment_duration):
        markers = [0.0]
        for point in scene_points:
            if duration - point <= 0:
                continue
            if point > markers[-1] + min_segment_duration:
                markers.append(point)

        if duration - markers[-1] >= min_segment_duration:
            markers.append(duration)
        elif len(markers) == 1:
            markers.append(duration)
        else:
            markers[-1] = duration

        ranges = []
        for index in range(len(markers) - 1):
            start = markers[index]
            end = markers[index + 1]
            if end - start > 0:
                ranges.append((start, end))

        if len(ranges) >= 2:
            last_start, last_end = ranges[-1]
            if last_end - last_start < min_segment_duration:
                prev_start, _ = ranges[-2]
                ranges[-2] = (prev_start, last_end)
                ranges.pop()

        return ranges

    def split_video_by_scenes(self, file_path, output_dir):
        if not self.has_transnetv2():
            raise RuntimeError("Khong tim thay AI TransNetV2 trong moi truong hien tai.")
        self.append_log("Dang dung AI TransNetV2...")
        return self.split_video_by_transnetv2(file_path, output_dir)

    def split_video_by_transnetv2(self, file_path, output_dir):
        model = self.get_transnet_model()
        scenes = model.detect_scenes(file_path, threshold=TRANSNETV2_THRESHOLD)
        if not scenes:
            raise RuntimeError("TransNetV2 khong tim thay canh nao.")

        ranges = []
        for scene in scenes:
            try:
                start_seconds = float(scene["start_time"])
                end_seconds = float(scene["end_time"])
            except (KeyError, TypeError, ValueError):
                continue
            if end_seconds - start_seconds > 0:
                ranges.append((start_seconds, end_seconds))

        if not ranges:
            raise RuntimeError("TransNetV2 tra ve canh nhung khong doc duoc timestamp.")

        self.append_log(f"TransNetV2 tim thay {len(ranges)} canh.")
        return self.export_ranges(
            file_path,
            output_dir,
            ranges,
            "Khong cat duoc canh {index} bang TransNetV2.",
        )

    def split_video_by_adaptive(self, file_path, output_dir):
        scene_list = detect(
            file_path,
            AdaptiveDetector(
                adaptive_threshold=PYSCENE_ADAPTIVE_THRESHOLD,
                min_scene_len=PYSCENE_MIN_SCENE_LEN_FRAMES,
                window_width=PYSCENE_ADAPTIVE_WINDOW_WIDTH,
                min_content_val=PYSCENE_ADAPTIVE_MIN_CONTENT_VAL,
            ),
            show_progress=False,
        )
        if not scene_list:
            raise RuntimeError("AdaptiveDetector khong tim thay canh nao.")

        ranges = [
            (float(start_time.get_seconds()), float(end_time.get_seconds()))
            for start_time, end_time in scene_list
        ]
        return self.export_ranges(
            file_path,
            output_dir,
            ranges,
            "Khong cat duoc canh {index} bang AdaptiveDetector.",
        )

    def split_video_by_adaptive_ffmpeg(self, file_path, output_dir):
        scene_list = detect(
            file_path,
            AdaptiveDetector(
                adaptive_threshold=PYSCENE_ADAPTIVE_THRESHOLD,
                min_scene_len=PYSCENE_MIN_SCENE_LEN_FRAMES,
                window_width=PYSCENE_ADAPTIVE_WINDOW_WIDTH,
                min_content_val=PYSCENE_ADAPTIVE_MIN_CONTENT_VAL,
            ),
            show_progress=False,
        )
        if not scene_list:
            raise RuntimeError("AdaptiveDetector khong tim thay canh nao.")

        stem, ext = os.path.splitext(os.path.basename(file_path))
        safe_stem = sanitize_filename(stem)
        created_files = []

        with tempfile.TemporaryDirectory(prefix="split_scene_", dir=output_dir) as temp_dir:
            split_result = split_video_ffmpeg(
                file_path,
                scene_list,
                output_dir=Path(temp_dir),
                output_file_template="$VIDEO_NAME-Scene-$SCENE_NUMBER.mp4",
                arg_override="-map 0:v:0 -map 0:a? -c:v libx264 -preset veryfast -crf 18 -c:a aac",
                show_progress=False,
                show_output=False,
            )
            if split_result != 0:
                raise RuntimeError("split_video_ffmpeg khong xuat duoc video.")

            temp_files = sorted(Path(temp_dir).glob("*-Scene-*.mp4"))
            if not temp_files:
                raise RuntimeError("Khong tim thay file tam do split_video_ffmpeg tao ra.")

            for index, temp_file in enumerate(temp_files, start=1):
                output_name = f"{safe_stem}_{index}{ext}"
                output_path = ensure_unique_filepath(os.path.join(output_dir, output_name))
                shutil.move(str(temp_file), output_path)
                created_files.append(output_path)

        if not created_files:
            raise RuntimeError("split_video_ffmpeg da cat nhung khong xuat duoc file nao.")

        return created_files

    def split_video_by_pyscenedetect(self, file_path, output_dir):
        scene_list = detect(
            file_path,
            ContentDetector(
                threshold=PYSCENE_THRESHOLD,
                min_scene_len=PYSCENE_MIN_SCENE_LEN_FRAMES,
            ),
            show_progress=False,
        )
        if not scene_list:
            raise RuntimeError("PySceneDetect khong tim thay canh nao.")
        ranges = [
            (float(start_time.get_seconds()), float(end_time.get_seconds()))
            for start_time, end_time in scene_list
        ]
        return self.export_ranges(
            file_path,
            output_dir,
            ranges,
            "Khong cat duoc canh {index} bang PySceneDetect.",
        )

    def list_videos_in_folder(self, folder_path):
        return sorted(
            os.path.join(folder_path, name)
            for name in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, name)) and name.lower().endswith(VIDEO_EXTENSIONS)
        )

    def start_split_videos(self):
        self.source_dir = self.source_entry.get().strip() or self.source_dir
        self.output_dir = self.output_entry.get().strip() or self.output_dir

        if not self.source_dir or not os.path.isdir(self.source_dir):
            self.append_log("Thu muc nguon khong hop le.")
            return

        if not self.output_dir:
            self.append_log("Vui long chon thu muc xuat.")
            return

        os.makedirs(self.output_dir, exist_ok=True)

        if not self.has_ffmpeg_tools():
            self.append_log("Khong tim thay ffmpeg/ffprobe. Hay cai ffmpeg truoc khi split.")
            return

        video_files = self.list_videos_in_folder(self.source_dir)
        if not video_files:
            self.append_log("Khong tim thay video nao trong thu muc nguon.")
            return

        def task():
            total_segments = 0
            self.append_log(f"Bat dau split {len(video_files)} video... Che do: AI (TransNetV2)")
            for index, file_path in enumerate(video_files, start=1):
                file_name = os.path.basename(file_path)
                self.append_log(f"[{index}/{len(video_files)}] Dang phan tich {file_name}")
                try:
                    created = self.split_video_by_scenes(file_path, self.output_dir)
                    total_segments += len(created)
                    self.append_log(f"Da cat {file_name}: {len(created)} file")
                except Exception as exc:
                    self.append_log(f"Loi {file_name}: {exc}")

            self.append_log(f"Hoan tat. Tong file xuat: {total_segments}")

        threading.Thread(target=task, daemon=True).start()
