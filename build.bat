@echo off
setlocal
cd /d "%~dp0"

set "BLACKJACK_EXE=%CD%\dist\Blackjack.exe"
powershell.exe -NoProfile -Command "$app = Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -eq $env:BLACKJACK_EXE }; if ($app) { Write-Output ('Blackjack is still running (PID ' + $app.ProcessId + '). Close the game window and run build.bat again.'); exit 1 }"
if errorlevel 1 (
    echo.
    echo The existing executable is in use and cannot be replaced.
    pause
    exit /b 1
)

py -m pip install -r requirements-build.txt
if errorlevel 1 (
    echo Failed to install the build dependency.
    pause
    exit /b 1
)

py -m PyInstaller --noconfirm --clean --onefile --windowed --name Blackjack main.py
if errorlevel 1 (
    echo The executable build failed.
    pause
    exit /b 1
)

echo.
echo Build complete: dist\Blackjack.exe
pause
