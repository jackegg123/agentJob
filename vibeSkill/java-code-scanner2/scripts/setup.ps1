<#
.SYNOPSIS
    Java Code Scanner v2 - Windows 环境依赖安装脚本
.DESCRIPTION
    安装运行 Java Code Scanner v2 所需的全部依赖：
      1. Python 依赖 (javalang, pandas, openpyxl)
      2. jscpd (npm 全局安装)
.NOTES
    请以管理员身份运行 PowerShell 执行此脚本。
    如果 npm 不在 PATH 中，请先安装 Node.js: https://nodejs.org/
#>

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Java Code Scanner v2 - 环境安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 步骤 1: 检查 Python
Write-Host "[1/3] 检查 Python..." -ForegroundColor Yellow
try {
    $pyVer = python --version 2>&1
    Write-Host "  [OK] $pyVer" -ForegroundColor Green
} catch {
    Write-Host "  [ERR] Python 未安装！请从 https://www.python.org/downloads/ 下载安装。" -ForegroundColor Red
    Write-Host "        安装时请勾选 'Add Python to PATH'"
    exit 1
}

# 确保 pip 可用
try {
    pip --version 2>&1 | Out-Null
} catch {
    Write-Host "  [WARN] pip 不可用，尝试 python -m pip..." -ForegroundColor Yellow
    python -m pip --version 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERR] pip 不可用，请重新安装 Python (勾选 pip)" -ForegroundColor Red
        exit 1
    }
}

# 步骤 2: 安装 Python 依赖
Write-Host "[2/3] 安装 Python 依赖 (javalang, pandas, openpyxl)..." -ForegroundColor Yellow
$reqFile = Join-Path $PSScriptRoot "..\requirements.txt"
try {
    pip install --timeout 60 -r $reqFile
    if ($LASTEXITCODE -ne 0) { throw "pip 退出码: $LASTEXITCODE" }
    Write-Host "  [OK] Python 依赖安装完成" -ForegroundColor Green
} catch {
    Write-Host "  [ERR] Python 依赖安装失败: $_" -ForegroundColor Red
    Write-Host "  请手动运行: pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# 步骤 3: 安装 jscpd
Write-Host "[3/3] 安装 jscpd..." -ForegroundColor Yellow
try {
    $jscpdVer = jscpd --version 2>&1
    Write-Host "  [OK] jscpd 已安装 (版本: $jscpdVer)" -ForegroundColor Green
} catch {
    Write-Host "  -> npm install -g jscpd..." -ForegroundColor Yellow
    try {
        npm install -g jscpd
        Write-Host "  [OK] jscpd 安装完成" -ForegroundColor Green
    } catch {
        Write-Host "  [ERR] jscpd 安装失败: $_" -ForegroundColor Red
        Write-Host "  请手动运行: npm install -g jscpd" -ForegroundColor Yellow
        Write-Host "  (需要先安装 Node.js: https://nodejs.org/)" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 环境安装完成！" -ForegroundColor Green
Write-Host ""
Write-Host "运行扫描:" -ForegroundColor White
Write-Host "  python scripts\main.py --project-path D:\path\to\java\project" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
