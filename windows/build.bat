@echo off
rem Builds usbc.exe (runs "msikvm.py set usbc") into this folder.
cd /d "%~dp0"
if not exist .venv (
    python -m venv .venv || exit /b 1
    .venv\Scripts\python -m pip install -q hidapi pyinstaller || exit /b 1
)
.venv\Scripts\pyinstaller --onefile --windowed --name usbc --paths .. --distpath . --workpath build --specpath build usbc.py
