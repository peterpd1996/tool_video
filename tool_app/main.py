import customtkinter as ctk

from .auto_video_tab import AutoCreateVideoTab
from .config import APP_GEOMETRY, APP_TITLE, configure_theme
from .merge_tab import MergeVideoTab
from .search_download_tab import SearchDownloadTab
from .split_tab import SceneSplitTab
from .tiktok_tab import TikTokDownloadTab


def run_app():
    configure_theme()

    app = ctk.CTk()
    app.title(APP_TITLE)
    app.geometry(APP_GEOMETRY)

    header = ctk.CTkLabel(app, text=APP_TITLE, font=ctk.CTkFont(size=24, weight="bold"))
    header.pack(pady=(20, 10))

    tabview = ctk.CTkTabview(app, width=920, height=660)
    tabview.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    download_tab = tabview.add("Tai TikTok")
    search_tab = tabview.add("Tim chu de")
    auto_tab = tabview.add("Tao video")
    split_tab = tabview.add("Split canh")
    merge_tab = tabview.add("Ghep video")

    downloader_tab = TikTokDownloadTab(app, download_tab)
    searcher_tab = SearchDownloadTab(app, search_tab, downloader_tab)
    splitter_tab = SceneSplitTab(app, split_tab)
    merger_tab = MergeVideoTab(app, merge_tab)
    AutoCreateVideoTab(app, auto_tab, downloader_tab, searcher_tab, splitter_tab, merger_tab)

    app.mainloop()
