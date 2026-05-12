# demo1 使用示例

## 示例 1：完整扫描（重复代码 + 无用代码）

智能体在用户指定的项目目录中执行：

```bash
# 1. 运行 jscpd 扫描重复代码
jscpd "src/main/java" --pattern "**/*.java" --min-tokens 50 --min-lines 5 \
  --reporters json --output .jscpd-report

# 2. 运行无用代码扫描
python3 scripts/scan_dead_code.py "src/main/java" --output .dead-code-results.json

# 3. 生成报告
python3 scripts/generate_report.py \
  --jscpd-report .jscpd-report/jscpd-report.json \
  --dead-code-report .dead-code-results.json \
  --scan-dir "src/main/java" \
  -o java-analysis-report.md

# 4. 清理
rm -rf .jscpd-report .dead-code-results.json
```

## 示例 2：仅扫描重复代码

```bash
jscpd "src/" --pattern "**/*.java" --min-tokens 50 --reporters json --output .jscpd-report

python3 scripts/generate_report.py \
  --jscpd-report .jscpd-report/jscpd-report.json \
  --scan-dir "src/" \
  -o duplicate-report.md

rm -rf .jscpd-report
```

## 示例 3：仅扫描无用代码

```bash
python3 scripts/scan_dead_code.py "src/" --output .dead-code-results.json

python3 scripts/generate_report.py \
  --dead-code-report .dead-code-results.json \
  --scan-dir "src/" \
  -o dead-code-report.md

rm -f .dead-code-results.json
```

## 生成的报告示例

```markdown
# Java 代码质量分析报告

**项目**: my-project
**扫描时间**: 2026-05-12 15:30 CST
**扫描范围**: src/main/java

## 📊 概览统计

| 指标 | 数值 |
|------|------|
| 重复代码块数量 | 3 个 |
| 重复代码总行数 | 89 行 |
| jscpd 扫描文件数 | 120 个 |
| jscpd 重复率 | 5.20% |
| 无用代码问题数 | 15 处 |
| javalang 分析文件数 | 120 个 |
| 问题总数 | 18 处 |

### 重复代码严重程度分布

| 严重程度 | 数量 | 说明 |
|----------|------|------|
| 🔴 高 | 1 | ≥20行 且跨文件 |
| 🟡 中 | 2 | ≥10行 |
| 🟢 低 | 0 | <10行 或同文件内 |

## 🔄 重复代码 Top 3

共检测到 3 处重复，以下是最严重的 3 处：

### 1. 🔴 `ServiceA.java` ↔ `ServiceB.java`

- **文件 A**: `com/example/service/ServiceA.java` (行 45-78)
- **文件 B**: `com/example/service/ServiceB.java` (行 52-85)
- **重复行数**: 34 行
- **严重程度**: 高 (严重)
- **重复片段**:
  ```java
  public boolean validateRequest(Request req) {
    if (req == null || req.getId() == null) {
      return false;
    }
    // ...
  }
  ```

## 🗑️ 无用代码

### 类型分布

| 类型 | 数量 |
|------|------|
| 未使用的 import | 8 |
| 未使用的 private 字段 | 4 |
| 未使用的 private 方法 | 3 |
| 未使用的局部变量 | 0 |

## 💡 重构建议

1. **优先处理 1 处高严重度重复代码**：跨文件且行数 ≥20，建议提取公共基类或工具类
2. **关注 2 处中等严重度重复**
3. **清理 15 处无用代码**：未使用的 import、字段、方法和变量可以安全删除，减少代码噪音
   - 其中 8 个未使用的 import 可直接使用 IDE 自动清理
4. 重构后务必运行单元测试，确保功能不受影响
5. 建议将本工具集成到 CI/CD 流程中，定期扫描代码质量
```
