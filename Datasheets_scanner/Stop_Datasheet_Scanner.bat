@echo off
setlocal

echo Stopping Datasheet Scanner server (python app.py)...
for /f "tokens=2" %%P in ('tasklist ^| findstr /i "python.exe"') do (
  rem best-effort stop; harmless if not the scanner process
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'Datasheets_scanner\\app.py|\\app.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

echo Done.
timeout /t 1 /nobreak >nul
exit /b 0
