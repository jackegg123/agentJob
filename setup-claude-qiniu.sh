#!/bin/bash
# Claude Code 七牛云配置脚本

# 七牛云API配置
export ANTHROPIC_API_KEY="sk-ad3ae4900838d7ee027f426ac95d45c5b99bfb4731e974a8e2c11cf8ff855d17"
export ANTHROPIC_BASE_URL="https://api.qnaigc.com"

# 可选：设置默认模型（需要与七牛云支持的模型一致）
# export CLAUDE_MODEL="your-model-name"

echo "已配置 Claude Code 使用七牛云 API"
echo "API Endpoint: $ANTHROPIC_BASE_URL"
echo ""
echo "使用方法："
echo "  1. 直接运行: claude --print \"你的问题\""
echo "  2. 启动交互: claude"
echo "  3. 指定模型: claude --model \"模型名\" --print \"问题\""
echo ""
echo "注意：需要确认七牛云支持的模型名称，可能需要查看七牛云文档"
