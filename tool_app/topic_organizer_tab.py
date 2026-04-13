import os
import re
import shutil
import threading
import unicodedata
from tkinter import filedialog

import customtkinter as ctk

from .config import VIDEO_EXTENSIONS
from .helpers import append_textbox, sanitize_filename

BREED_KEYWORDS = {
    "Border Collie": ["border collie", "border collies"],
    "Bulldog": ["bulldog", "bulldogs"],
    "Cane Corso": ["cane corso", "cane corsos"],
    "Chihuahua": ["chihuahua", "chihuahuas"],
    "Dachshund": ["dachshund", "dachshunds", "sausage dog", "sausage dogs"],
    "Doberman": ["doberman", "dobermans"],
    "French Bulldog": ["french bulldog", "french bulldogs", "frenchie", "frenchies"],
    "German Shepherd": ["german shepherd", "german shepherds"],
    "Golden Retriever": ["golden retriever", "golden retrievers", "goldenretriever", "goldenretrievers"],
    "Great Dane": ["great dane", "great danes"],
    "Greyhound": ["greyhound", "greyhounds"],
    "Husky": ["husky", "huskies"],
    "Malinois": ["malinois"],
    "Maltese": ["maltese"],
    "Pitbull": ["pitbull", "pitbulls"],
    "Pug": ["pug", "pugs"],
}

TOPIC_KEYWORDS = {
    "Reaction Sounds": ["reacting", "reaction", "fart", "farts", "whisper", "whispers", "sound", "sounds", "hearing", "sneez", "kissing", "reflection"],
    "Sleep Naps": ["sleep", "sleepy", "asleep", "napping", "naps", "waking", "yawning", "fight sleep"],
    "Eating Drinking": ["eating", "drink", "drinking", "meal", "hungry", "bite", "food", "medicine", "treat", "treats", "sparkling water"],
    "Bath Water": ["bath", "baths", "bath time", "water", "wet", "splash", "splish", "shower", "pool"],
    "Fails Slips": ["fail", "fails", "slip", "slipping", "tripping", "falling", "gravity", "ice", "objects", "bugs"],
    "Zoomies Running": ["zoomies", "racing", "running", "turbo", "off leash", "speed"],
    "Talking Barking": ["speak", "speaks", "english", "talk", "talking", "bark", "barking", "whisper"],
    "Stealing Guilty Jealous": ["stealing", "stole", "socks", "guilty", "jealous", "innocent", "caught"],
    "Smart Understanding": ["smart", "understanding", "understand", "copying", "imitating", "owners better"],
    "Attitude Drama": ["attitude", "dramatic", "main character", "judging", "bosses", "run the world", "adopted", "side eye", "sassy"],
    "Cute Wholesome": ["cute", "cuteness", "happiness", "peaceful", "love", "babies", "kisses", "goodest", "cuddle", "happiest"],
    "Funny Chaos": ["funny", "hilarious", "chaos", "goofy", "clown", "comedy", "silly", "compilation", "random", "roommates"],
    "Costume Dance Car": ["costume", "dance", "dancing", "beat drops", "car ride", "movie night", "weddings"],
    "Vet Walk Home": ["vet", "walk", "leash", "house", "roommates", "drive", "daily chaos"],
}


class TopicOrganizerTab:
    def __init__(self, app, parent):
        self.app = app
        self.parent = parent
        self.source_dir = os.getcwd()
        self.output_dir = os.path.join(os.getcwd(), "video_topics")

        self._build_ui()
        self.append_log(f"Thu muc nguon mac dinh: {self.source_dir}")
        self.append_log(f"Thu muc dich mac dinh: {self.output_dir}")

    def _build_ui(self):
        title = ctk.CTkLabel(
            self.parent,
            text="Phan loai video theo chu de",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.pack(pady=(16, 10))

        note = ctk.CTkLabel(
            self.parent,
            text="Chon thu muc nguon va thu muc dich. Tool se doc ten file video, xac dinh chu de, tao folder theo nhom va copy video vao dung folder.",
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
        ctk.CTkLabel(output_frame, text="Thu muc dich", width=120, anchor="w").pack(side="left")
        self.output_entry = ctk.CTkEntry(output_frame, width=620)
        self.output_entry.pack(side="left", padx=(0, 10), fill="x", expand=True)
        self.output_entry.insert(0, self.output_dir)
        ctk.CTkButton(output_frame, text="Chon dich", command=self.choose_output_dir, width=120).pack(side="left")

        ctk.CTkButton(self.parent, text="Phan loai video", command=self.start_organize, width=220).pack(pady=8)

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
            self.append_log(f"Thu muc nguon: {selected}")

    def choose_output_dir(self):
        selected = filedialog.askdirectory(initialdir=self.output_dir)
        if selected:
            self.output_dir = selected
            self.set_entry_value(self.output_entry, selected)
            self.append_log(f"Thu muc dich: {selected}")

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

    def normalize_text(self, text):
        lowered = text.lower()
        ascii_text = unicodedata.normalize("NFKD", lowered)
        ascii_text = "".join(ch for ch in ascii_text if not unicodedata.combining(ch))
        ascii_text = re.sub(r"[^a-z0-9\s]", " ", ascii_text)
        return re.sub(r"\s+", " ", ascii_text).strip()

    def find_best_label(self, normalized_title, mapping):
        best_label = None
        best_score = 0
        for label, keywords in mapping.items():
            score = 0
            for keyword in keywords:
                if keyword in normalized_title:
                    score += len(keyword.split())
            if score > best_score:
                best_label = label
                best_score = score
        return best_label

    def infer_topic_folder(self, title):
        normalized = self.normalize_text(title)
        breed = self.find_best_label(normalized, BREED_KEYWORDS)
        topic = self.find_best_label(normalized, TOPIC_KEYWORDS)

        if breed and topic:
            return f"{breed} - {topic}"
        if breed:
            return f"{breed} - General"
        if topic:
            return f"General - {topic}"
        return "General - Misc"

    def organize_videos(self):
        self.source_dir = self.source_entry.get().strip() or self.source_dir
        self.output_dir = self.output_entry.get().strip() or self.output_dir

        if not self.source_dir or not os.path.isdir(self.source_dir):
            self.append_log("Thu muc nguon khong hop le.")
            return

        if not self.output_dir:
            self.append_log("Vui long chon thu muc dich.")
            return

        video_files = self.list_videos(self.source_dir)
        if not video_files:
            self.append_log("Khong tim thay video nao trong thu muc nguon.")
            return

        os.makedirs(self.output_dir, exist_ok=True)
        grouped_count = {}

        for index, file_path in enumerate(video_files, start=1):
            title = self.clean_title_from_filename(file_path)
            topic_folder = sanitize_filename(self.infer_topic_folder(title))
            destination_folder = os.path.join(self.output_dir, topic_folder)
            os.makedirs(destination_folder, exist_ok=True)

            destination_file = os.path.join(destination_folder, os.path.basename(file_path))
            if os.path.abspath(file_path) != os.path.abspath(destination_file):
                shutil.copy2(file_path, destination_file)

            grouped_count[topic_folder] = grouped_count.get(topic_folder, 0) + 1
            self.append_log(f"[{index}/{len(video_files)}] {os.path.basename(file_path)} -> {topic_folder}")

        self.append_log(f"Hoan tat. Da phan loai {len(video_files)} video vao {len(grouped_count)} nhom.")
        for topic_folder, count in sorted(grouped_count.items(), key=lambda item: (-item[1], item[0]))[:10]:
            self.append_log(f"- {topic_folder}: {count} video")

    def start_organize(self):
        threading.Thread(target=self.organize_videos, daemon=True).start()
