<#
.SYNOPSIS
    Java Code Scanner v2 - Windows 调用示例 (PowerShell)
.DESCRIPTION
    演示如何使用 main.py 扫描 Java 项目。
    用法: .\run_example.ps1 [项目路径] [输出路径]
#>

param(
    [string]$ProjectPath = "C:\path\to\your\java-project",
    [string]$OutputPath = ""
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Java Code Scanner v2 - 示例调用" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not (Test-Path $ProjectPath)) {
    Write-Host "[ERR] 项目路径不存在: $ProjectPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "请修改本脚本或将路径作为参数传入:" -ForegroundColor Yellow
    Write-Host "  .\run_example.ps1 D:\my-java-project" -ForegroundColor Yellow
    exit 1
}

# 可选: 跳过某项扫描
# $env:SKIP_JSCPD = "1"

Write-Host "[INFO] 项目: $ProjectPath" -ForegroundColor Green
Write-Host ""

$cmd = "python scripts\main.py --project-path ""$ProjectPath"""
if ($OutputPath) {
    $cmd += " --output ""$OutputPath"""
}

Invoke-Expression $cmd

Write-Host ""
Write-Host "[DONE] 示例调用完成。" -ForegroundColor Green
