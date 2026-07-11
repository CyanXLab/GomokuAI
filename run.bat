@echo off
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [安装] 首次运行，正在安装依赖...
    python -m pip install flask
)
python run.py %*
pause
