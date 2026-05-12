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

      **⚠️ 重要：本工具为交互式使用，供 AI 智能体调用。执行过程中会打印目录列表并等待用户输入。**

      ## 执行流程（智能体工作流）

      ### 1. 运行命令
      执行以下命令启动扫描：

      **Linux / macOS:**
      ```bash
      python3 scripts/main.py --project-path "{{project_path}}"
      ```

      **Windows:**
      ```cmd
      python scripts\main.py --project-path "{{project_path}}"
      ```

      **可选参数：**
      - `--output /path/to/report.xlsx`：指定输出路径

      **跳过特定扫描：**
      Linux/macOS: `SKIP_JSCPD=1 python3 scripts/main.py ...`
      Windows: `set SKIP_JSCPD=1 && python scripts/main.py ...`

      ### 2. 读取输出并询问用户（关键交互步骤）

      脚本启动后会扫描项目结构，打印类似以下的目录列表：
      ```
      发现 N 个包含 Java 文件的目录：

        [1] module-a
        [2] module-b/sub-module
        [3] module-c
        ...

      请输入要扫描的目录路径（支持: 绝对路径 / 相对路径 / 逗号或空格分隔多个 / 直接回车=全部）:
      ```

      **你（智能体）需要做的是：**
      1. 将目录列表展示给用户
      2. 询问用户要扫描哪些模块。**用户不需要记住编号**，可以直接说目录名或路径。
      3. 根据用户的回答，**由你（智能体）** 将其转换为对应的路径后输入：
         - 用户说"扫 module-a"→ 输入 `module-a`（相对路径）
         - 用户说"扫 module-a 和 module-c"→ 输入 `module-a module-c`（空格分隔）
         - 用户说"扫 module-a, module-b/sub-module"→ 输入 `module-a,module-b/sub-module`
         - 用户说"全部扫描" → 直接回车
         - 也可以输入绝对路径如 `/home/user/project/module-a`

      ### 3. 兜底策略

      - 如果用户说"全部扫描"或类似意思 → 直接回车（不输入）
      - 如果用户指定了目录 → **你负责转换成路径字符串输入**
      - 如果用户表示不用管或不清楚 → 兜底扫描全部（直接回车）

      ### 4. 扫描完成

      扫描完成后会在指定路径生成 Excel 报告，报告中包含冗余代码和无用代码的详细信息。
      Excel 会生成在项目根目录（或 `--output` 指定的路径），报告路径会在执行完成后打印。

      **交互总结表：**
      | 用户意图 | 智能体输入 |
      |---|---|
      | 扫描所有模块 | 直接回车 |
      | 扫描单个模块 | `module-a`（相对路径） |
      | 扫描多个模块 | `module-a module-c`（空格分隔）或 `module-a,module-c` |
      | 没有明确指定 | 默认扫描全部（直接回车） |
