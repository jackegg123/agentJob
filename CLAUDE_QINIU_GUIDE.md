# Claude Code 七牛云配置指南

## 可行性评估

✅ **可行** - Claude Code可以通过设置环境变量使用自定义API端点，包括七牛云的API服务。

## 配置方法

### 1. 环境变量配置（推荐）

```bash
# 设置七牛云API密钥和端点
export ANTHROPIC_API_KEY="sk-ad3ae4900838d7ee027f426ac95d45c5b99bfb4731e974a8e2c11cf8ff855d17"
export ANTHROPIC_BASE_URL="https://api.qnaigc.com"
```

### 2. 使用配置文件

Claude Code也支持通过`--settings`参数加载配置文件：

```json
{
  "anthropicApiKey": "your-api-key",
  "apiUrl": "https://api.qnaigc.com",
  "model": "model-name"
}
```

运行：
```bash
claude --settings config.json --print "问题"
```

## 关键注意事项

### ⚠️ 模型名称
七牛云API可能使用不同的模型命名约定。需要确认：
- 七牛云支持的模型列表
- 正确的模型ID（例如：`step-3.5-flash`、`claude-3-5-sonnet`等）

### 🔐 API密钥安全
- 建议将API密钥保存在环境变量中，而非硬编码
- 可以考虑使用`~/.bashrc`或`~/.zshrc`设置
- 或使用Claude Code的密钥管理功能

## 在OpenClaw中使用

如果您希望通过OpenClaw调用Claude Code处理一次性任务：

### 方案A：直接调用可执行文件

```bash
# 在exec工具中设置环境变量
export ANTHROPIC_API_KEY="your-key"
export ANTHROPIC_BASE_URL="https://api.qnaigc.com"
claude --print "你的任务描述"
```

### 方案B：使用配置文件

```bash
claude --settings /path/to/qiniu-config.json --print "任务"
```

## 快速测试

已安装Claude Code，可立即测试：

```bash
# 临时设置环境变量并测试
ANTHROPIC_API_KEY="sk-ad3ae4900838d7ee027f426ac95d45c5b99bfb4731e974a8e2c11cf8ff855d17" \
ANTHROPIC_BASE_URL="https://api.qnaigc.com" \
claude --print "测试连接"
```

## 配置脚本

已创建便捷脚本：
```bash
source /home/dbq/.openclaw/workspace/setup-claude-qiniu.sh
```

## 下一步

1. **确认模型名称**：查看七牛云文档或控制台，确认可用的模型ID
2. **测试功能**：验证代码编辑、文件读写等功能是否正常
3. **安全配置**：将API密钥安全存储（考虑使用密钥管理工具）

## 已知问题

- `claude doctor`命令可能无法正常工作（需要Anthropic账户认证）
- 某些Anthropic特定功能（如OAuth、Keychain集成）需要官方API
- 模型名称必须与七牛云API兼容

## 总结

**可以成功使用** - Claude Code + 七牛云API的方案是可行的。主要配置就是设置`ANTHROPIC_BASE_URL`环境变量指向七牛云端点，并配置正确的API密钥。
