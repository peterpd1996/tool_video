@echo off
setlocal

cd /d "%~dp0"

if not exist venv (
    py -3 -m venv venv
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name TikTokTool ^
  --collect-all playwright ^
  --collect-all transnetv2_pytorch ^
  --collect-all torch ^
  --hidden-import customtkinter ^
  --hidden-import yt_dlp ^
  --hidden-import scenedetect ^
  index.py

echo.
echo Build xong. File exe nam o: dist\TikTokTool\TikTokTool.exe
echo Neu ban dung one-folder build cua PyInstaller, nho giu nguyen ca thu muc dist\TikTokTool

endlocal
