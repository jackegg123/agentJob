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

      ### 2. 解析脚本输出并生成选项（智能体 MUST DO）

      脚本启动后会扫描项目结构，打印类似以下的输出：
      ```
      发现 15 个包含 Java 文件的目录：

        [1] module-a/src/main/java/com/example/a
        [2] module-b/src/main/java/com/example/b
        [3] module-b/src/main/java/com/example/b/sub
        [4] module-c/src/main/java/com/example/c
        ...
      ```

      **⚠️ 你必须按以下步骤处理，保证交互体验统一：**

      **Step A - 解析目录列表**

      从脚本输出中提取所有 `[编号] 路径` 行，得到完整路径列表。

      **Step B - 生成选项（最多 10 个）**

      - 如果模块目录数量 ≤ 10，全部展示
      - 如果模块目录数量 > 10，按深度排序（浅层优先），只展示前 9 个 +
        一个 `[N] 扫描全部` 选项（即共 10 个选项）
      - 每个选项展示完整的相对路径，并尝试提取模块名作简短说明
      - 在最后追加一个「扫描全部」选项

      **Step C - 向用户展示选项，请求多选**

      必须用统一的选项格式展示给用户。示例格式：

      ```
      发现以下包含 Java 代码的模块目录，请选择要扫描哪些（支持多选）：

      1. module-user/src/main/java/com/example/user（用户模块）
      2. module-order/src/main/java/com/example/order（订单模块）
      3. module-common/src/main/java/com/example/common（公共模块）
      A. 扫描全部

      请输入编号（支持多选如 1,3，直接回车或输入 A = 全部）：
      ```

      **Step D - 根据用户选择映射为路径输入**

      用户选择编号后，你负责将编号映射为对应的完整路径，输入给脚本的提示行。

      映射规则：
      | 用户选择 | 你输入给脚本 |
      |---|---|
      | 选了编号 1,3 | 将选项 1 和 3 的路径用逗号连接输入 |
      | 选了「全部」或直接回车 | 直接回车（不输入任何内容） |
      | 用户没有明确回复 | 兜底：直接回车 = 扫描全部 |

      **❌ 不要做的事：**
      - 不要让用户自己输入路径字符串
      - 不要只返回文字说明而不生成编号选项
      - 不要把模块路径名称暴露给用户让用户手打
      - 一定要生成数字编号选项，用户只要输入编号

      ### 3. 兜底策略

      - 如果用户说"全部扫描" → 直接回车
      - 如果用户选择编号 → 你映射为路径字符串输入给脚本
      - 如果用户没有明确选择 → 直接回车（扫描全部）

      ### 4. 扫描完成

      扫描完成后会在指定路径生成 Excel 报告（默认在项目根目录下 `java-code-report.xlsx`）。
      报告包含两个 Sheet：冗余重复代码、无用代码。
      每条记录都有「重要程度」列（高/中/低），按优先级从高到低排序。
