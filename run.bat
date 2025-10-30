@echo off
REM Options Anomaly Detector - Windows 一键运行脚本
REM 自动检查环境、安装依赖、运行分析

setlocal EnableDelayedExpansion

echo.
echo ========================================================================
echo   Options Anomaly Detector - 期权市场异常分析
echo ========================================================================
echo.

REM Step 1: 检查 Python
echo [Step 1] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [成功] Python 已安装
echo.

REM Step 2: 检查虚拟环境
echo [Step 2] 检查虚拟环境...
if not exist "venv\" (
    echo [提示] 虚拟环境不存在，正在创建...
    python -m venv venv
    echo [成功] 虚拟环境创建成功
) else (
    echo [成功] 虚拟环境已存在
)
echo.

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM Step 3: 安装依赖
echo [Step 3] 检查依赖包...
pip show requests >nul 2>&1
if errorlevel 1 (
    echo [提示] 依赖包未安装，正在安装...
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    echo [成功] 依赖包安装完成
) else (
    echo [成功] 依赖包已安装
)
echo.

REM Step 4: 检查配置文件
echo [Step 4] 检查配置文件...
if not exist ".env" (
    echo [错误] .env 文件不存在
    echo.
    echo 请执行以下操作:
    echo   1. 复制示例文件: copy .env.example .env
    echo   2. 编辑 .env 文件，填入你的 Polygon API Key
    echo   3. 重新运行此脚本
    pause
    exit /b 1
)

findstr /C:"YOUR_API_KEY_HERE" .env >nul
if not errorlevel 1 (
    echo [错误] Polygon API Key 未设置
    echo.
    echo 请编辑 .env 文件，将 YOUR_API_KEY_HERE 替换为真实的 API Key
    pause
    exit /b 1
)

echo [成功] 配置文件检查通过
echo.

REM Step 5: 创建目录
echo [Step 5] 检查目录结构...
if not exist "data" mkdir data
if not exist "output" mkdir output
echo [成功] 目录结构完整
echo.

REM Step 6: 运行分析
echo ========================================================================
echo   准备开始分析...
echo ========================================================================
echo.

echo [Step 6] 运行分析程序...
echo.

python main.py
if errorlevel 1 (
    echo.
    echo ========================================================================
    echo   [失败] 分析失败
    echo ========================================================================
    echo.
    echo 请检查上方的错误信息
    pause
    exit /b 1
)

REM 成功
echo.
echo ========================================================================
echo   [成功] 分析完成！
echo ========================================================================
echo.

if exist "output\anomaly_report.html" (
    echo 报告文件: output\anomaly_report.html
    echo.
    echo 正在打开报告...
    start output\anomaly_report.html
)

echo.
echo ========================================================================

pause
