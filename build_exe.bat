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

echo [1/3] Check PyInstaller...
"%PY%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo       Installing PyInstaller...
    "%PY%" -m pip install pyinstaller
)

echo [2/3] Building onefile exe (includes RapidOCR models, ~100MB)...
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

echo [3/3] Assemble release folder (exe + banks + config example)...
if not exist "%ROOT%dist\release" mkdir "%ROOT%dist\release"
copy /y "%ROOT%dist\quiz-answer-tool.exe" "%ROOT%dist\release\" >nul
if exist "%ROOT%dist\release\banks" rmdir /s /q "%ROOT%dist\release\banks"
xcopy /e /i /q "%ROOT%banks" "%ROOT%dist\release\banks" >nul
copy /y "%ROOT%config\config.example.json" "%ROOT%dist\release\config.json" >nul

echo.
echo [OK] Done:
echo      %ROOT%dist\quiz-answer-tool.exe
echo      %ROOT%dist\release\  (exe + banks + config, whole folder is distributable)
echo      NOTE: exe is gitignored, never commit it.
pause
