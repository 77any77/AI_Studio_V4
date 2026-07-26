@echo off
setlocal
chcp 65001 >nul
title AI Studio V4 - 安装更新中心 v0.6.1
cd /d "%~dp0"

echo ==========================================================
echo AI Studio V4 内置更新中心 v0.6.1 安装修复版
echo ==========================================================
echo.

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py"
if not defined PYTHON_CMD (
    where python >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo [错误] 没有检测到 Python。
    echo 请先安装 Python。
    echo.
    pause
    exit /b 1
)

%PYTHON_CMD% --version
%PYTHON_CMD% "%~dp0install_patch.py"
set "RESULT=%errorlevel%"

echo.
if not "%RESULT%"=="0" (
    echo 安装没有完成，请把“安装更新中心日志.txt”发给我。
) else (
    echo 安装已经完成。
)

echo.
pause
exit /b %RESULT%
