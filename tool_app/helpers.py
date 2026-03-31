import os
import re
import subprocess


def sanitize_filename(name):
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "", name or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(". ")
    return cleaned or "video"


def ensure_unique_filepath(file_path):
    if not os.path.exists(file_path):
        return file_path

    base, ext = os.path.splitext(file_path)
    counter = 1
    while True:
        candidate = f"{base} ({counter}){ext}"
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def run_command(command):
    return subprocess.run(command, capture_output=True, text=True)


def append_textbox(app, textbox, text):
    def _update():
        textbox.insert("end", text + "\n")
        textbox.see("end")

    app.after(0, _update)

