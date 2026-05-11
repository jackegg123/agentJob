---
name: java-code-scanner
version: 1.1.0
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

## Description

A Java code quality scanner that detects (1) duplicate/redundant code using `jscpd`, and (2) dead/unused code using JetBrains `Qodana JVM Community`. Results are aggregated into a formatted Excel report with two sheets.

## Steps

### #Init

#### 系统要求

- **Python** ≥ 3.9（`python3 --version` 确认）
- **Node.js** ≥ 16（`node --version` 确认，用于运行 jscpd）
- **Qodana CLI**（用于运行 Qodana JVM Community 扫描）

#### 安装依赖

**macOS / Linux：**

```bash
# 1. 安装 Python 依赖
pip3 install -r requirements.txt

# 2. 安装 jscpd
npm install -g jscpd

# 3. 安装 Qodana CLI
curl -fsSL https://jb.gg/qodana-cli/install | bash

# 或一键运行安装脚本
bash scripts/setup.sh
```

**Windows（PowerShell 管理员模式）：**

```powershell
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 安装 jscpd
npm install -g jscpd

# 3. 安装 Qodana CLI
# 从 https://github.com/JetBrains/qodana-cli/releases 下载 qodana_windows_x86_64.zip
# 解压后将 qodana.exe 所在目录加入系统 PATH 环境变量
# 验证安装：qodana --version
```

> ⚠️ `setup.sh` 仅支持 Linux/macOS。Windows 用户请按上方 PowerShell 步骤手动安装。

### #Run

Execute the scanner against a Java project.

**Linux / macOS:**

```bash
# Basic usage
python3 scripts/main.py --project-path /path/to/java/project

# Specify output path
python3 scripts/main.py --project-path /path --output ./report.xlsx

# Skip one of the scans
SKIP_JSCPD=1 python3 scripts/main.py --project-path /path
SKIP_QODANA=1 python3 scripts/main.py --project-path /path
```

**Windows (cmd):**

```cmd
# Basic usage
python scripts\main.py --project-path C:\path\to\java\project

# Specify output path
python scripts\main.py --project-path C:\path --output .\report.xlsx

# Skip one of the scans (PowerShell: $env:SKIP_JSCPD=1)
set SKIP_JSCPD=1 && python scripts\main.py --project-path C:\path
```

> The scanner will auto-detect missing dependencies and skip the relevant module.

## Structure

```
java-code-scanner/
├── SKILL.md              # Skill metadata and instructions
├── requirements.txt      # Python dependencies
├── scripts/
│   ├── main.py           # Core scanner logic
│   └── setup.sh          # Environment setup script
└── examples/
    └── run_example.sh    # Example invocation
```

## Input

| CLI Argument     | Type   | Required | Description                                           |
|------------------|--------|----------|-------------------------------------------------------|
| `--project-path` | string | Yes      | Absolute path to the Java project to scan             |
| `--output`       | string | No       | Path for the output Excel report (default: project)   |

## Output

The scanner only generates an `.xlsx` report when at least one scan module finds issues. If both scans find nothing, no file is written.

### Sheet: `冗余重复代码` (Duplicate Code)

| Column             | Description                                              |
|--------------------|----------------------------------------------------------|
| 项目相对路径       | File path relative to project root                       |
| 文件名             | Source file name                                         |
| 起始行             | Start line of duplicate block                            |
| 结束行             | End line of duplicate block                              |
| 问题类型           | Fixed: "冗余重复代码"                                    |
| 详细说明（重复代码位置） | Description pointing to the other duplicate location |

### Sheet: `无用代码` (Dead Code)

| Column                | Description                                          |
|-----------------------|------------------------------------------------------|
| 项目相对路径          | File path relative to project root                   |
| 文件名                | Source file name                                     |
| 起始行                | Start line of dead code                              |
| 结束行                | End line of dead code                                |
| 问题类型              | Qodana rule ID (e.g., UnusedDeclaration)             |
| 详细说明（为什么无用）| Qodana explanation                                   |

## Tools

No custom tools are defined. The skill executes local CLI tools (`jscpd`, `qodana`) via subprocess.
