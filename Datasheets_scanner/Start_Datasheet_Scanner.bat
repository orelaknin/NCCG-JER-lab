@echo off
setlocal

set "APP_DIR=%~dp0"
for %%I in ("%APP_DIR%..") do set "REPO_DIR=%%~fI"
set "PYTHON_EXE=%REPO_DIR%\.venv\Scripts\python.exe"
set "URL=http://127.0.0.1:5000"

if not exist "%PYTHON_EXE%" (
  echo Python virtual environment was not found:
  echo %PYTHON_EXE%
  echo.
  echo Please contact the tool owner to set up the environment.
  pause
  exit /b 1
)

echo Stopping old Datasheet Scanner process if running...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'Datasheets_scanner\\app.py|\\app.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1

pushd "%APP_DIR%"
start "Datasheet Scanner Server" /min "%PYTHON_EXE%" "app.py"
timeout /t 3 /nobreak >nul
start "" "%URL%"
popd

echo Datasheet Scanner opened in your browser.
echo You can close this window.
timeout /t 2 /nobreak >nul
exit /b 0
