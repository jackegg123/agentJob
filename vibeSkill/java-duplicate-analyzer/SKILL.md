---
name: analyze-java-duplicates
description: 使用 jscpd 分析 Java 项目中的重复/冗余代码，并提供专家级的重构建议。当用户需要检测 Java 代码中的复制粘贴、分析代码重复率、或识别可重构的冗余代码时使用此技能。
version: 1.0.0
license: Apache-2.0
compatibility: 需要 Node.js 和 npm（用于运行 npx jscpd），需要 Python 3.10+（用于生成报告）
metadata:
  author: 个人开发者
  category: task-code-review
---

# Java 冗余代码分析与重构专家

## 概述

使用 jscpd 工具检测 Java 项目中的重复代码，分析冗余代码，并生成 Markdown 和 Excel 格式的分析报告。

## 快速开始

执行 jscpd 检测 Java 项目重复代码的最简命令：

```bash
npx jscpd "src/" --pattern "**/*.java" --min-tokens 100 --reporters json --output .jscpd-report
```

如果 `src/` 目录不存在，请自行找到包含 `.java` 文件的源码目录进行扫描。

## 执行步骤

### 1. 执行 jscpd 扫描

在当前项目根目录运行以下命令：

```bash
npx jscpd "src/" --pattern "**/*.java" --min-tokens 100 --reporters json --output .jscpd-report
```

**参数说明：**
- `src/` - 源码目录（如果不存在，替换为实际目录，如 `app/`、`main/`、`java/`）
- `--min-tokens 100` - 只有超过 100 个 token 的相同片段才会被视为重复
- `--reporters json` - 输出 JSON 格式报告
- `--output .jscpd-report` - 报告输出目录

### 2. 生成 Markdown 分析报告

使用脚本生成 Markdown 格式的分析报告：

```bash
python scripts/generate_report.py .jscpd-report/jscpd-report.json ./java-duplicate-report.md
```

此命令会生成 `java-duplicate-report.md` 文件，包含：
- 概览统计（重复块数量、总重复行数）
- Top 10 严重重复代码详情
- 重复代码类型分布分析
- 重构建议

### 3. 生成 Excel 详细报告

使用脚本生成 Excel 格式的详细报告（包含所有重复项）：

```bash
python scripts/generate_excel.py .jscpd-report/jscpd-report.json ./java-duplicate-report.xlsx
```

此命令会生成 `java-duplicate-report.xlsx` 文件，包含以下工作表：

| 工作表 | 内容 |
|--------|------|
| **概览统计** | 扫描时间、重复块数量、总重复行数 |
| **重复代码明细** | 所有重复项的完整列表（序号、文件路径、行号、重复行数、严重程度、重构建议） |
| **Top 10 严重重复** | 最严重的 10 个重复项 |

Excel 表格列说明：
- **序号**: 重复项编号（按严重程度排序）
- **第一个文件**: 第一个重复文件的全路径
- **第二个文件**: 第二个重复文件的全路径
- **第一个文件行号**: 第一个文件中的行号范围
- **第二个文件行号**: 第二个文件中的行号范围
- **重复行数**: 重复的代码行数
- **严重程度**: 🔴严重(≥100行) / 🟠较严重(50-99行) / 🟡一般(20-49行) / 🟢轻微(<20行)
- **重构建议**: 针对该重复项的重构建议

### 4. 输出报告文件路径

报告生成完成后，输出文件路径给用户：

```
✅ 分析完成！

📊 报告已生成：
- Markdown 报告: ./java-duplicate-report.md
- Excel 详细报告: ./java-duplicate-report.xlsx
```

### 5. 清理现场

分析完成后，删除临时生成的报告目录：

```bash
rm -rf .jscpd-report
```

**注意**：保留生成的报告文件，供用户后续查阅和整改。

## 输出格式示例

### Markdown 报告示例

```markdown
# Java 代码重复分析报告

## 概览

| 指标 | 数值 |
|------|------|
| 扫描时间 | 2026-04-30 14:47:23 |
| 重复块数量 | 835 个 |
| 总重复行数 | 14,936 行 |
| 扫描范围 | hss-domain/src 目录 |

## 详细分析

### Top 10 严重重复代码

| 序号 | 第一个文件 | 第二个文件 | 重复位置 | 重复行数 | 严重程度 | 重构建议 |
|------|------------|------------|----------|----------|----------|----------|
| 1 | AccessFieldMapping.java | AccessFieldMappingExportVO.java | 行 28-129 ↔ 行 23-124 | 102 行 | 🔴 严重 | 建议提取公共基类 |
| 2 | ImageOcrAndDimensionVO.java | ImageOcrAndImageInfoVO.java | 行 24-242 ↔ 行 22-215 | 219 行 | 🔴 严重 | 建议提取公共基类 |
...
```

### Excel 报告说明

Excel 报告包含三个工作表：

1. **概览统计** - 展示扫描基本信息
2. **重复代码明细** - 展示所有重复项，可用于整改跟踪
3. **Top 10 严重重复** - 展示最严重的 10 个重复项

## 脚本工具

### scripts/generate_report.py

生成 Markdown 格式的分析报告。

**参数：**
- 第1个参数：jscpd JSON 报告路径
- 第2个参数：输出的 Markdown 文件路径

**示例：**
```bash
python scripts/generate_report.py .jscpd-report/jscpd-report.json ./report.md
```

### scripts/generate_excel.py

生成 Excel 格式的详细报告。

**参数：**
- 第1个参数：jscpd JSON 报告路径
- 第2个参数：输出的 Excel 文件路径

**依赖：**
- openpyxl（脚本会自动安装）

**示例：**
```bash
python scripts/generate_excel.py .jscpd-report/jscpd-report.json ./report.xlsx
```

## 参考资源

### 参考文档
- **`references/best-practices.md`** — Java 重构最佳实践，包含 Extract Method、Util Class、Generics、Template Method、Strategy 等模式的详细示例和代码

### 使用示例
- **`examples/usage.md`** — 基本用法演示，包含典型场景的输入输出示例

## 注意事项

- jscpd 依赖 Node.js 环境，确保本地已安装 Node.js 和 npm
- 报告生成依赖 Python 3.10+，如无 openpyxl 会自动安装
- `--min-tokens 100` 是推荐值，可根据项目实际情况调整
- 扫描大型项目时可能需要较长时间，请耐心等待
- Excel 报告包含所有重复项，便于进行整改跟踪和进度管理