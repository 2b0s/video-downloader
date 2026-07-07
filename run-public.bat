@echo off
cd /d "%~dp0"
echo ===================================================
echo   Public Video Downloader  (YouTube works here)
echo ---------------------------------------------------
echo   1) A window opens running the app - keep it open.
echo   2) ngrok shows your public https URL below.
echo      Open that URL on your phone / share it.
echo   3) Keep THIS window open while using it.
echo ===================================================
echo.
start "Downloader App - keep open" cmd /k python app.py
timeout /t 4 >nul
echo Starting public tunnel... your public URL appears below:
echo.
ngrok http 5000
