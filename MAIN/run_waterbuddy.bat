@echo off
cd /d "%~dp0"
start "Water Buddy" ".venv\Scripts\python.exe" -m streamlit run "waterbuddy.py"
timeout /t 3 /nobreak >nul
start "" "http://localhost:8501"


