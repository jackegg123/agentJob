#!/usr/bin/env bash
# ====================================================================
# Java Code Scanner Skill - 环境依赖安装脚本
# ====================================================================
# 自动安装所有系统级和语言级依赖。
# 适用于 Ubuntu/Debian / macOS 环境。
# ====================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo " Java Code Scanner - 环境安装脚本"
echo "========================================"

# ------------------------------------------------------------------
# 1. Node.js 检查与安装（用于 jscpd）
# ------------------------------------------------------------------
echo "[1/4] 检查 Node.js..."
if command -v node &>/dev/null && node --version | grep -qE "v(1[6-9]|[2-9][0-9])"; then
    echo "  ✅ Node.js $(node --version) 已安装。"
else
    echo "  -> 未检测到 Node.js 或版本低于 16。"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "  -> 请运行: brew install node"
    else
        echo "  -> 请运行: curl -fsSL https://deb.nodesource.com/setup_18.x | sudo bash - && sudo apt-get install -y nodejs"
    fi
    exit 1
fi

# ------------------------------------------------------------------
# 2. jscpd 全局安装
# ------------------------------------------------------------------
echo "[2/4] 安装/检查 jscpd..."
if command -v jscpd &>/dev/null; then
    echo "  ✅ jscpd $(jscpd --version 2>/dev/null) 已安装。"
else
    npm install -g jscpd
    echo "  ✅ jscpd 安装完成。"
fi

# ------------------------------------------------------------------
# 3. Python 依赖安装
# ------------------------------------------------------------------
echo "[3/4] 安装 Python 依赖..."
cd "$PROJECT_DIR"
pip3 install --quiet -r requirements.txt 2>/dev/null || \
    python3 -m pip install --quiet -r requirements.txt 2>/dev/null || {
        echo "  ⚠️  pip 不可用，尝试 pip install --user..."
        pip install --user --quiet -r requirements.txt
    }
echo "  ✅ Python 依赖安装完成。"

# ------------------------------------------------------------------
# 4. Qodana CLI 安装
# ------------------------------------------------------------------
echo "[4/4] 安装/检查 Qodana CLI..."
if command -v qodana &>/dev/null; then
    echo "  ✅ Qodana $(qodana --version 2>&1 | head -1) 已安装。"
else
    echo "  -> 下载 Qodana CLI..."
    INSTALL_DIR="${HOME}/.local/bin"
    mkdir -p "$INSTALL_DIR"

    # 获取最新版本号
    LATEST_VERSION=$(curl -s https://api.github.com/repos/JetBrains/qodana-cli/releases/latest \
        | grep '"tag_name"' | sed 's/.*"v\(.*\)".*/\1/' 2>/dev/null || echo "2025.1.0")

    curl -L "https://github.com/JetBrains/qodana-cli/releases/download/v${LATEST_VERSION}/qodana_linux_x86_64.tar.gz" \
        -o /tmp/qodana.tar.gz
    tar xzf /tmp/qodana.tar.gz -C "$INSTALL_DIR"
    chmod +x "$INSTALL_DIR/qodana"
    rm /tmp/qodana.tar.gz

    echo "  ✅ Qodana CLI 已安装到 $INSTALL_DIR"
    echo "  ⚠️  请确保 $INSTALL_DIR 在 PATH 中: export PATH=\"\$PATH:$INSTALL_DIR\""
fi

echo ""
echo "========================================"
echo " 环境安装完毕！"
echo ""
echo "运行扫描示例："
echo "  bash $PROJECT_DIR/examples/run_example.sh"
echo "========================================"
