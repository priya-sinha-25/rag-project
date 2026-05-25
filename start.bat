@echo off
echo Starting Mutual Fund FAQ Assistant...
echo The UI will be available at http://127.0.0.1:8000

call .\venv\Scripts\activate.bat
set PYTHONPATH=src
set PYTHONIOENCODING=utf-8

uvicorn mf_faq.ui.api:app --host 127.0.0.1 --port 8000
pause
