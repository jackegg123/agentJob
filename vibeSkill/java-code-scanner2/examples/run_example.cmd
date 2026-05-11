@echo off
REM ====================================================================
REM Java Code Scanner v2 - Windows 调用示例 (cmd)
REM ====================================================================
REM 演示如何使用 main.py 扫描 Java 项目。
REM 用法: run_example.cmd [项目路径] [输出路径]
REM ====================================================================

echo ========================================
echo  Java Code Scanner v2 - 示例调用
echo ========================================

set PROJECT_PATH=%~1
if "%PROJECT_PATH%"=="" set PROJECT_PATH=C:\path\to\your\java-project

set OUTPUT_PATH=%~2

REM 检查项目目录是否存在
if not exist "%PROJECT_PATH%" (
    echo [ERR] 项目路径不存在: %PROJECT_PATH%
    echo.
    echo 请修改本脚本或将路径作为参数传入:
    echo   %~nx0 D:\my-java-project
    pause
    exit /b 1
)

REM 可选: 跳过某项扫描
REM set SKIP_JSCPD=1

echo [INFO] 项目: %PROJECT_PATH%
echo.

python scripts\main.py --project-path "%PROJECT_PATH%" %OUTPUT_PATH%

echo.
echo [DONE] 示例调用完成。
pause
