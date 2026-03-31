import customtkinter as ctk

from .config import APP_GEOMETRY, APP_TITLE, configure_theme
from .split_tab import SceneSplitTab
from .tiktok_tab import TikTokDownloadTab
from .title_export_tab import TitleExportTab


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
    split_tab = tabview.add("Split canh")
    export_tab = tabview.add("Export tieu de")

    TikTokDownloadTab(app, download_tab)
    SceneSplitTab(app, split_tab)
    TitleExportTab(app, export_tab)

    app.mainloop()
