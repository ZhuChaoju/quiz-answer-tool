@echo off
REM 一键启动：自动检测源码更新→按需重打包→启动最新版工具
setlocal
set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"
%PY% -X utf8 "%ROOT%tools\launch_latest.py"
pause
