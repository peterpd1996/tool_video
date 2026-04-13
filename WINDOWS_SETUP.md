# Chay Va Dong Goi Tren Windows

## 1. Cai san truoc

- Cai Python 3.12 hoac 3.13
- Cai FFmpeg va them `ffmpeg.exe` / `ffprobe.exe` vao `PATH`

## 2. Chay app

Nhan dup:

- [run_windows.bat](/Users/admin/Documents/Coding/ToolDownloadTiktok/run_windows.bat)

File nay se:

- tao `venv`
- cai package trong `requirements.txt`
- cai Chromium cho Playwright
- chay `index.py`

## 3. Dong goi ra exe

Nhan dup:

- [build_windows.bat](/Users/admin/Documents/Coding/ToolDownloadTiktok/build_windows.bat)

Sau khi build xong, file app se nam o:

- `dist\TikTokTool\TikTokTool.exe`

## 4. Luu y

- Build `.exe` nen duoc thuc hien truc tiep tren may Windows.
- Vi app dung `Playwright`, `torch`, `TransNetV2`, nen ban build kieu one-folder se on dinh hon one-file.
- Neu app mo len nhung khong split/ghep duoc video, thu kiem tra lai `ffmpeg` da co trong `PATH` chua.
