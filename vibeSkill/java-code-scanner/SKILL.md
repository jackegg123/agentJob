---
name: java-code-scanner
version: 1.0.0
description: Java 项目代码质量扫描工具，支持冗余重复代码扫描 (jscpd) 和无用代码扫描 (Qodana JVM Community)
author: OpenCode Skill
icon: https://cdn.jsdelivr.net/gh/simple-icons/simple-icons/icons/java.svg
tags:
  - java
  - code-quality
  - linting
  - duplication
  - static-analysis
input:
  project-path:
    type: string
    description: 待扫描的 Java 项目根目录绝对路径
    required: true
  output:
    type: string
    description: 扫描结果 Excel 文件输出路径（默认在项目目录下生成）
    required: false
---

# Java Code Scanner Skill

## 概述

本 Skill 提供两大核心代码质量扫描能力，专为 Java 项目设计：

1. **冗余重复代码扫描 (Duplicate Code Detection)**：基于 `jscpd` 工具，检测项目中的重复或高度相似的代码片段。
2. **无用代码扫描 (Dead Code Detection)**：基于 JetBrains `Qodana JVM Community` 分析工具，检测未使用的声明、死代码等。

扫描结果统一汇总为格式化的 Excel 文件，方便 CI/CD 集成与团队审查。

## 核心指令

### 输入参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `--project-path` | string | 是 | 待扫描的 Java 项目根目录 |
| `--output` | string | 否 | Excel 报告输出路径（默认于项目目录下生成 `java-code-report.xlsx`） |

### 执行流程

1. **环境就绪检查**：确保 `jscpd` 和 `qodana` CLI 已安装
2. **并行扫描阶段**：
   - 调用 `jscpd` 对全部 `*.java` 文件执行重复代码扫描，输出 JSON 报告
   - 调用 `qodana scan` 执行 JVM 社区版静态分析，输出 SARIF 格式报告
3. **结果解析与聚合**：解析两份报告，提取问题详情
4. **Excel 生成阶段**：将聚合数据写入 `.xlsx` 文件，包含两个 Sheet
5. **临时清理**：自动删除扫描产生的临时文件

### 依赖要求

- Python ≥ 3.9 + `pandas` + `openpyxl`
- Node.js ≥ 16 + `jscpd`（全局安装）
- JetBrains `qodana` CLI
- 网络连接（Qodana 首次使用需验证 license 或拉取必要组件）

## 输出说明

生成的 Excel 文件包含两个 Sheet：

### Sheet 1：「冗余重复代码」

| 列名 | 说明 |
|------|------|
| 项目相对路径 | 文件在项目中的相对路径 |
| 文件名 | 源文件名 |
| 起始行 | 冗余代码块起始行 |
| 结束行 | 冗余代码块结束行 |
| 问题类型 | 固定值为"冗余重复代码" |
| 详细说明 | 指向重复的另一处位置及行号 |

### Sheet 2：「无用代码」

| 列名 | 说明 |
|------|------|
| 项目相对路径 | 文件在项目中的相对路径 |
| 文件名 | 源文件名 |
| 起始行 | 问题代码起始行 |
| 结束行 | 问题代码结束行 |
| 问题类型 | Qodana 规则 ID（如 UnusedDeclaration） |
| 详细说明 | Qodana 提供的详细解释信息 |

## 注意事项

- Qodana 首次运行可能需联网验证或拉取组件
- 扫描结果仅反映代码静态结构问题，不涵盖运行时行为
- 如需跳过某一项扫描，可通过环境变量控制：`SKIP_JSCPD=1` 或 `SKIP_QODANA=1`
