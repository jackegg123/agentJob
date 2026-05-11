#!/usr/bin/env bash
# ====================================================================
# Java Code Scanner v2 - 环境依赖安装脚本 (Linux/macOS)
# ====================================================================
# 安装运行所需的全部依赖:
#   1. Python 依赖 (javalang, pandas, openpyxl)
#   2. jscpd (npm 全局安装)
# ====================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo " Java Code Scanner v2 - 环境安装"
echo "========================================"
echo ""

# 步骤 1: 检查 Python
echo "[1/3] 检查 Python..."
if command -v python3 &>/dev/null; then
    py_cmd="python3"
elif command -v python &>/dev/null; then
    py_cmd="python"
else
    echo "  [ERR] Python 未安装！请先安装 Python >= 3.9"
    exit 1
fi

py_ver=$($py_cmd --version 2>&1)
echo "  [OK] $py_ver"

# 步骤 2: 安装 Python 依赖
echo "[2/3] 安装 Python 依赖 (javalang, pandas, openpyxl)..."
if ! $py_cmd -m pip install -r "$PROJECT_DIR/requirements.txt" --quiet 2>/dev/null; then
    # 尝试 --user 安装
    if ! $py_cmd -m pip install --user -r "$PROJECT_DIR/requirements.txt" --quiet; then
        echo "  [ERR] Python 依赖安装失败"
        echo "  请手动运行: $py_cmd -m pip install -r requirements.txt"
        exit 1
    fi
fi
echo "  [OK] Python 依赖安装完成"

# 步骤 3: 安装 jscpd
echo "[3/3] 安装 jscpd..."
if command -v jscpd &>/dev/null; then
    echo "  [OK] jscpd 已安装"
elif command -v npm &>/dev/null; then
    npm install -g jscpd
    echo "  [OK] jscpd 安装完成"
else
    echo "  [WARN] npm 未找到，请手动安装 jscpd: npm install -g jscpd"
    echo "        需要先安装 Node.js: https://nodejs.org/"
fi

echo ""
echo "========================================"
echo " 环境安装完成！"
echo ""
echo "运行扫描:"
echo "  $py_cmd scripts/main.py --project-path /path/to/java/project"
echo "========================================"
