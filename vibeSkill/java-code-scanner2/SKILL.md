---
name: java-code-scanner2
version: 1.0.0
description: >
  Scan Java projects for duplicate code and dead code (unused imports, fields,
  methods, and local variables). Detects redundant code via jscpd and unused
  code via javalang AST parser, generating an Excel report with styled output.
  扫描 Java 项目中的冗余代码和死代码（未使用的 import、字段、方法、局部变量）。
  通过 jscpd 检测冗余代码，通过 javalang AST 解析器检测死代码，生成带样式的 Excel 报告。

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
      Absolute or relative path to the Java project root directory.
      Java 项目根目录的绝对或相对路径。
    required: true
  output:
    type: string
    description: >
      Path for the generated Excel report (default: project_dir/java-code-report.xlsx).
      Excel 报告输出路径（默认在项目目录下生成 java-code-report.xlsx）。
    required: false

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

  - id: Run
    description: |
      Execute the Java code scanner against the target project.
      对目标项目执行 Java 代码扫描。

      The scanner will first scan the project structure and list all directories
      containing Java files. If it's a multi-module project (no Java files in
      the root), it will ask you to select which module/subdirectory to scan.
      扫描器会先检查项目结构，列出所有包含 Java 文件的目录。
      如果是多模块项目，会提示选择要扫描的子模块。

      **Linux / macOS:**
      ```bash
      python3 scripts/main.py --project-path "{{project_path}}"
      ```

      **Windows:**
      ```cmd
      python scripts\main.py --project-path "{{project_path}}"
      ```

      **Skip one of the scans:**
      Linux/macOS: SKIP_JSCPD=1 python3 scripts/main.py ...
      Windows: set SKIP_JSCPD=1 && python scripts/main.py ...

      **Optional output path:**
      Add `--output /path/to/report.xlsx`
