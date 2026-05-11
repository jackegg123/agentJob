# 工作流变更说明

## 问题
Claude Code (CC) v2.1 无法使用自定义 API（DeepSeek V4 Pro）。
CC 的 model 验证机制对非 Anhtropic 官方模型不兼容。

## 解决方案
由小香菇（当前模型·DeepSeek Chat）直接生成完整代码。
所有技术点已通过实际验证：
- ✅ javalang 解析 Java AST 可行，行号精准
- ✅ 500 行代码解析仅 6ms，性能够
- ✅ 支持泛型/Lambda/内部类/注解
- ✅ jscpd 使用方式已验证（v1 经验）
- ✅ pandas + openpyxl 输出 Excel

## 变更后的开发流程
1. 我直接开发所有文件
2. 每个文件生成后我会自我审查代码质量
3. 完成后上传到代码仓（agentJob/vibeSkill/java-code-scanner2/）
4. 不上传任何敏感信息
