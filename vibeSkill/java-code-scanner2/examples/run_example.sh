#!/usr/bin/env bash
# ====================================================================
# Java Code Scanner v2 - 示例调用脚本 (Linux/macOS)
# ====================================================================
# 用法: bash run_example.sh [project-path] [output-path]
# ====================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo " Java Code Scanner v2 - 示例调用"
echo "========================================"

PROJECT_PATH="${1:-"/path/to/your/java-project"}"
OUTPUT_PATH="${2:-}"

if [ ! -d "$PROJECT_PATH" ]; then
    echo "[ERR] 项目路径不存在: $PROJECT_PATH"
    echo ""
    echo "请修改本脚本或将路径作为参数传入:"
    echo "  bash $0 /home/user/my-java-project"
    exit 1
fi

# 可选: 跳过某项扫描
# export SKIP_JSCPD=1

CMD="python3 \"$PROJECT_DIR/scripts/main.py\" --project-path \"$PROJECT_PATH\""
[ -n "$OUTPUT_PATH" ] && CMD="$CMD --output \"$OUTPUT_PATH\""

echo "[INFO] 项目: $PROJECT_PATH"
echo ""
eval "$CMD"

echo ""
echo "[DONE] 示例调用完成。"
