@echo off
cd /d "%~dp0"
.venv\Scripts\streamlit.exe run app.py --server.port 8501
