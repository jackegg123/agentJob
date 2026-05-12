---
name: java-code-scanner2
version: 2.0.0
description: >
  Scan Java projects for duplicate code and dead code (unused imports, fields,
  methods, and local variables). Detects redundant code via jscpd and unused
  code via javalang AST parser, generating both Markdown and Excel reports.
  扫描 Java 项目中的冗余代码和无用代码（未使用的 import、字段、方法、局部变量）。
  通过 jscpd 检测冗余代码，通过 javalang AST 解析器检测死代码，生成 Markdown + Excel 报告。

tags:
  - java
  - code-quality
  - scanner
  - duplicate-code
  - dead-code
  - lint

input:
  project_path:
    type: string
    description: >
      Absolute or relative path to the Java source directory to scan.
      If the path doesn't contain .java files directly, the agent should
      recursively find subdirectories containing Java files and pass one to the script.
      要扫描的 Java 源码目录的绝对或相对路径。
    required: true
  output:
    type: string
    description: >
      Output report path. `.md` suffix → Markdown, `.xlsx` suffix → Excel,
      otherwise generates both. Default: project_dir/java-code-report.{md,xlsx}
      报告输出路径。
    required: false
  min_lines:
    type: integer
    description: "Minimum duplicate line count for jscpd (default: 3)"
    required: false
    default: 3
  min_tokens:
    type: integer
    description: "Minimum duplicate token count for jscpd (default: 50)"
    required: false
    default: 50
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

      Prerequisites:
      - Python >= 3.9
      - Node.js >= 16 (for jscpd)

      Install commands:

      **Python dependencies:**
      ```bash
      pip install -r requirements.txt
      ```

      **jscpd (global):**
      ```bash
      npm install -g jscpd
      ```
      On Windows, if `jscpd` is not found after installation, add the npm global
      bin directory to your system PATH, then restart your terminal.

      Verify installation:
      ```bash
      python scripts/main.py --help
      ```

  - id: FindJavaDir
    description: |
      **🔍 Step 1: 找到正确的 Java 代码目录（智能体工作流）**

      本脚本不再内置交互式目录选择。智能体负责在调用脚本前找到正确的目录。

      ### 工作流

      1. **检查用户提供的路径**是否直接包含 `.java` 文件
         ```bash
         find {{project_path}} -maxdepth 1 -name "*.java" | head -3
         ```
      2. 如果有 Java 文件 → 直接使用该路径作为 `--project-path`
      3. 如果没有 → **递归查找**包含 Java 文件的子目录：
         ```bash
         find {{project_path}} -name "*.java" -not -path "*/test/*" -not -path "*/target/*" | head -20
         ```
      4. 分析找到的 Java 文件分布，**选择一个最合适的目录**传给脚本：
         - 优先选择 `src/main/java` 目录
         - 如果没有标准目录结构，选择 Java 文件数量最多的父目录
         - 将选中的目录作为 `--project-path` 参数

      ### 示例

      用户说 "扫描 /home/user/my-java-project"：

      ```
      # 智能体执行
      # 1. 检查根目录
      find /home/user/my-java-project -maxdepth 1 -name "*.java"
      # 结果: 空

      # 2. 递归查找
      find /home/user/my-java-project -name "*.java" -not -path "*/test/*" | head -5
      # 输出:
      # /home/user/my-java-project/module-a/src/main/java/com/example/Service.java
      # /home/user/my-java-project/module-a/src/main/java/com/example/Controller.java
      # /home/user/my-java-project/module-b/src/main/java/com/example/Dao.java

      # 3. 智能体确定：最佳扫描目录是项目根目录（jscpd 会递归扫描子目录）
      # → 使用 --project-path /home/user/my-java-project
      ```

  - id: Run
    description: |
      **🚀 Step 2: 运行扫描**

      使用在 Step 1 中找到的目录路径执行扫描。

      **基本用法:**
      ```bash
      python3 scripts/main.py --project-path "{{java_source_dir}}"
      ```

      **指定输出路径:**
      ```bash
      # Markdown 报告
      python3 scripts/main.py --project-path "{{java_source_dir}}" --output ./java-scan-report.md

      # Excel 报告
      python3 scripts/main.py --project-path "{{java_source_dir}}" --output ./java-scan-report.xlsx

      # 同时生成两种（默认）
      python3 scripts/main.py --project-path "{{java_source_dir}}" --output ./java-scan-report
      ```

      **自定义扫描参数:**
      ```bash
      # 更严格的参数
      python3 scripts/main.py --project-path ./src --min-lines 5 --min-tokens 100

      # 更宽松的参数
      python3 scripts/main.py --project-path ./src --min-lines 2 --min-tokens 30
      ```

      **跳过特定扫描:**
      ```bash
      # 只扫描无用代码
      python3 scripts/main.py --project-path ./src --skip-jscpd

      # 只扫描重复代码
      python3 scripts/main.py --project-path ./src --skip-dead-code
      ```

      **Windows (cmd):**
      ```cmd
      python scripts\main.py --project-path C:\project\src --output report.md
      ```

  - id: Report
    description: |
      **📊 Step 3: 阅读报告**

      脚本会生成两种格式的报告：

      ### Markdown 报告（推荐阅读）

      包含：
      - 📊 概览统计表（重复块数、总行数、问题数、扫描范围等）
      - 🔴🟡🟢 严重程度分布
      - 🔄 重复代码 Top 20（含文件路径、行号、重复行数、严重程度）
      - 🗑️ 无用代码分类（未使用的 import/字段/方法/局部变量）
      - 💡 重构建议

      示例输出结构：
      ```markdown
      # Java 代码质量扫描报告

      **项目**: my-project
      **扫描时间**: 2026-05-12 14:30 CST
      **扫描范围**: /path/to/src

      ## 📊 概览统计
      | 指标 | 数值 |
      |------|------|
      | 重复代码块数量 | 12 个 |
      | 重复代码总行数 | 345 行 |
      ...

      ## 🔄 重复代码 Top 20
      ### 1. 🔴 Service.java (行 45-78)
      - **文件**: `com/example/Service.java`
      - **重复行数**: 34 行
      - **严重程度**: 高
      - **详情**: 该代码块与文件 [AdminService.java] 第 52-85 行存在重复
      ...

      ## 🗑️ 无用代码
      ### 类型分布
      | 类型 | 数量 |
      |------|------|
      | 未使用的 import | 23 |
      | 未使用的 private 字段 | 5 |
      ...

      ## 💡 重构建议
      1. **优先处理 3 处高严重度重复代码**：建议提取公共基类或工具类
      ...
      ```

      ### Excel 报告（详细明细）

      包含两个 Sheet：
      - **冗余重复代码**：每条记录包含重要程度（高/中/低）、文件路径、行号、重复位置详情
      - **无用代码**：每条记录包含重要程度、文件路径、行号、为什么无用
      - 高/中重要程度行分别用红色/黄色背景突出显示
      - 按重要程度从高到低排序

  - id: Cleanup
    description: |
      扫描完成后自动清理临时文件。报告文件保留在指定输出路径。
