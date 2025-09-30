@echo off
echo 启动校园网账号管理系统...
echo.
echo 系统将在浏览器中打开，请稍候...
echo 如需停止系统，请按 Ctrl+C
echo.

streamlit run app.py --server.port 8501 --browser.gatherUsageStats false

pause