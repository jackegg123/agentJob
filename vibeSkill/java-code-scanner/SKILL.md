---
name: java-code-scanner
version: 2.0.0
description: >
  Analyze Java projects for duplicate code (via jscpd) and dead code
  (unused imports/fields/methods/variables via javalang AST).
  Generates structured Chinese Markdown report + Excel report with
  severity levels and refactoring suggestions.
  扫描 Java 项目中的重复代码（jscpd）和无用代码（javalang AST），
  生成带严重程度和重构建议的中文 Markdown + Excel 报告。

tags:
  - java
  - code-quality
  - duplicate-code
  - dead-code
  - jscpd

input:
  project_path:
    type: string
    description: >
      Path to the Java project or source directory to scan.
      要扫描的 Java 项目或源码目录路径。
    required: true
  output:
    type: string
    description: >
      Path for the generated Markdown report (default: project_dir/java-analysis-report.md).
      Markdown 报告输出路径。
    required: false
  output_excel:
    type: string
    description: >
      Path for the generated Excel report (default: project_dir/java-analysis-report.xlsx).
      Excel 报告输出路径。
    required: false
  min_tokens:
    type: integer
    description: "Minimum duplicate token count for jscpd (default: 50)"
    required: false
    default: 50
  min_lines:
    type: integer
    description: "Minimum duplicate line count for jscpd (default: 5)"
    required: false
    default: 5
  auto_mode:
    type: boolean
    description: "Auto mode: skip module selection and scan ALL modules automatically"
    required: false
    default: false
  selected_modules:
    type: string
    description: "Comma-separated list of modules to scan (e.g. 'module-a,module-b'). If omitted, ALL modules are scanned."
    required: false
  skip_jscpd:
    type: boolean
    description: "Skip duplicate code scan"
    required: false
    default: false
  skip_dead_code:
    type: boolean
    description: "Skip dead code scan"
    required: false
    default: false
  skip_excel:
    type: boolean
    description: "Skip Excel report generation"
    required: false
    default: false

steps:
  - id: Init
    description: |
      Install required dependencies.

      **jscpd (Node.js):**
      ```bash
      npm install -g jscpd
      ```
      If Windows PATH issues, use `npx jscpd` instead.

      **Python dependencies:**
      ```bash
      pip install javalang openpyxl
      ```

  - id: FindModules
    description: |
      **🗂️ Step 1: 发现并选择扫描模块（由智能体完成）**

      ⚠️ **强制要求**: 智能体必须执行模块发现步骤，不能默认只扫描第一个模块。

      ### 1.1 查找项目中的 Java 模块

      先找到包含 Java 源码的子目录（模块），列出所有可选的扫描目标：

      ```bash
      find "{{project_path}}" -name "*.java" -not -path "*/test/*" -not -path "*/target/*" -not -path "*/.git/*" | head -50
      ```

      分析搜索结果，将所有包含 `.java` 文件的**不同父目录**（即模块/子项目）列出：

      模块识别规则：
      - 如果 `{{project_path}}/src/main/java` 存在且含 Java 文件 → 包含此路径
      - 如果 `{{project_path}}` 下有多个子目录各自包含 Java 文件 → 每个子目录视为一个模块
      - 如果 `{{project_path}}` 本身直接包含 Java 文件 → 将整个目录视为一个模块
      - 也可以按 `pom.xml` / `build.gradle` 的子项目目录划分

      ### 1.2 展示模块列表并询问用户

      **智能体必须将找到的模块列表展示给用户**，格式如下：

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

      **选择规则**：
      - 用户输入单个数字 "1" → 扫描模块 1
      - 用户输入 "0" 或 "all" → 扫描全部模块
      - 用户输入 "1,3" → 扫描模块 1 和 3
      - 用户输入 "1-3" → 扫描模块 1,2,3
      - **如果 `auto_mode` 为 true 或用户直接说"全部"/"所有"→ 默认选择全部模块（选项 0）**
      - 如果只有一个模块 → 直接确认扫描该模块（无需列出选择）

      ### 1.3 确定最终扫描目录

      根据用户选择，将各模块路径拼接为扫描目标列表。如果是全部模块，用空格分隔多个路径传给后续步骤。

      记录最终选择的模块列表到变量 `selected_modules_str`（用逗号连接模块路径）。

  - id: FindJavaDir
    description: |
      **🔍 Step 2: 确认扫描目录**

      对于每个选中的模块，确定具体的 Java 源码目录：

      1. 先直接检查路径下是否有 `.java` 文件：
         ```bash
         find "<selected_module_path>" -maxdepth 3 -name "*.java" -not -path "*/test/*" | head -5
         ```
      2. 如果有 → 直接使用该路径
      3. 如果没有 → 递归查找 Java 文件最多的目录，传给 `--project-path`

      将所有选中的模块路径用空格分隔，存储在 `scan_paths` 变量中。

  - id: RunJscpd
    description: |
      **🔄 Step 3: 运行 jscpd 扫描重复代码**

      如果跳过了 jscpd 扫描（`--skip-jscpd`），跳到 Step 4。

      **对每个模块分别扫描：**

      对 `scan_paths` 中的每个路径执行 jscpd：
      ```bash
      jscpd "<module_path>" --pattern "**/*.java" --min-tokens {{min_tokens}} --min-lines {{min_lines}} --reporters json --output .jscpd-report-<idx>
      ```

      如果 jscpd 不在 PATH 中，使用 npx：
      ```bash
      npx jscpd "<module_path>" --pattern "**/*.java" --min-tokens {{min_tokens}} --min-lines {{min_lines}} --reporters json --output .jscpd-report-<idx>
      ```

      jscpd 会在 `.jscpd-report-<idx>/jscpd-report.json` 生成 JSON 报告。

      **如果多个模块 → 合并 jscpd 结果：**
      - 如果只有一个模块，直接使用该 JSON 报告
      - 如果多个模块，用 Python 合并所有 JSON 报告（合并 duplicates 数组，累加 statistics）
      - 合并后的报告保存为 `.jscpd-report/jscpd-report.json`

      **Windows (cmd):**
      ```cmd
      npx jscpd "C:\project\src" --pattern "**/*.java" --min-tokens 50 --min-lines 5 --reporters json --output .jscpd-report
      ```

  - id: RunDeadCode
    description: |
      **🗑️ Step 4: 运行无用代码扫描**

      如果跳过了无用代码扫描（`--skip-dead-code`），跳到 Step 5。

      对 `scan_paths` 中的每个路径分别扫描：

      ```bash
      python3 scripts/scan_dead_code.py "<module_path>" --output .dead-code-results-<idx>.json
      ```

      合并策略：
      - 单模块：直接用该结果
      - 多模块：合并 results 数组（追加），累加 summary 中的 scanned_files
      - 最终合并结果保存为 `.dead-code-results.json`

  - id: GenerateMarkdown
    description: |
      **📊 Step 5: 生成 Markdown 报告**

      将 jscpd JSON 报告和无用代码结果合并生成 Markdown 报告：

      ```bash
      python3 scripts/generate_report.py \
        --jscpd-report .jscpd-report/jscpd-report.json \
        --dead-code-report .dead-code-results.json \
        --output "{{output}}"
      ```

      报告包含：
      - 📊 概览统计表
      - 🔴🟡🟢 重复代码严重程度分布
      - 🔄 重复代码 Top 20
      - 🗑️ 无用代码分类列表
      - 💡 重构建议

  - id: GenerateExcel
    description: |
      **📈 Step 6: 生成 Excel 详细报告**

      如果跳过了 Excel 生成（`--skip-excel`），跳到 Step 7。

      ```bash
      python3 scripts/generate_excel.py \
        --jscpd-report .jscpd-report/jscpd-report.json \
        --dead-code-report .dead-code-results.json \
        --scan-dir "{{project_path}}" \
        --output "{{output_excel}}"
      ```

      **Excel 报告包含 4 个 Sheet：**

      | Sheet | 内容 |
      |-------|------|
      | 概览 | 总体统计、严重程度分布、无用代码类型分布 |
      | 重复代码 | 每处重复代码的详细位置、行号、片段（按严重程度着色） |
      | 无用代码 | 每处无用代码的类型、位置、说明（按严重程度着色） |
      | 重构建议 | 按优先级排列的重构建议与说明 |

      **着色规则**：
      - 🔴 红色行 = 高严重度（需优先处理）
      - 🟡 黄色行 = 中等严重度
      - 🟢 绿色行 = 低严重度

  - id: Cleanup
    description: |
      **🧹 Step 7: 清理临时文件**

      ```bash
      rm -rf .jscpd-report .jscpd-report-* .dead-code-results.json .dead-code-results-*.json
      ```

  - id: ReportSummary
    description: |
      **📋 Step 8: 汇总输出（由智能体完成）**

      扫描完成后，智能体应友好地汇总结果：

      ```
      ✅ 扫描完成！

      📊 扫描报告：
      - Markdown 报告: {{output}}
      - Excel 报告: {{output_excel}}

      📈 问题统计：
      - 重复代码: X 处 (高: Y1, 中: Y2, 低: Y3)
      - 无用代码: Z 处
      - 总计: W 处问题

      💡 建议优先处理高严重度的重复代码（跨文件且≥20行）。
      Excel 报告可按颜色快速筛选严重问题，建议用 Excel 打开方便定位代码。
      ```
