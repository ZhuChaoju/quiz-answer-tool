@echo off
REM One-click rebuild of quiz-answer-tool.exe (Windows)
REM Usage: edit code in src\, then double-click this script
setlocal

set ROOT=%~dp0
set PY=%ROOT%.venv\Scripts\python.exe

if not exist "%PY%" (
    echo [ERROR] venv not found. Run: python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    exit /b 1
)

echo [1/2] Check PyInstaller...
"%PY%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo       Installing PyInstaller...
    "%PY%" -m pip install pyinstaller
)

echo [2/2] Building onefile exe (includes RapidOCR models, ~100MB)...
"%PY%" -m PyInstaller --onefile --name quiz-answer-tool --windowed ^
    --paths "%ROOT%src" ^
    --collect-all rapidocr ^
    --collect-all rapidfuzz ^
    --hidden-import win32gui ^
    "%ROOT%pack_launcher.py" ^
    --distpath "%ROOT%dist" ^
    --workpath "%ROOT%build" --clean >nul

if errorlevel 1 (
    echo [ERROR] Build failed, check output above
    exit /b 1
)

echo.
echo [OK] Done: %ROOT%dist\quiz-answer-tool.exe
echo      Ship together with config.example.json.
echo      NOTE: exe is gitignored, never commit it.
pause
