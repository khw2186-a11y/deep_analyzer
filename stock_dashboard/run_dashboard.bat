@echo off
echo ==============================================
echo Stock Dashboard Execution Script
echo ==============================================
echo.
echo [1] Installing required packages...
python -m pip install -r requirements.txt

echo.
echo [2] Running Streamlit dashboard...
python -m streamlit run main_dashboard.py

pause
