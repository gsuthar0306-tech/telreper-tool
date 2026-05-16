@echo off
setlocal
cd /d "%~dp0"

echo Starting TelReper Control Center...
echo.

python -m streamlit run telreper_web.py --server.port 8501 --server.headless true

echo.
echo TelReper stopped. Press any key to close this window.
pause >nul
