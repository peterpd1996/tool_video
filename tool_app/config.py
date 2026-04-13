import customtkinter as ctk

APP_TITLE = "TikTok Downloader + Video Scene Splitter"
APP_GEOMETRY = "980x760"
VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm")
FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"
AUTO_MIN_SEGMENT_DURATION = 2.5
AUTO_END_TRIM_SECONDS = 0.25
SCDET_MIN_SCORE = 9.0
SCDET_SCORE_PERCENTILE = 0.92
SCDET_NEIGHBOR_WINDOW = 2
PYSCENE_THRESHOLD = 27.0
PYSCENE_MIN_SCENE_LEN_FRAMES = 15
PYSCENE_ADAPTIVE_THRESHOLD = 3.0
PYSCENE_ADAPTIVE_WINDOW_WIDTH = 2
PYSCENE_ADAPTIVE_MIN_CONTENT_VAL = 15.0
TRANSNETV2_THRESHOLD = 0.5


def configure_theme():
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")
