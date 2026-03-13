@echo off
call C:\Users\niinito\AppData\Local\anaconda3\Scripts\activate.bat views-dashboard
cd /d "%~dp0"
streamlit run app.py
pause
