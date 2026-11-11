@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel% equ 0 (
  py -3 client.py --url https://terminal-study-assistant-khzr.vercel.app
) else (
  python client.py --url https://terminal-study-assistant-khzr.vercel.app
)
endlocal
