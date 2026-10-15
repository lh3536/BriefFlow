@echo off
cd /d "%~dp0"
.venv\Scripts\streamlit.exe run finance_app.py --server.port 8502
