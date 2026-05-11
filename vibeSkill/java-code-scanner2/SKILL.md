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
      Check and install required dependencies.
      检查并安装所需的依赖。
    shell:
      linux:
        command: >
          bash scripts/setup.sh
      windows:
        command: >
          powershell -ExecutionPolicy ByPass -File scripts/setup.ps1
          
          # 安装完成后请关闭当前终端重新打开，确保 PATH 刷新
          # 然后执行 Run 步骤

  - id: Run
    description: |
      Execute the Java code scanner against the target project.
      对目标项目执行 Java 代码扫描。
    shell:
      linux:
        command: >
          python3 scripts/main.py --project-path "{{project_path}}"
          {% if output %}--output "{{output}}"{% endif %}
      windows:
        command: >
          python scripts/main.py --project-path "{{project_path}}"
          {% if output %}--output "{{output}}"{% endif %}
