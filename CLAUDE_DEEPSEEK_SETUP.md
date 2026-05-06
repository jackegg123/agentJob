# Claude Code DeepSeek 配置指南

## 环境变量设置

在开发目录中设置以下环境变量：

```bash
export ANTHROPIC_API_KEY="sk-47a8cadc96fd491bb85053f6cf6db85a"
export ANTHROPIC_BASE_URL="https://api.deepseek.com"
```

或者使用 `.env.local` 文件（已配置，无需提交到Git）。

## 使用方法

### 交互模式
```bash
cd /path/to/project
claude
```

### 一次性任务
```bash
ANTHROPIC_API_KEY="sk-..." ANTHROPIC_BASE_URL="https://api.deepseek.com" claude --print "任务描述"
```

### 配置文件方式
```bash
claude --settings ./claude-settings.json --print "任务"
```

示例 `claude-settings.json`：
```json
{
  "anthropicApiKey": "sk-47a8cadc96fd491bb85053f6cf6db85a",
  "apiUrl": "https://api.deepseek.com",
  "model": "deepseek-chat"
}
```

## 可用模型

- `deepseek-chat` - 通用对话模型
- `deepseek-reasoner` - 推理增强模型

## 注意事项

1. ⚠️ API 密钥切勿提交到Git仓库
2. ✅ `.env.local` 和 `claude-settings-*.json` 已在 `.gitignore` 中
3. 📱 开发移动端游戏时，确保使用viewport meta标签和触摸友好的UI
4. 🔄 每次新项目前检查 `.gitignore` 是否包含敏感文件排除

## 测试连接

```bash
curl -X POST "https://api.deepseek.com/v1/chat/completions" \
  -H "Authorization: Bearer $ANTHROPIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"Hello"}],"max_tokens":10}'
```

## 故障排除

- 如果返回 `unauthorized`，检查API密钥是否正确
- 如果返回 `rate limit exceeded`，等待或检查配额
- 如果连接超时，检查网络和BASE_URL设置
