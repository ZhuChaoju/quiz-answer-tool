@echo off
REM 一键推送（首次会弹出 GitHub 登录窗口，用你的账号授权一次即可）
set PATH=D:\git\cmd;%PATH%
cd /d %~dp0

echo ==== push main ====
git push origin main
if errorlevel 1 goto :fail

echo ==== push csharp ====
git push origin csharp
if errorlevel 1 goto :fail

echo.
echo [OK] 推送完成
git status -sb
pause
exit /b 0

:fail
echo.
echo [ERROR] 推送失败（网络或登录未完成），关掉重试一次
pause
exit /b 1
