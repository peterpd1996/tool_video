import os
import random
import re
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from .config import FFMPEG_BIN, FFPROBE_BIN, VIDEO_EXTENSIONS
from .helpers import append_textbox, run_command, sanitize_filename

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
    import cv2
except Exception:
    cv2 = None

TARGET_DURATION_SECONDS = 62.0
MAX_OUTPUT_DURATION_SECONDS = 80.0
MAX_SINGLE_SCENE_DURATION_SECONDS = 15.0
INITIAL_PRIORITY_SCENES = 4
HOOK_MIN_DURATION_SECONDS = 3.0
HOOK_MAX_DURATION_SECONDS = 5.5
INTRO_MIN_DURATION_SECONDS = 2.5
INTRO_MAX_DURATION_SECONDS = 7.0
INTRO_HARD_MAX_DURATION_SECONDS = 10.0
MAX_SCENES_PER_SOURCE = 3
MIN_SCENE_GAP_PER_SOURCE = 2
SPEED_UP_THRESHOLD_SECONDS = 5.0
SPEED_UP_FACTOR = 1.25
HIGH_SPEED_UP_THRESHOLD_SECONDS = 10.0
HIGH_SPEED_UP_FACTOR = 1.35
FINAL_VIDEO_SATURATION = 1.18
FINAL_VIDEO_CONTRAST = 1.04
FINAL_AUDIO_VOLUME = 1.2
RANDOM_FLIP_RATIO = 0.35


@dataclass
class SceneClip:
    file_path: str
    source_key: str
    source_label: str
    view_score: int
    scene_index: int
    duration: float


class MergeVideoTab:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self.source_dir = os.getcwd()
        self.output_dir = os.path.join(os.getcwd(), "merged_videos")
        self.text_detection_cache = {}
        self.enable_flip_var = ctk.BooleanVar(value=True)

        self._build_ui()
        self.append_log(f"Thu muc nguon mac dinh: {self.source_dir}")
        self.append_log(f"Thu muc dich mac dinh: {self.output_dir}")

    def _build_ui(self):
        title = ctk.CTkLabel(
            self.parent,
            text="Ghep video tu cac canh da split",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.pack(pady=(16, 10))

        note = ctk.CTkLabel(
            self.parent,
            text=(
                "Nhap thu muc export da split, chon thu muc dich va so video can tao. "
                "Tool se uu tien canh view cao o dau, khong lap lai canh, "
                "va moi video goc chi duoc lay toi da 3 canh khong lien nhau."
            ),
            wraplength=820,
            justify="left",
        )
        note.pack(padx=20, pady=(0, 10), anchor="w")

        source_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        source_frame.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(source_frame, text="Thu muc export", width=120, anchor="w").pack(side="left")
        self.source_entry = ctk.CTkEntry(source_frame, width=620)
        self.source_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.source_entry.insert(0, self.source_dir)
        ctk.CTkButton(source_frame, text="Chon nguon", command=self.choose_source_dir, width=120).pack(side="left")

        output_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        output_frame.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(output_frame, text="Thu muc dich", width=120, anchor="w").pack(side="left")
        self.output_entry = ctk.CTkEntry(output_frame, width=620)
        self.output_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.output_entry.insert(0, self.output_dir)
        ctk.CTkButton(output_frame, text="Chon dich", command=self.choose_output_dir, width=120).pack(side="left")

        count_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        count_frame.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(count_frame, text="So video", width=120, anchor="w").pack(side="left")
        self.count_entry = ctk.CTkEntry(count_frame, width=120)
        self.count_entry.pack(side="left")
        self.count_entry.insert(0, "5")

        flip_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        flip_frame.pack(fill="x", padx=20, pady=6)
        self.flip_checkbox = ctk.CTkCheckBox(
            flip_frame,
            text="Lat canh khong co text",
            variable=self.enable_flip_var,
            onvalue=True,
            offvalue=False,
        )
        self.flip_checkbox.pack(anchor="w")

        self.merge_button = ctk.CTkButton(self.parent, text="Ghep video", command=self.start_merge, width=220)
        self.merge_button.pack(pady=8)

        self.log_box = ctk.CTkTextbox(self.parent, height=360, width=860)
        self.log_box.pack(padx=20, pady=(10, 20), fill="both", expand=True)

    def append_log(self, text):
        append_textbox(self.app, self.log_box, text)

    def set_merge_button_state(self, text, state):
        def _update():
            self.merge_button.configure(text=text, state=state)

        self.app.after(0, _update)

    def set_entry_value(self, entry, value):
        entry.delete(0, "end")
        entry.insert(0, value)

    def choose_source_dir(self):
        selected = filedialog.askdirectory(initialdir=self.source_dir)
        if selected:
            self.source_dir = selected
            self.set_entry_value(self.source_entry, selected)
            self.append_log(f"Thu muc export: {selected}")

    def choose_output_dir(self):
        selected = filedialog.askdirectory(initialdir=self.output_dir)
        if selected:
            self.output_dir = selected
            self.set_entry_value(self.output_entry, selected)
            self.append_log(f"Thu muc dich: {selected}")

    def has_ffmpeg_tools(self):
        try:
            ffmpeg_ok = run_command([FFMPEG_BIN, "-version"]).returncode == 0
            ffprobe_ok = run_command([FFPROBE_BIN, "-version"]).returncode == 0
            return ffmpeg_ok and ffprobe_ok
        except FileNotFoundError:
            return False

    def list_videos(self, folder_path):
        return sorted(
            os.path.join(folder_path, name)
            for name in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, name)) and name.lower().endswith(VIDEO_EXTENSIONS)
        )

    def get_duration(self, file_path):
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
            raise RuntimeError(result.stderr.strip() or f"Khong doc duoc duration: {file_path}")
        return float(result.stdout.strip())

    def parse_view_score(self, view_text):
        match = re.fullmatch(r"(\d+(?:\.\d+)?)([KMB]?)", view_text.strip(), flags=re.IGNORECASE)
        if not match:
            return 0

        number = float(match.group(1))
        suffix = match.group(2).upper()
        multiplier = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(suffix, 1)
        return int(number * multiplier)

    def parse_scene_clip(self, file_path):
        stem = os.path.splitext(os.path.basename(file_path))[0]
        match = re.match(r"^(?P<views>[^_]+)_(?P<label>.+)_(?P<scene>\d+)$", stem)
        if not match:
            return None

        source_key = f"{match.group('views')}_{match.group('label')}"
        duration = self.get_duration(file_path)
        return SceneClip(
            file_path=file_path,
            source_key=source_key,
            source_label=match.group("label"),
            view_score=self.parse_view_score(match.group("views")),
            scene_index=int(match.group("scene")),
            duration=duration,
        )

    def build_source_groups(self, source_dir):
        groups = {}
        for file_path in self.list_videos(source_dir):
            clip = self.parse_scene_clip(file_path)
            if not clip:
                continue
            groups.setdefault(clip.source_key, []).append(clip)

        for clips in groups.values():
            clips.sort(key=lambda clip: clip.scene_index)

        return dict(sorted(groups.items(), key=lambda item: (-item[1][0].view_score, item[0].lower())))

    def can_take_clip(self, clip, selected_clips, selected_by_source):
        if clip.file_path in {item.file_path for item in selected_clips}:
            return False

        taken_from_source = selected_by_source.get(clip.source_key, [])
        if len(taken_from_source) >= MAX_SCENES_PER_SOURCE:
            return False

        for existing in taken_from_source:
            if abs(existing.scene_index - clip.scene_index) < MIN_SCENE_GAP_PER_SOURCE:
                return False

        if selected_clips and selected_clips[-1].source_key == clip.source_key:
            return False

        return True

    def get_effective_duration(self, clip):
        if clip.duration > HIGH_SPEED_UP_THRESHOLD_SECONDS:
            return clip.duration / HIGH_SPEED_UP_FACTOR
        if clip.duration > SPEED_UP_THRESHOLD_SECONDS:
            return clip.duration / SPEED_UP_FACTOR
        return clip.duration

    def get_speed_factor(self, clip):
        if clip.duration > HIGH_SPEED_UP_THRESHOLD_SECONDS:
            return HIGH_SPEED_UP_FACTOR
        if clip.duration > SPEED_UP_THRESHOLD_SECONDS:
            return SPEED_UP_FACTOR
        return 1.0

    def is_clip_duration_allowed(self, clip):
        return self.get_effective_duration(clip) <= MAX_SINGLE_SCENE_DURATION_SECONDS

    def pick_next_clip_from_group(self, clips, selected_clips, selected_by_source, global_used):
        for clip in clips:
            if clip.file_path in global_used:
                continue
            if not self.is_clip_duration_allowed(clip):
                continue
            if self.can_take_clip(clip, selected_clips, selected_by_source):
                return clip
        return None

    def can_fit_output_duration(self, clip, total_duration):
        clip_duration = self.get_effective_duration(clip)
        if total_duration < TARGET_DURATION_SECONDS:
            return total_duration + clip_duration <= MAX_OUTPUT_DURATION_SECONDS
        return False

    def frame_has_text_like_region(self, frame):
        if cv2 is None or frame is None:
            return False

        height, width = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        tophat = cv2.morphologyEx(
            gray,
            cv2.MORPH_TOPHAT,
            cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5)),
        )
        _, thresh = cv2.threshold(tophat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        merged = cv2.morphologyEx(
            thresh,
            cv2.MORPH_CLOSE,
            cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3)),
            iterations=2,
        )
        contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        text_boxes = 0
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            if area < width * height * 0.002:
                continue
            if w < width * 0.12:
                continue
            if h < 8 or h > height * 0.18:
                continue
            if w / max(h, 1) < 2.2:
                continue
            text_boxes += 1
            if text_boxes >= 2:
                return True

        return False

    def clip_has_text(self, clip):
        cached = self.text_detection_cache.get(clip.file_path)
        if cached is not None:
            return cached

        if cv2 is None:
            self.text_detection_cache[clip.file_path] = True
            return True

        capture = cv2.VideoCapture(clip.file_path)
        if not capture.isOpened():
            self.text_detection_cache[clip.file_path] = True
            return True

        try:
            frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            if frame_count <= 0:
                self.text_detection_cache[clip.file_path] = True
                return True

            sample_positions = sorted(
                {
                    min(frame_count - 1, max(0, int(frame_count * ratio)))
                    for ratio in (0.15, 0.35, 0.5, 0.7, 0.85)
                }
            )
            hits = 0
            for position in sample_positions:
                capture.set(cv2.CAP_PROP_POS_FRAMES, position)
                ok, frame = capture.read()
                if not ok:
                    continue
                if self.frame_has_text_like_region(frame):
                    hits += 1
                    if hits >= 2:
                        self.text_detection_cache[clip.file_path] = True
                        return True
        finally:
            capture.release()

        self.text_detection_cache[clip.file_path] = False
        return False

    def pick_flip_targets(self, clips):
        if not self.enable_flip_var.get():
            return set()
        if not clips or cv2 is None:
            return set()

        candidates = [clip for clip in clips if not self.clip_has_text(clip)]
        if not candidates:
            return set()

        flip_count = max(0, int(round(len(clips) * RANDOM_FLIP_RATIO)))
        flip_count = min(flip_count, len(candidates))
        if flip_count <= 0:
            return set()

        return {clip.file_path for clip in random.sample(candidates, flip_count)}

    def score_clip_for_intro(self, clip, position):
        effective_duration = self.get_effective_duration(clip)
        score = clip.view_score

        if position == 0:
            if HOOK_MIN_DURATION_SECONDS <= effective_duration <= HOOK_MAX_DURATION_SECONDS:
                score += 2_000_000_000
            elif INTRO_MIN_DURATION_SECONDS <= effective_duration <= INTRO_MAX_DURATION_SECONDS:
                score += 800_000_000
            else:
                score -= 1_000_000_000
        else:
            if INTRO_MIN_DURATION_SECONDS <= effective_duration <= INTRO_MAX_DURATION_SECONDS:
                score += 1_000_000_000
            elif effective_duration <= INTRO_HARD_MAX_DURATION_SECONDS:
                score += 200_000_000
            else:
                score -= 1_000_000_000

        return score

    def pick_intro_clip(self, source_groups, selected_clips, selected_by_source, global_used, total_duration):
        position = len(selected_clips)
        candidates = []
        for _, clips in source_groups:
            for clip in clips:
                if clip.file_path in global_used:
                    continue
                if not self.is_clip_duration_allowed(clip):
                    continue
                if not self.can_take_clip(clip, selected_clips, selected_by_source):
                    continue
                if not self.can_fit_output_duration(clip, total_duration):
                    continue
                if position < INITIAL_PRIORITY_SCENES and self.get_effective_duration(clip) > INTRO_HARD_MAX_DURATION_SECONDS:
                    continue
                candidates.append(clip)

        if not candidates:
            return None

        candidates.sort(
            key=lambda clip: (
                self.score_clip_for_intro(clip, position),
                clip.view_score,
            ),
            reverse=True,
        )
        return candidates[0]

    def select_clips_for_output(self, source_groups, global_used):
        selected_clips = []
        selected_by_source = {}
        total_duration = 0.0

        sorted_groups = list(source_groups.items())

        # 4 canh dau: hook-first, uu tien canh ngan manh va view cao.
        while len(selected_clips) < INITIAL_PRIORITY_SCENES:
            clip = self.pick_intro_clip(
                sorted_groups,
                selected_clips,
                selected_by_source,
                global_used,
                total_duration,
            )
            if not clip:
                break
            selected_clips.append(clip)
            selected_by_source.setdefault(clip.source_key, []).append(clip)
            total_duration += self.get_effective_duration(clip)

        if not selected_clips:
            return []

        while total_duration < TARGET_DURATION_SECONDS:
            candidates = []
            for _, clips in sorted_groups:
                clip = self.pick_next_clip_from_group(clips, selected_clips, selected_by_source, global_used)
                if not clip:
                    continue
                if not self.can_fit_output_duration(clip, total_duration):
                    continue
                candidates.append(clip)

            if not candidates:
                break

            candidates.sort(key=lambda clip: clip.view_score, reverse=True)
            top_pool_size = min(5, len(candidates))
            weighted_pool = candidates[:top_pool_size]
            weights = [max(1, clip.view_score) for clip in weighted_pool]
            picked_clip = random.choices(weighted_pool, weights=weights, k=1)[0]

            selected_clips.append(picked_clip)
            selected_by_source.setdefault(picked_clip.source_key, []).append(picked_clip)
            total_duration += self.get_effective_duration(picked_clip)

        if total_duration < TARGET_DURATION_SECONDS:
            return []

        return selected_clips

    def build_processed_clip(self, clip, temp_dir, index, flip_targets=None):
        speed_factor = self.get_speed_factor(clip)
        should_flip = bool(flip_targets and clip.file_path in flip_targets)
        if speed_factor <= 1.0 and not should_flip:
            return clip.file_path

        processed_path = os.path.join(temp_dir, f"clip_{index:03d}.mp4")
        video_filters = []
        if should_flip:
            video_filters.append("hflip")
        if speed_factor > 1.0:
            video_filters.append(f"setpts=PTS/{speed_factor}")

        result = run_command(
            [
                FFMPEG_BIN,
                "-y",
                "-hide_banner",
                "-i",
                clip.file_path,
                "-filter:v",
                ",".join(video_filters),
                "-filter:a",
                f"atempo={speed_factor}",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-ar",
                "44100",
                processed_path,
            ]
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"Khong the tang toc canh {index}.")
        return processed_path

    def merge_with_ffmpeg(self, clips, output_path, flip_targets=None):
        with tempfile.TemporaryDirectory(prefix="merge_clips_") as temp_dir:
            flip_targets = flip_targets or set()
            prepared_paths = [
                self.build_processed_clip(clip, temp_dir, index, flip_targets=flip_targets)
                for index, clip in enumerate(clips, start=1)
            ]

            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as concat_file:
                concat_path = concat_file.name
                for prepared_path in prepared_paths:
                    escaped_path = prepared_path.replace("'", "'\\''")
                    concat_file.write(f"file '{escaped_path}'\n")

            try:
                command = [
                    FFMPEG_BIN,
                    "-y",
                    "-hide_banner",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    concat_path,
                    "-vf",
                    f"eq=saturation={FINAL_VIDEO_SATURATION}:contrast={FINAL_VIDEO_CONTRAST}",
                    "-af",
                    f"volume={FINAL_AUDIO_VOLUME}",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "20",
                    "-c:a",
                    "aac",
                    "-ar",
                    "44100",
                    output_path,
                ]
                result = run_command(command)
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.strip() or "Khong the ghep video.")
            finally:
                if os.path.exists(concat_path):
                    os.remove(concat_path)

    def log_selected_clips(self, output_name, clips, flip_targets=None):
        self.append_log(f"Canh duoc chon cho {output_name}:")
        flip_targets = flip_targets or set()
        for index, clip in enumerate(clips, start=1):
            speed_factor = self.get_speed_factor(clip)
            speed_note = f" | speed {speed_factor:.2f}x" if speed_factor > 1.0 else ""
            flip_note = " | flip" if clip.file_path in flip_targets else ""
            self.append_log(
                f"  {index}. {clip.source_key}_{clip.scene_index} | {clip.duration:.1f}s{speed_note}{flip_note}"
            )

    def merge_videos(self):
        self.set_merge_button_state("Dang ghep video...", "disabled")
        self.source_dir = self.source_entry.get().strip() or self.source_dir
        self.output_dir = self.output_entry.get().strip() or self.output_dir

        try:
            if not self.source_dir or not os.path.isdir(self.source_dir):
                self.append_log("Thu muc export khong hop le.")
                return

            if not self.output_dir:
                self.append_log("Vui long chon thu muc dich.")
                return

            try:
                output_count = int(self.count_entry.get().strip() or "5")
            except ValueError:
                self.append_log("So video phai la so.")
                return

            if output_count <= 0:
                self.append_log("So video phai lon hon 0.")
                return

            if not self.has_ffmpeg_tools():
                self.append_log("Khong tim thay ffmpeg/ffprobe.")
                return

            os.makedirs(self.output_dir, exist_ok=True)
            source_groups = self.build_source_groups(self.source_dir)
            if not source_groups:
                self.append_log("Khong tim thay file canh hop le trong thu muc export.")
                return

            global_used = set()
            created_outputs = 0

            for output_index in range(1, output_count + 1):
                selected_clips = self.select_clips_for_output(source_groups, global_used)
                if not selected_clips:
                    self.append_log("Khong du canh de tao them video moi theo rule hien tai.")
                    break

                output_name = f"{output_index}.mp4"
                output_path = os.path.join(self.output_dir, output_name)

                try:
                    flip_targets = self.pick_flip_targets(selected_clips)
                    self.log_selected_clips(output_name, selected_clips, flip_targets=flip_targets)
                    self.merge_with_ffmpeg(selected_clips, output_path, flip_targets=flip_targets)
                    created_outputs += 1
                    for clip in selected_clips:
                        global_used.add(clip.file_path)

                    duration = sum(self.get_effective_duration(clip) for clip in selected_clips)
                    self.append_log(
                        f"Da tao {output_name}: {len(selected_clips)} canh, {duration:.1f}s | mau tuoi hon | audio +20%"
                    )
                except Exception as exc:
                    self.append_log(f"Loi khi ghep {output_name}: {exc}")
                    break

            self.append_log(f"Hoan tat. Da tao {created_outputs} video.")
        finally:
            self.set_merge_button_state("Ghep video", "normal")

    def start_merge(self):
        threading.Thread(target=self.merge_videos, daemon=True).start()
