---
name: java-code-scanner
version: 1.0.0
description: >
  Analyze Java projects for duplicate code (via jscpd) and dead code
  (unused imports/fields/methods/variables via javalang AST).
  Generates a structured Chinese Markdown report with severity levels
  and refactoring suggestions.
  扫描 Java 项目中的重复代码（jscpd）和无用代码（javalang AST），
  生成带严重程度和重构建议的中文 Markdown 报告。

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
      pip install javalang
      # javalang is the only Python dependency (standard library used for report generation)
      ```

  - id: FindJavaDir
    description: |
      **🔍 Step 1: 找到包含 Java 代码的目录（由智能体完成）**

      智能体需要找到正确的扫描目录后调用脚本。方法：

      1. 先检查用户提供的路径下是否直接有 `.java` 文件：
         ```bash
         find "{{project_path}}" -maxdepth 1 -name "*.java" | head -3
         ```
      2. 如果有 → 直接使用该路径
      3. 如果没有 → 递归查找：
         ```bash
         find "{{project_path}}" -name "*.java" -not -path "*/test/*" -not -path "*/target/*" | head -20
         ```
      4. 分析结果，选择合适的目录：
         - 优先 `src/main/java`
         - 否则选 Java 文件最多的父目录
         - 传给 `--project-path`

  - id: RunJscpd
    description: |
      **🔄 Step 2: 运行 jscpd 扫描重复代码**

      智能体直接执行 jscpd（不用 Python 脚本封装）：

      **Basic:**
      ```bash
      jscpd "{{scan_dir}}" --pattern "**/*.java" --min-tokens {{min_tokens}} --min-lines {{min_lines}} --reporters json --output .jscpd-report
      ```

      如果 jscpd 不在 PATH 中，使用 npx：
      ```bash
      npx jscpd "{{scan_dir}}" --pattern "**/*.java" --min-tokens {{min_tokens}} --min-lines {{min_lines}} --reporters json --output .jscpd-report
      ```

      jscpd 会在 `.jscpd-report/jscpd-report.json` 生成 JSON 报告。

      **Windows (cmd):**
      ```cmd
      npx jscpd "C:\project\src" --pattern "**/*.java" --min-tokens 50 --min-lines 5 --reporters json --output .jscpd-report
      ```

      如果跳过此步骤，设置 `--skip-jscpd`。

  - id: RunDeadCode
    description: |
      **🗑️ Step 3: 运行无用代码扫描**

      调用 Python 脚本扫描未使用的 import/字段/方法/局部变量：

      ```bash
      python3 scripts/scan_dead_code.py "{{scan_dir}}" --output .dead-code-results.json
      ```

      脚本会输出结果到 `.dead-code-results.json`。

      如果跳过此步骤，设置 `--skip-dead-code`。

  - id: GenerateReport
    description: |
      **📊 Step 4: 生成报告**

      将 jscpd JSON 报告和无用代码结果合并生成 Markdown 报告：

      ```bash
      python3 scripts/generate_report.py \
        --jscpd-report .jscpd-report/jscpd-report.json \
        --dead-code-report .dead-code-results.json \
        --output "{{output}}"
      ```

      报告包含：
      - 📊 概览统计表（重复块数、总行数、问题数、扫描范围等）
      - 🔴🟡🟢 重复代码严重程度分布
      - 🔄 重复代码 Top 20（含文件路径、行号、重复行数、严重程度）
      - 🗑️ 无用代码分类列表
      - 💡 重构建议

      输出示例见 `examples/` 目录。

  - id: Cleanup
    description: |
      **🧹 Step 5: 清理临时文件**

      ```bash
      rm -rf .jscpd-report .dead-code-results.json
      ```
