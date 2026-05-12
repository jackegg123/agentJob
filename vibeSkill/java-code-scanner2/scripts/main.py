#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Java Code Scanner v2 - 核心扫描引擎
====================================
功能:
  1. 冗余重复代码扫描（基于 jscpd）
  2. 无用代码扫描（基于 javalang AST 解析器，检测未使用的 import/字段/方法/局部变量）

用法:
  python main.py --project-path /path/to/java/project [--output /path/to/report.xlsx]

环境变量:
  SKIP_JSCPD=1   跳过重复代码扫描
  SKIP_JSCPD2=1  同上（兼容不同命名）
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


# ====================================================================
# 常量
# ====================================================================

HEADER_DUPLICATE = [
    "项目相对路径", "文件名", "起始行", "结束行",
    "问题类型", "详细说明（重复代码位置）",
]

HEADER_DEAD_CODE = [
    "项目相对路径", "文件名", "起始行", "结束行",
    "问题类型", "详细说明（为什么无用）",
]

HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=11)
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
CELL_ALIGN = Alignment(vertical="top", wrap_text=True)
CELL_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin"),
)


# ====================================================================
# 工具函数
# ====================================================================

def info(msg: str) -> None:
    print(f"  [INFO] {msg}")

def ok(msg: str) -> None:
    print(f"  [OK]   {msg}")

def warn(msg: str) -> None:
    print(f"  [WARN] {msg}")

def err(msg: str) -> None:
    print(f"  [ERR]  {msg}")

def skip(msg: str) -> None:
    print(f"  [SKIP] {msg}")


def resolve_project_path(project_path: str) -> Path:
    """规范化并验证项目路径。"""
    path = Path(project_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"项目路径不存在: {project_path}")
    if not path.is_dir():
        raise NotADirectoryError(f"项目路径不是目录: {project_path}")
    return path


def rel_path(project_root: Path, abs_path: str) -> str:
    """获取文件相对路径。"""
    try:
        return str(Path(abs_path).resolve().relative_to(project_root))
    except (ValueError, RuntimeError):
        return Path(abs_path).name


def run_cmd(cmd: List[str], cwd: Optional[str] = None, timeout: int = 1800) -> subprocess.CompletedProcess:
    """安全执行外部命令。"""
    print(f"  [EXEC] {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            warn(f"退出码 {result.returncode}")
            if result.stderr:
                debug_stderr(result.stderr)
        return result
    except subprocess.TimeoutExpired:
        err(f"命令超时 ({timeout}s)")
        raise
    except FileNotFoundError:
        err(f"命令未找到: {cmd[0]}")
        raise
    except Exception as e:
        err(f"执行异常: {e}")
        raise


def debug_stderr(text: str) -> None:
    """截断打印 stderr。"""
    lines = text.strip().split("\n")
    for line in lines[:5]:
        print(f"       | {line}")
    if len(lines) > 5:
        print(f"       | ... (共 {len(lines)} 行)")


# ====================================================================
# 模块 0: 环境检查
# ====================================================================

def check_environment() -> Dict[str, bool]:
    """
    检查所有运行依赖。
    缺失时不中断，只做记录，调用方根据状态决定是否跳过对应模块。
    """
    print("\n" + "=" * 60)
    info("环境依赖检查")
    print("=" * 60)

    status: Dict[str, bool] = {}

    # Python 版本
    ver = sys.version_info
    py_ok = ver.major >= 3 and ver.minor >= 9
    ok(f"Python {ver.major}.{ver.minor}.{ver.micro}") if py_ok else err("需要 Python >= 3.9")
    status["python"] = py_ok

    # Node.js
    node_ok = shutil.which("node") is not None
    if node_ok:
        try:
            r = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
            ok(f"Node.js {r.stdout.strip()}")
        except Exception:
            ok("Node.js 已安装")
    else:
        warn("Node.js 未安装 (jscpd 需要)")
    status["node"] = node_ok

    # jscpd
    jscpd_ok = shutil.which("jscpd") is not None
    if jscpd_ok:
        ok("jscpd 已安装")
    elif shutil.which("npx"):
        ok("jscpd 将通过 npx 调用")
        jscpd_ok = True
    else:
        warn("jscpd 未安装 (将跳过冗余代码扫描)")
    status["jscpd"] = jscpd_ok

    # javalang
    jl_ok = False
    try:
        import javalang  # noqa
        jl_ok = True
        ok("javalang 已安装")
    except ImportError:
        warn("javalang 未安装 (将跳过无用代码扫描)")
    status["javalang"] = jl_ok

    # pandas + openpyxl
    pd_ok = False
    try:
        import pandas  # noqa
        pd_ok = True
        ok("pandas 已安装")
    except ImportError:
        warn("pandas 未安装 (无法生成 Excel)")

    xl_ok = False
    try:
        import openpyxl  # noqa
        xl_ok = True
        ok("openpyxl 已安装")
    except ImportError:
        warn("openpyxl 未安装 (无法生成 Excel)")

    if not pd_ok or not xl_ok:
        warn("请运行: pip install -r requirements.txt")

    print()
    return status


def scan_project_structure(project_root: Path) -> List[str]:
    """
    扫描项目目录结构，列出所有包含 .java 文件的子目录（相对路径）。
    用于让用户选择要扫描的模块/子目录。
    """
    print("\n" + "=" * 60)
    info("扫描项目目录结构...")
    print("=" * 60)

    java_dirs: Set[str] = set()
    for root, _, files in os.walk(str(project_root)):
        has_java = any(f.endswith(".java") for f in files)
        if has_java:
            rel = rel_path(project_root, root)
            if rel:
                java_dirs.add(rel)

    sorted_dirs = sorted(java_dirs)

    print(f"\n  发现 {len(sorted_dirs)} 个包含 Java 文件的目录：\n")
    for i, d in enumerate(sorted_dirs, 1):
        print(f"    [{i}] {d}")

    # 自动检测 Maven/Gradle 模块
    pom_files = list(project_root.rglob("pom.xml"))
    gradle_files = list(project_root.rglob("build.gradle")) + list(project_root.rglob("build.gradle.kts"))
    if pom_files:
        print(f"\n  检测到 Maven 项目（{len(pom_files)} 个 pom.xml）")
    if gradle_files:
        print(f"\n  检测到 Gradle 项目（{len(gradle_files)} 个构建文件）")

    print(f"\n  输入编号选择要扫描的目录，或输入 0 扫描整个项目根目录：")
    return sorted_dirs


def resolve_paths_from_input(project_root: Path, input_str: str) -> List[Path]:
    """
    解析用户输入的路径表达式，返回对应的绝对路径列表。

    支持：
    - 绝对路径：`/home/user/project/module-a`
    - 相对路径（相对于 project_root）：`module-a`、`src/main`
    - 逗号分隔多个路径：`module-a,module-b`
    - 空格分隔多个路径：`module-a module-b`（自动按空格/逗号分割）
    - 空输入：扫描全部模块（兜底）

    自动过滤掉不存在或不包含 Java 文件的目录，并给出警告。
    """
    raw = input_str.strip()

    # 空输入 → 全部模块
    if not raw:
        return []

    # 分割：逗号和连续空格都作为分隔符
    parts = [p.strip() for p in re.split(r"[,\s]+|，", raw) if p.strip()]

    resolved: List[Path] = []
    for part in parts:
        # 尝试作为绝对路径
        p = Path(part)
        if p.is_absolute():
            candidate = p.resolve()
        else:
            # 尝试作为相对路径（相对于 project_root）
            candidate = (project_root / part).resolve()

        if not candidate.exists():
            warn(f"路径不存在，已跳过: {part}")
            continue
        if not candidate.is_dir():
            warn(f"路径不是目录，已跳过: {part}")
            continue

        # 检查是否有 Java 文件
        has_java = any(f.endswith(".java") for f in os.listdir(str(candidate)))
        if not has_java:
            has_java = any(
                f.endswith(".java")
                for root, _, files in os.walk(str(candidate))
                for f in files
            )
        if not has_java:
            warn(f"路径中未找到 Java 文件，已跳过: {part}")
            continue

        resolved.append(candidate)

    # 去重（按绝对路径）
    seen: Set[str] = set()
    unique: List[Path] = []
    for p in resolved:
        s = str(p)
        if s not in seen:
            seen.add(s)
            unique.append(p)

    return unique


def select_scan_target(project_root: Path) -> List[Path]:
    """
    选择扫描目标路径。
    返回一个路径列表（可能包含多个模块）。

    行为：
    - 如果项目根目录包含 Java 文件，直接返回 [根目录]
    - 否则列出子模块目录，提示输入路径：
      - 用户/智能体可以输入模块的绝对路径或相对路径
      - 支持逗号或空格分隔多个路径
      - **直接回车（不输入）→ 扫描所有模块（兜底逻辑）**
    """
    # 检查根目录是否包含 Java 文件
    root_has_java = False
    for f in os.listdir(str(project_root)):
        if f.endswith(".java"):
            root_has_java = True
            break
    if not root_has_java:
        for root, _, files in os.walk(str(project_root)):
            depth = root[len(str(project_root)) + 1:].count(os.sep)
            if depth == 0 and any(f.endswith(".java") for f in files):
                root_has_java = True
                break

    if root_has_java:
        info("项目根目录包含 Java 文件，直接扫描根目录")
        return [project_root]

    # 列出子模块让用户/智能体选择
    dirs = scan_project_structure(project_root)

    if not dirs:
        warn("项目中未找到任何 Java 文件")
        return [project_root]

    hint = (
        "\n  请输入要扫描的目录路径（支持: 绝对路径 / 相对路径 / 逗号或空格分隔多个 / 直接回车=全部）:\n"
        "  > "
    )
    choice = input(hint).strip()

    selected = resolve_paths_from_input(project_root, choice)

    if not selected:
        # 没有有效输入或路径全部无效 → 扫描所有
        info("未指定有效路径，扫描所有模块")
        return [project_root / d for d in dirs]

    names = [str(p.relative_to(project_root)) if project_root in p.parents else str(p) for p in selected]
    info(f"将扫描 {len(selected)} 个目录: {names}")
    return selected


# ====================================================================
# 模块 1: 冗余代码扫描 (jscpd)
# ====================================================================

def scan_duplicate(scan_target: Path, temp_dir: str, project_root: Path) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    执行 jscpd 扫描并解析 JSON 报告。

    Args:
        scan_target: 要扫描的目标目录（可能是子模块）。
        temp_dir: 临时目录，用于存放 jscpd 输出。
        project_root: 项目根目录，用于计算相对路径。

    Returns:
        (结果列表, 错误信息)。错误信息为 None 表示扫描正常完成。
    """
    print("\n" + "=" * 60)
    info("冗余重复代码扫描 - jscpd")
    print("=" * 60)

    results: List[Dict[str, Any]] = []
    error_msg: Optional[str] = None

    # 先检查目标目录是否有 Java 文件
    java_count = 0
    for root, _, files in os.walk(str(scan_target)):
        java_count += sum(1 for f in files if f.endswith(".java"))

    if java_count == 0:
        err_msg = f"目标目录中没有找到任何 Java 文件: {scan_target}"
        err(err_msg)
        return results, err_msg

    info(f"目标目录包含 {java_count} 个 Java 文件")

    try:
        # Windows 下 npx 可能找不到 PATH，先尝试直接使用 jscpd
        jscpd_path = shutil.which("jscpd")
        if jscpd_path:
            cmd = [
                jscpd_path,
                str(scan_target),
                "--pattern", "**/*.java",
                "--reporters", "json",
                "--output", temp_dir,
                "--threshold", "0",
                "--min-lines", "6",
                "--min-tokens", "50",
            ]
        else:
            cmd = [
                "npx", "jscpd",
                str(scan_target),
                "--pattern", "**/*.java",
                "--reporters", "json",
                "--output", temp_dir,
                "--threshold", "0",
                "--min-lines", "6",
                "--min-tokens", "50",
            ]
        result = run_cmd(cmd, cwd=str(scan_target), timeout=600)

        # 检查 jscpd 输出是否有错误提示
        stderr_text = result.stderr.strip() if result.stderr else ""
        if result.returncode != 0:
            if "No files found" in stderr_text or "no files" in stderr_text.lower():
                err_msg = f"jscpd 未找到匹配的 Java 文件（退出码 {result.returncode}）: {stderr_text[:300]}"
                err(err_msg)
                return results, err_msg
            else:
                err_msg = f"jscpd 执行异常（退出码 {result.returncode}）: {stderr_text[:300]}"
                err(err_msg)
                return results, err_msg

        # 查找生成的 JSON 报告
        report_path: Optional[str] = None
        for root, _, files in os.walk(temp_dir):
            for f in files:
                if f.endswith(".json") and "jscpd" in f.lower():
                    report_path = os.path.join(root, f)
                    break
            if report_path:
                break

        if not report_path:
            for root, _, files in os.walk(temp_dir):
                for f in files:
                    if f.endswith(".json"):
                        report_path = os.path.join(root, f)
                        break
                if report_path:
                    break

        if not report_path:
            info("jscpd 未生成报告，未发现重复代码。")
            return results, None

        info(f"解析报告: {report_path}")
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        duplicates = data.get("duplicates", [])
        info(f"发现 {len(duplicates)} 处重复")

        for dup in duplicates:
            try:
                first = dup.get("first", {})
                second = dup.get("second", {})

                def get_line(loc) -> int:
                    if isinstance(loc, dict):
                        return loc.get("line", 0)
                    return loc or 0

                f_file = first.get("name", "") or first.get("path", "")
                if not f_file:
                    continue
                f_start = get_line(first.get("start", first.get("startLine", 0)))
                f_end = get_line(first.get("end", first.get("endLine", 0)))

                s_file = second.get("name", "") or second.get("path", "")
                if not s_file:
                    continue
                s_start = get_line(second.get("start", second.get("startLine", 0)))
                s_end = get_line(second.get("end", second.get("endLine", 0)))

                s_filename = os.path.basename(s_file)
                desc = (
                    f"该代码块与文件 [{s_filename}] 第 {s_start}-{s_end} 行存在重复"
                    f" (文件: {rel_path(project_root, s_file)})"
                )

                results.append({
                    "relative_path": rel_path(project_root, f_file),
                    "filename": os.path.basename(f_file),
                    "start_line": f_start,
                    "end_line": f_end,
                    "issue_type": "冗余重复代码",
                    "description": desc,
                })
            except Exception as e:
                warn(f"解析 duplicate 记录时异常: {e}")
                continue

        return results, None

    except subprocess.TimeoutExpired:
        err_msg = "jscpd 扫描超时（超过 600 秒）"
        err(err_msg)
        return results, err_msg
    except FileNotFoundError:
        err_msg = "jscpd 命令未找到，请确认已安装: npm install -g jscpd"
        err(err_msg)
        return results, err_msg
    except Exception as e:
        err_msg = f"jscpd 扫描异常: {e}"
        err(err_msg)
        return results, err_msg


# ====================================================================
# 模块 2: 无用代码扫描 (javalang AST)
# ====================================================================

def scan_dead_code(scan_target: Path, project_root: Path) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    使用 javalang 解析 Java 文件的 AST，检测以下无用代码：
      1. 未使用的 import
      2. 未使用的 private 字段
      3. 未使用的 private 方法
      4. 未使用的局部变量

    Args:
        scan_target: 要扫描的目标目录（可能是子模块）。
        project_root: 项目根目录，用于计算相对路径。

    Returns:
        格式化后的扫描结果列表。
    """
    print("\n" + "=" * 60)
    info("无用代码扫描 - javalang AST")
    print("=" * 60)

    import javalang

    results: List[Dict[str, Any]] = []

    # 收集所有 Java 文件
    java_files: List[Path] = []
    for root, _, files in os.walk(str(scan_target)):
        for f in files:
            if f.endswith(".java"):
                java_files.append(Path(root) / f)

    info(f"找到 {len(java_files)} 个 Java 文件，开始分析...")
    parsed_count = 0
    skipped_count = 0

    for jf in java_files:
        # 大文件处理策略
        try:
            file_size = jf.stat().st_size
        except OSError:
            skipped_count += 1
            continue

        if file_size > 1024 * 1024:
            warn(f"文件过大，回退正则检测: {rel_path(project_root, str(jf))}")
            try:
                file_results = _dead_code_regex_only(jf, project_root)
                results.extend(file_results)
            except Exception as e:
                warn(f"正则回退检测异常: {e}")
            skipped_count += 1
            continue

        # 读取源码
        try:
            with open(jf, "r", encoding="utf-8", errors="replace") as fh:
                source = fh.read()
        except Exception as e:
            warn(f"读取失败: {rel_path(project_root, str(jf))} - {e}")
            skipped_count += 1
            continue

        # 用 javalang 解析 AST
        try:
            tree = javalang.parse.parse(source)
        except javalang.parser.JavaSyntaxError as e:
            at_line = getattr(e.at, 'line', '?') if hasattr(e, 'at') else '?'
            warn(f"语法错误，跳过: {rel_path(project_root, str(jf))} at line {at_line}")
            skipped_count += 1
            continue
        except Exception as e:
            warn(f"解析异常: {rel_path(project_root, str(jf))} - {e}")
            skipped_count += 1
            continue

        parsed_count += 1
        relative = rel_path(project_root, str(jf))
        filename = jf.name
        source_lines = source.split("\n")

        # 用 try-except 包裹每个文件的完整分析，防止异常中断整个扫描
        try:
            _analyze_file(tree, source_lines, relative, filename, results)
        except Exception as e:
            warn(f"文件分析异常 ({relative}): {e}")
            skipped_count += 1
            continue

        # 进度提示
        if parsed_count % 50 == 0:
            info(f"已分析 {parsed_count}/{len(java_files)} 个文件...")

    info(f"分析完成: 成功解析 {parsed_count} 个, 跳过 {skipped_count} 个")
    info(f"发现 {len(results)} 处死代码问题")
    return results, None


# ====================================================================
# 模块 2 子函数: 单文件分析
# ====================================================================

def _analyze_file(
    tree: Any, source_lines: List[str],
    relative: str, filename: str, results: List[Dict[str, Any]]
) -> None:
    """
    对单个 Java 文件执行 4 种无用代码检测。
    每种检测独立 try-except，防止单步异常丢弃全部结果。
    """
    try:
        _detect_unused_imports(tree, source_lines, relative, filename, results)
    except Exception as e:
        warn(f"  import 检测异常 ({filename}): {e}")

    try:
        _detect_unused_fields(tree, source_lines, relative, filename, results)
    except Exception as e:
        warn(f"  字段检测异常 ({filename}): {e}")

    try:
        _detect_unused_methods(tree, source_lines, relative, filename, results)
    except Exception as e:
        warn(f"  方法检测异常 ({filename}): {e}")

    try:
        _detect_unused_locals(tree, source_lines, relative, filename, results)
    except Exception as e:
        warn(f"  局部变量检测异常 ({filename}): {e}")


def _detect_unused_imports(
    tree: Any, source_lines: List[str],
    relative: str, filename: str, results: List[Dict[str, Any]]
) -> None:
    """检测未使用的 import 语句。"""
    for imp in tree.imports:
        if not imp.path:
            continue
        try:
            short_name = imp.path.split(".")[-1]
            if short_name == "*":
                pkg_prefix = imp.path.rsplit(".", 1)[0] + "."
                used = any(
                    not line.strip().startswith("import") and pkg_prefix[:-1] in line
                    for line in source_lines
                )
            else:
                used = any(
                    not line.strip().startswith("import")
                    and re.search(r'\b' + re.escape(short_name) + r'\b', line)
                    for line in source_lines
                )
            if not used:
                results.append({
                    "relative_path": relative, "filename": filename,
                    "start_line": (imp.position.line if imp.position else 1),
                    "end_line": (imp.position.line if imp.position else 1),
                    "issue_type": "未使用的 import",
                    "description": f"import '{imp.path}' 在文件中未被使用",
                })
        except re.error:
            continue
        except Exception:
            continue


def _detect_unused_fields(
    tree: Any, source_lines: List[str],
    relative: str, filename: str, results: List[Dict[str, Any]]
) -> None:
    """检测未使用的 private 字段。"""
    from javalang.tree import FieldDeclaration

    private_fields = []
    injection_fields = set()
    injection_keywords = {"Autowired", "Inject", "Resource", "Value"}

    for path, node in tree:
        try:
            if not isinstance(node, FieldDeclaration):
                continue
            modifiers = set(node.modifiers) if node.modifiers else set()
            if "private" not in modifiers:
                continue

            annotations = set()
            if hasattr(node, "annotations") and node.annotations:
                for ann in node.annotations:
                    if hasattr(ann, "name"):
                        annotations.add(ann.name)

            for decl in node.declarators:
                if decl.name == "serialVersionUID":
                    continue
                if annotations & injection_keywords:
                    injection_fields.add(decl.name)
                    continue
                private_fields.append((node, decl.name))
        except Exception:
            continue

    used_fields = set()
    for line_num, line in enumerate(source_lines, 1):
        for fnode, fn in private_fields:
            if fn in used_fields:
                continue
            try:
                if not re.search(r'\b' + re.escape(fn) + r'\b', line):
                    continue
            except re.error:
                continue
            if fnode.position and fnode.position.line == line_num:
                continue
            used_fields.add(fn)

    for fnode, fn in private_fields:
        if fn not in used_fields:
            results.append({
                "relative_path": relative, "filename": filename,
                "start_line": (fnode.position.line if fnode.position else 1),
                "end_line": (fnode.position.line if fnode.position else 1),
                "issue_type": "未使用的 private 字段",
                "description": f"private 字段 '{fn}' 声明后未被使用",
            })


def _detect_unused_methods(
    tree: Any, source_lines: List[str],
    relative: str, filename: str, results: List[Dict[str, Any]]
) -> None:
    """检测未使用的 private 方法。"""
    from javalang.tree import MethodDeclaration

    private_methods = []
    for path, node in tree:
        try:
            if not isinstance(node, MethodDeclaration):
                continue
            modifiers = set(node.modifiers) if node.modifiers else set()
            if "private" not in modifiers:
                continue
            if node.name == "main":
                continue
            private_methods.append((node, node.name))
        except Exception:
            continue

    used_methods = set()
    for line_num, line in enumerate(source_lines, 1):
        for mnode, mn in private_methods:
            if mn in used_methods:
                continue
            try:
                if not re.search(r'\b' + re.escape(mn) + r'\s*\(', line):
                    continue
            except re.error:
                continue
            if mnode.position and mnode.position.line == line_num:
                continue
            used_methods.add(mn)

    for mnode, mn in private_methods:
        if mn not in used_methods:
            results.append({
                "relative_path": relative, "filename": filename,
                "start_line": (mnode.position.line if mnode.position else 1),
                "end_line": (mnode.position.line if mnode.position else 1),
                "issue_type": "未使用的 private 方法",
                "description": f"private 方法 '{mn}' 定义后未被调用",
            })


def _detect_unused_locals(
    tree: Any, source_lines: List[str],
    relative: str, filename: str, results: List[Dict[str, Any]]
) -> None:
    """检测未使用的局部变量（声明后只有赋值没有读取）。"""
    from javalang.tree import LocalVariableDeclaration

    local_vars = []
    for path, node in tree:
        try:
            if not isinstance(node, LocalVariableDeclaration):
                continue
            for decl in node.declarators:
                decl_line = node.position.line if node.position else 1
                local_vars.append((decl.name, decl_line))
        except Exception:
            continue

    used_locals = set()
    for line_num, line in enumerate(source_lines, 1):
        for lv_name, decl_line in local_vars:
            if lv_name in used_locals:
                continue
            if line_num <= decl_line:
                continue
            try:
                if not re.search(r'\b' + re.escape(lv_name) + r'\b', line):
                    continue
            except re.error:
                continue
            # 仅在等号左侧出现不算"读取"
            if "=" in line:
                try:
                    if re.search(r'\b' + re.escape(lv_name) + r'\s*=', line):
                        continue
                except re.error:
                    pass
            used_locals.add(lv_name)

    for lv_name, decl_line in local_vars:
        if lv_name not in used_locals:
            results.append({
                "relative_path": relative, "filename": filename,
                "start_line": decl_line, "end_line": decl_line,
                "issue_type": "未使用的局部变量",
                "description": f"局部变量 '{lv_name}' 声明后仅赋值未读取",
            })


def _dead_code_regex_only(file_path: Path, project_root: Path) -> List[Dict[str, Any]]:
    """
    大文件回退方案: 仅用正则检测未使用的 import。
    对于超过大小阈值的文件，不做完整 AST 分析。
    """
    results: List[Dict[str, Any]] = []
    relative = rel_path(project_root, str(file_path))
    filename = file_path.name

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
    except Exception:
        return results

    source_lines = source.split("\n")
    import_pattern = re.compile(r'^import\s+(static\s+)?([a-zA-Z0-9_.*]+)\s*;')

    for line_num, line in enumerate(source_lines, 1):
        try:
            m = import_pattern.match(line.strip())
            if not m:
                continue
            full_path = m.group(2)
            short_name = full_path.split(".")[-1]
            if short_name == "*":
                continue

            used = False
            for i, sl in enumerate(source_lines, 1):
                if i == line_num:
                    continue
                if re.search(r'\b' + re.escape(short_name) + r'\b', sl):
                    used = True
                    break
            if not used:
                results.append({
                    "relative_path": relative, "filename": filename,
                    "start_line": line_num, "end_line": line_num,
                    "issue_type": "未使用的 import (正则回退)",
                    "description": f"import '{full_path}' 在文件中未被使用",
                })
        except re.error:
            continue
        except Exception:
            continue

    return results


# ====================================================================
# 模块 3: Excel 输出
# ====================================================================

def write_excel(
    dup_results: List[Dict[str, Any]],
    dead_results: List[Dict[str, Any]],
    output_path: str,
    scan_errors: Optional[List[str]] = None,
) -> Optional[str]:
    """
    将扫描结果写入格式化的 Excel 文件。
    如果无结果但有扫描异常信息，仍生成报告记录异常。

    Returns:
        输出路径，或 None（无结果且无异常时）。
    """
    total = len(dup_results) + len(dead_results)
    has_errors = scan_errors and len(scan_errors) > 0

    if total == 0 and not has_errors:
        print("\n" + "=" * 60)
        info("两次扫描均未发现问题，跳过 Excel 生成。")
        return None

    print("\n" + "=" * 60)
    info("聚合结果 & 生成 Excel")
    print("=" * 60)

    header_dup = HEADER_DUPLICATE
    header_dead = HEADER_DEAD_CODE

    try:
        df_dup = pd.DataFrame(dup_results) if dup_results else pd.DataFrame(columns=header_dup)
        if not df_dup.empty:
            df_dup = df_dup.rename(columns={
                "relative_path": header_dup[0], "filename": header_dup[1],
                "start_line": header_dup[2], "end_line": header_dup[3],
                "issue_type": header_dup[4], "description": header_dup[5],
            })[header_dup]

        df_dead = pd.DataFrame(dead_results) if dead_results else pd.DataFrame(columns=header_dead)
        if not df_dead.empty:
            df_dead = df_dead.rename(columns={
                "relative_path": header_dead[0], "filename": header_dead[1],
                "start_line": header_dead[2], "end_line": header_dead[3],
                "issue_type": header_dead[4], "description": header_dead[5],
            })[header_dead]

        # 如果有扫描异常，在无用代码 Sheet 中添加说明行
        if has_errors:
            error_rows = []
            for i, err_msg in enumerate(scan_errors):
                error_rows.append({
                    header_dead[0]: "",
                    header_dead[1]: "",
                    header_dead[2]: "",
                    header_dead[3]: "",
                    header_dead[4]: f"扫描异常 #{i+1}",
                    header_dead[5]: err_msg,
                })
            df_error = pd.DataFrame(error_rows)
            df_dead = pd.concat([df_dead, df_error], ignore_index=True) if not df_dead.empty else df_error

        abspath = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(abspath) or ".", exist_ok=True)

        with pd.ExcelWriter(abspath, engine="openpyxl") as writer:
            df_dup.to_excel(writer, sheet_name="冗余重复代码", index=False)
            df_dead.to_excel(writer, sheet_name="无用代码", index=False)

        info(f"已写入: {abspath}")

        # 美化格式
        _format_excel(abspath)

        ok("格式美化完成")
        print(f"\n  [DONE] 报告: {abspath}")
        print(f"         - 冗余重复代码: {len(df_dup)} 条")
        print(f"         - 无用代码:      {len(df_dead)} 条")

        return abspath

    except Exception as e:
        err(f"Excel 写入异常: {e}")
        return None


def _format_excel(filepath: str) -> None:
    """美化 Excel 文件格式，异常不影响主流程。"""
    try:
        wb = load_workbook(filepath)
        for sheet in ("冗余重复代码", "无用代码"):
            ws = wb[sheet]
            try:
                for cell in ws[1]:
                    cell.font = HEADER_FONT
                    cell.fill = HEADER_FILL
                    cell.alignment = HEADER_ALIGN
                    cell.border = CELL_BORDER
                for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
                    for cell in row:
                        cell.alignment = CELL_ALIGN
                        cell.border = CELL_BORDER
                for ci in range(1, ws.max_column + 1):
                    cl = chr(64 + ci)
                    max_w = 10
                    for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=ci, max_col=ci):
                        for cell in row:
                            if cell.value:
                                w = sum(2 if ord(c) > 127 else 1 for c in str(cell.value))
                                max_w = max(max_w, w)
                    ws.column_dimensions[cl].width = min(max_w + 2, 80)
                ws.freeze_panes = "A2"
            except Exception:
                warn(f"Sheet '{sheet}' 美化异常，跳过")
                continue
        wb.save(filepath)
    except Exception as e:
        warn(f"Excel 格式美化异常: {e}")


# ====================================================================
# 主入口
# ====================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Java Code Scanner v2 - 冗余代码 + 无用代码扫描",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python main.py --project-path /path/to/java/project
  python main.py --project-path ./my-java-project --output ./report.xlsx

Windows (cmd):
  set SKIP_JSCPD=1 && python main.py --project-path C:\\project

Linux/macOS:
  SKIP_JSCPD=1 python3 main.py --project-path /path
        """,
    )
    parser.add_argument("--project-path", required=True, help="待扫描的 Java 项目根目录")
    parser.add_argument("--output", default=None, help="Excel 报告输出路径")
    args = parser.parse_args()

    print("=" * 60)
    print("  Java Code Scanner v2")
    print("  冗余代码扫描 (jscpd) + 无用代码扫描 (javalang AST)")
    print("=" * 60)

    # 1. 验证项目路径
    try:
        project_root = resolve_project_path(args.project_path)
        info(f"项目: {project_root}")
    except (FileNotFoundError, NotADirectoryError) as e:
        err(str(e))
        sys.exit(1)

    output_path = args.output or os.path.join(str(project_root), "java-code-report.xlsx")
    info(f"输出: {output_path}")

    # 2. 环境检查
    env = check_environment()

    # 3. 扫描目标路径选择（支持多模块项目）
    scan_targets = select_scan_target(project_root)
    info(f"待扫描模块: {len(scan_targets)} 个")

    # 4. 创建临时目录
    tmpdir = tempfile.TemporaryDirectory(prefix="java-code-scanner-")
    info(f"临时目录: {tmpdir.name}\n")

    dup_results: List[Dict[str, Any]] = []
    dead_results: List[Dict[str, Any]] = []
    scan_errors: List[str] = []  # 记录扫描异常信息，写入报告中

    skip_jscpd = os.environ.get("SKIP_JSCPD", "").lower() in ("1", "true", "yes")
    skip_jscpd2 = os.environ.get("SKIP_JSCPD2", "").lower() in ("1", "true", "yes")

    try:
        # 5. 对每个目标模块执行扫描
        for i, scan_root in enumerate(scan_targets, 1):
            module_label = f"模块 {i}/{len(scan_targets)}"
            print(f"\n{'=' * 60}")
            info(f"{module_label}: {scan_root}")
            print(f"{'=' * 60}")

            # 5a. 冗余代码扫描
            if skip_jscpd or skip_jscpd2:
                skip("SKIP_JSCPD 已设置，跳过")
            elif not env.get("jscpd", False):
                skip("jscpd 未安装，跳过")
            else:
                dup_batch, dup_err = scan_duplicate(scan_root, tmpdir.name, project_root)
                dup_results.extend(dup_batch)
                if dup_err:
                    scan_errors.append(f"[{module_label} 冗余代码] {dup_err}")

            # 5b. 无用代码扫描
            if not env.get("javalang", False):
                skip("javalang 未安装，跳过")
            else:
                dead_batch, dead_err = scan_dead_code(scan_root, project_root)
                dead_results.extend(dead_batch)
                if dead_err:
                    scan_errors.append(f"[{module_label} 无用代码] {dead_err}")

            info(f"{module_label} 扫描完成")

        # 6. 生成 Excel（如果有异常信息也记录）
        if scan_errors:
            info(f"扫描过程存在 {len(scan_errors)} 个异常")
            for se in scan_errors:
                err(se)
        write_excel(dup_results, dead_results, output_path, scan_errors)

        # 7. 汇总
        total = len(dup_results) + len(dead_results)
        print(f"\n  {'=' * 58}")
        print(f"  扫描汇总: 共 {total} 处问题（共扫描 {len(scan_targets)} 个模块）")
        print(f"    - 冗余重复代码: {len(dup_results)} 处")
        print(f"    - 无用代码:     {len(dead_results)} 处")
        print(f"  {'=' * 58}")

    except KeyboardInterrupt:
        warn("用户中断")
        sys.exit(130)
    except Exception as e:
        err(f"扫描异常: {e}")
        if dup_results or dead_results:
            try:
                write_excel(dup_results, dead_results, output_path)
            except Exception:
                pass
        sys.exit(1)
    finally:
        try:
            tmpdir.cleanup()
        except Exception:
            pass

    print(f"\n  [DONE] 扫描完成！")


if __name__ == "__main__":
    main()
