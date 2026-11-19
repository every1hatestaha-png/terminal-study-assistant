@echo off
setlocal
title KHZR Terminal Installer
set "INSTALL_DIR=%LOCALAPPDATA%\Programs\KHZR"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
where py >nul 2>&1
if errorlevel 1 (
  where python >nul 2>&1
  if errorlevel 1 (
    echo Python 3 is required. Install it from https://www.python.org/downloads/windows/
    echo During installation, enable "Add python.exe to PATH".
    pause
    exit /b 1
  )
)
copy /Y "%~dp0client.py" "%INSTALL_DIR%\client.py" >nul
if errorlevel 1 (
  echo Could not copy client.py. Extract the full ZIP first.
  pause
  exit /b 1
)
(
  echo @echo off
  echo if exist "%%~dp0client.py" ^(
  echo   where py ^>nul 2^>^&1
  echo   if not errorlevel 1 ^( py -3 "%%~dp0client.py" %%* ^& exit /b ^)
  echo   python "%%~dp0client.py" %%*
  echo ^) else ^(
  echo   echo KHZR installation is incomplete. Run install_khzr.bat again.
  echo ^)
) > "%INSTALL_DIR%\khzr.cmd"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=[Environment]::GetEnvironmentVariable('Path','User'); $d='%INSTALL_DIR%'; if (($p -split ';') -notcontains $d) { [Environment]::SetEnvironmentVariable('Path', (($p.TrimEnd(';') + ';' + $d).Trim(';')), 'User') }"
set "PATH=%INSTALL_DIR%;%PATH%"
echo.
echo KHZR Terminal installed.
echo Opening one-time setup now. Your token stays in your Windows user profile.
echo.
call "%INSTALL_DIR%\khzr.cmd" --setup
if errorlevel 1 (
  echo Setup did not finish. You can retry later with: khzr --setup
  pause
  exit /b 1
)
echo.
echo DONE. Close this window, open CMD anywhere, and type: khzr
pause
