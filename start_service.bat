@echo off
chcp 65001 > nul
echo ========================================
echo   校园网账号管理系统 - 服务启动
echo   Campus Account Manager Service
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 检查 Python 环境...
python --version > nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo [2/3] 安装/更新依赖...
pip install -r requirements.txt --quiet

echo [3/3] 启动应用服务...
echo.
echo 应用将在后台运行，访问地址:
echo   http://localhost:38506
echo.
echo 按 Ctrl+C 停止服务
echo ========================================
echo.

streamlit run app.py --server.port=38506 --server.headless=true

pause