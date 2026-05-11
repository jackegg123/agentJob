#!/usr/bin/env bash
# ====================================================================
# Java Code Scanner Skill - 示例调用脚本
# ====================================================================
#
# 演示如何调用 main.py 对 Java 项目进行代码质量扫描。
#
# 用法:
#   bash examples/run_example.sh [project-path] [output-path]
#
# 或直接:
#   python3 scripts/main.py --project-path /path/to/java/project [--output /path/to/report.xlsx]
# ====================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo " Java Code Scanner - 示例调用"
echo "========================================"

# 参数：默认值可替换为实际项目路径
PROJECT_PATH="${1:-"/path/to/your/java-project"}"
OUTPUT_PATH="${2:-}"

# 可选：跳过某项扫描
# export SKIP_JSCPD=1
# export SKIP_QODANA=1

if [ ! -d "$PROJECT_PATH" ]; then
    echo "❌ 项目路径不存在: $PROJECT_PATH"
    echo ""
    echo "请修改本脚本或将路径作为参数传入:"
    echo "  bash $0 /home/user/my-java-project"
    exit 1
fi

CMD="python3 \"$PROJECT_DIR/scripts/main.py\" --project-path \"$PROJECT_PATH\""
[ -n "$OUTPUT_PATH" ] && CMD="$CMD --output \"$OUTPUT_PATH\""

echo "执行: $CMD"
echo ""
eval "$CMD"

echo ""
echo "✅ 示例调用完成。"
