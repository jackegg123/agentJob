# demo1 使用示例

## 交互流程 (v2.0 新特性)

### 1. 模块选择

智能体首先自动发现项目中的 Java 模块，列出所有可选模块供用户选择：

```
🔍 在项目中发现以下包含 Java 源码的模块：

┌────┬──────────────────────────────────┬──────────────────┐
│  # │ 模块路径                         │ Java 文件数       │
├────┼──────────────────────────────────┼──────────────────┤
│ 1  │ module-core/src/main/java        │ 45               │
│ 2  │ module-service/src/main/java     │ 32               │
│ 3  │ module-web/src/main/java         │ 28               │
│ 0  │ 全部模块 (扫描所有)               │ 105              │
└────┴──────────────────────────────────┴──────────────────┘

请选择要扫描的模块编号（输入数字，如 "1" / "0" / "1,2" / "all"）：
```

- 用户输入数字选择具体模块
- 输入 "0" 或 "all" 扫描全部
- 输入 "1,3" 扫描第 1 和第 3 个模块
- 如果启用自动模式（`auto_mode: true`），默认选择全部模块

## 示例 1：完整扫描（重复代码 + 无用代码 + Excel 报告）

智能体在用户指定的项目目录中执行：

```bash
# 1. 运行 jscpd 扫描重复代码
jscpd "src/main/java" --pattern "**/*.java" --min-tokens 50 --min-lines 5 \
  --reporters json --output .jscpd-report

# 2. 运行无用代码扫描
python3 scripts/scan_dead_code.py "src/main/java" --output .dead-code-results.json

# 3. 生成 Markdown 报告
python3 scripts/generate_report.py \
  --jscpd-report .jscpd-report/jscpd-report.json \
  --dead-code-report .dead-code-results.json \
  --scan-dir "src/main/java" \
  -o java-analysis-report.md

# 4. 生成 Excel 报告（v2.0 新增）
python3 scripts/generate_excel.py \
  --jscpd-report .jscpd-report/jscpd-report.json \
  --dead-code-report .dead-code-results.json \
  --scan-dir "src/main/java" \
  -o java-analysis-report.xlsx

# 5. 清理
rm -rf .jscpd-report .dead-code-results.json
```

## 示例 2：多模块分别扫描

```bash
# 对每个模块分别执行 jscpd
jscpd "module-a/src/main/java" --pattern "**/*.java" --min-tokens 50 \
  --reporters json --output .jscpd-report-0
jscpd "module-b/src/main/java" --pattern "**/*.java" --min-tokens 50 \
  --reporters json --output .jscpd-report-1

# 对每个模块分别执行无用代码扫描
python3 scripts/scan_dead_code.py "module-a/src/main/java" --output .dead-code-0.json
python3 scripts/scan_dead_code.py "module-b/src/main/java" --output .dead-code-1.json

# 合并结果（用 Python）
python3 -c "
import json
# 合并 jscpd
merged = {'duplicates': [], 'statistics': {'total': {}}}
for i in range(2):
    with open(f'.jscpd-report-{i}/jscpd-report.json') as f:
        data = json.load(f)
    merged['duplicates'].extend(data.get('duplicates', []))
import os; os.makedirs('.jscpd-report', exist_ok=True)
with open('.jscpd-report/jscpd-report.json', 'w') as f:
    json.dump(merged, f, indent=2, ensure_ascii=False)
print(f'Merged {len(merged[\"duplicates\"])} duplicates')

# 合并无用代码
merged_dead = {'results': [], 'summary': {'scanned_files': 0, 'skipped_files': 0, 'total_issues': 0}}
for i in range(2):
    with open(f'.dead-code-{i}.json') as f:
        data = json.load(f)
    merged_dead['results'].extend(data.get('results', []))
    merged_dead['summary']['scanned_files'] += data['summary']['scanned_files']
    merged_dead['summary']['total_issues'] += data['summary']['total_issues']
with open('.dead-code-results.json', 'w') as f:
    json.dump(merged_dead, f, indent=2, ensure_ascii=False)
print(f'Merged {len(merged_dead[\"results\"])} dead code issues')
"

# 生成报告
python3 scripts/generate_report.py \
  --jscpd-report .jscpd-report/jscpd-report.json \
  --dead-code-report .dead-code-results.json \
  --scan-dir "src/" \
  -o java-analysis-report.md

python3 scripts/generate_excel.py \
  --jscpd-report .jscpd-report/jscpd-report.json \
  --dead-code-report .dead-code-results.json \
  --scan-dir "src/" \
  -o java-analysis-report.xlsx

# 清理
rm -rf .jscpd-report .jscpd-report-* .dead-code-*.json .dead-code-results.json
```

## 示例 3：仅扫描重复代码（快速模式）

```bash
jscpd "src/" --pattern "**/*.java" --min-tokens 50 --reporters json --output .jscpd-report

python3 scripts/generate_report.py \
  --jscpd-report .jscpd-report/jscpd-report.json \
  --scan-dir "src/" \
  -o duplicate-report.md

python3 scripts/generate_excel.py \
  --jscpd-report .jscpd-report/jscpd-report.json \
  --scan-dir "src/" \
  -o duplicate-report.xlsx

rm -rf .jscpd-report
```

## 示例 4：仅扫描无用代码

```bash
python3 scripts/scan_dead_code.py "src/" --output .dead-code-results.json

python3 scripts/generate_report.py \
  --dead-code-report .dead-code-results.json \
  --scan-dir "src/" \
  -o dead-code-report.md

python3 scripts/generate_excel.py \
  --dead-code-report .dead-code-results.json \
  --scan-dir "src/" \
  -o dead-code-report.xlsx

rm -f .dead-code-results.json
```

## Excel 报告功能说明 (v2.0 新增)

生成的 Excel 文件包含 **4 个 Sheet**，用颜色标记严重程度：

| Sheet | 内容 | 着色 |
|-------|------|------|
| 概览 | 总体统计、严重程度分布、无用代码类型分布 | - |
| 重复代码 | 每处重复代码的详细位置、行号、代码片段 | 🔴高 🟡中 🟢低 |
| 无用代码 | 每处无用代码的类型、位置、说明 | 🔴高 🟡中 🟢低 |
| 重构建议 | 按优先级排列的重构建议 | 按优先级着色 |

### 为什么要 Excel 报告？

- 📊 **直观的表格视图**：比 Markdown 更适合浏览大量问题
- 🎨 **颜色标识**：红色=需要立即处理，黄色=关注，绿色=轻微
- 🔍 **筛选和排序**：Excel 自带筛选功能，可按文件、类型、严重程度筛选
- 📝 **团队共享**：Excel 格式更适合团队评审和分配任务
- 📈 **进度追踪**：可以添加「处理状态」列追踪修复进度

## 生成的 Markdown 报告示例

```markdown
# Java 代码质量分析报告

**项目**: my-project
**扫描时间**: 2026-05-13 10:00 CST
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
...
```

## 版本历史

### v2.0 (2026-05-13)
- ✅ 新增模块选择交互：智能体列出所有模块，用户选择扫描范围
- ✅ 自动模式：`auto_mode=true` 时默认扫描全部模块
- ✅ 新增 Excel 报告生成（`generate_excel.py`）：4 个 Sheet，颜色标记严重程度
- ✅ 新增 `--skip-excel` 参数控制 Excel 生成
- ✅ 支持多模块分别扫描并合并结果

### v1.0 (2026-05-12)
- 初始版本：jscpd + javalang 扫描，Markdown 报告
