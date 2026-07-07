@echo off
cd /d "%~dp0"
echo ===================================================
echo   Public Video Downloader  (YouTube works here)
echo ---------------------------------------------------
echo   Your PERMANENT public link:
echo   https://lapsable-anika-automatically.ngrok-free.dev
echo ---------------------------------------------------
echo   1) A window opens running the app - keep it open.
echo   2) Keep THIS window open too while using it.
echo   Open the link above on your phone / share it.
echo ===================================================
echo.
start "Downloader App - keep open" cmd /k python app.py
timeout /t 4 >nul
echo Starting public tunnel on your permanent domain...
echo.
ngrok http --url=https://lapsable-anika-automatically.ngrok-free.dev 5000
