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


# ====================================================================
# 模块 1: 冗余代码扫描 (jscpd)
# ====================================================================

def scan_duplicate(project_root: Path, temp_dir: str) -> List[Dict[str, Any]]:
    """
    执行 jscpd 扫描并解析 JSON 报告。

    Args:
        project_root: 项目根目录。
        temp_dir: 临时目录，用于存放 jscpd 输出。

    Returns:
        格式化后的扫描结果列表。
    """
    print("\n" + "=" * 60)
    info("冗余重复代码扫描 - jscpd")
    print("=" * 60)

    results: List[Dict[str, Any]] = []

    try:
        # Windows 下 npx 可能找不到 PATH，先尝试直接使用 jscpd
        jscpd_path = shutil.which("jscpd")
        if jscpd_path:
            cmd = [
                jscpd_path,
                str(project_root),
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
                str(project_root),
                "--pattern", "**/*.java",
                "--reporters", "json",
                "--output", temp_dir,
                "--threshold", "0",
                "--min-lines", "6",
                "--min-tokens", "50",
            ]
        run_cmd(cmd, cwd=str(project_root), timeout=600)

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
            # 兜底：遍历所有 json 文件
            for root, _, files in os.walk(temp_dir):
                for f in files:
                    if f.endswith(".json"):
                        report_path = os.path.join(root, f)
                        break
                if report_path:
                    break

        if not report_path:
            info("jscpd 未生成报告，未发现重复代码。")
            return results

        info(f"解析报告: {report_path}")
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        duplicates = data.get("duplicates", [])
        info(f"发现 {len(duplicates)} 处重复")

        for dup in duplicates:
            first = dup.get("first", {})
            second = dup.get("second", {})

            def get_line(loc) -> int:
                """获取行号，兼容 dict 或 int 格式。"""
                if isinstance(loc, dict):
                    return loc.get("line", 0)
                return loc or 0

            f_file = first.get("name", "") or first.get("path", "")
            f_start = get_line(first.get("start", first.get("startLine", 0)))
            f_end = get_line(first.get("end", first.get("endLine", 0)))

            s_file = second.get("name", "") or second.get("path", "")
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

        return results

    except Exception as e:
        err(f"jscpd 扫描异常: {e}")
        return results


# ====================================================================
# 模块 2: 无用代码扫描 (javalang AST)
# ====================================================================

def scan_dead_code(project_root: Path) -> List[Dict[str, Any]]:
    """
    使用 javalang 解析 Java 文件的 AST，检测以下无用代码：
      1. 未使用的 import
      2. 未使用的 private 字段
      3. 未使用的 private 方法
      4. 未使用的局部变量

    Args:
        project_root: 项目根目录。

    Returns:
        格式化后的扫描结果列表。
    """
    print("\n" + "=" * 60)
    info("无用代码扫描 - javalang AST")
    print("=" * 60)

    import javalang
    from javalang.tree import (
        Import, FieldDeclaration, MethodDeclaration,
        LocalVariableDeclaration, ClassDeclaration,
    )

    results: List[Dict[str, Any]] = []

    # 收集所有 Java 文件
    java_files: List[Path] = []
    for root, _, files in os.walk(str(project_root)):
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
            # > 1MB: 仅做简单的 import 正则检测
            warn(f"文件过大，回退正则检测: {rel_path(project_root, str(jf))}")
            file_results = _dead_code_regex_only(jf, project_root)
            results.extend(file_results)
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
            warn(f"语法错误，跳过: {rel_path(project_root, str(jf))} at line {e.at.line if hasattr(e, 'at') else '?'}")
            skipped_count += 1
            continue
        except Exception as e:
            warn(f"解析异常: {rel_path(project_root, str(jf))} - {e}")
            skipped_count += 1
            continue

        parsed_count += 1
        relative = rel_path(project_root, str(jf))
        filename = jf.name

        # ---------- 检测 1: 未使用的 import ----------
        source_lines = source.split("\n")
        imports_in_file: List[Import] = []
        for imp in tree.imports:
            if imp.path:
                imports_in_file.append(imp)

        for imp in imports_in_file:
            # 获取 import 的短名称
            short_name = imp.path.split(".")[-1]
            if short_name == "*":
                # 通配符 import: 检查是否有类型使用该包下的内容
                pkg_prefix = imp.path.rsplit(".", 1)[0] + "."
                used = False
                for line_num, line in enumerate(source_lines, 1):
                    if line.strip().startswith("import"):
                        continue
                    if pkg_prefix[:-1] in line or (
                        short_name := _find_full_qualifier(line, imp.path)
                    ):
                        used = True
                        break
                if not used:
                    results.append({
                        "relative_path": relative,
                        "filename": filename,
                        "start_line": (imp.position.line if imp.position else 1),
                        "end_line": (imp.position.line if imp.position else 1),
                        "issue_type": "未使用的 import",
                        "description": f"通配符导入 '{imp.path}' 在文件中未被使用",
                    })
                continue

            # 非通配符: 检查 short_name 是否在源码中出现
            used_in_source = False
            for line_num, line in enumerate(source_lines, 1):
                if line.strip().startswith("import"):
                    continue
                # 匹配单词边界，避免误匹配子串
                if re.search(r'\b' + re.escape(short_name) + r'\b', line):
                    used_in_source = True
                    break

            if not used_in_source:
                results.append({
                    "relative_path": relative,
                    "filename": filename,
                    "start_line": (imp.position.line if imp.position else 1),
                    "end_line": (imp.position.line if imp.position else 1),
                    "issue_type": "未使用的 import",
                    "description": f"import '{imp.path}' 在文件中未被使用",
                })

        # ---------- 检测 2: 未使用的 private 字段 ----------
        # 收集所有 private 字段声明
        private_fields: List[Tuple[FieldDeclaration, str]] = []
        field_annotation_names: Set[str] = set()

        for path, node in tree:
            if isinstance(node, FieldDeclaration):
                modifiers = set(node.modifiers) if node.modifiers else set()
                if "private" in modifiers:
                    annotations = set()
                    if hasattr(node, "annotations") and node.annotations:
                        for ann in node.annotations:
                            if hasattr(ann, "name"):
                                annotations.add(ann.name)
                    for decl in node.declarators:
                        field_name = decl.name
                        # 豁免 serialVersionUID
                        if field_name == "serialVersionUID":
                            continue
                        # 豁免有注入注解的字段
                        injection_annos = {"Autowired", "Inject", "Resource", "Value"}
                        if annotations & injection_annos:
                            field_annotation_names.add(field_name)
                            continue
                        private_fields.append((node, field_name))

        used_field_names: Set[str] = set()
        private_field_names = {fn for _, fn in private_fields}
        # 跳过豁免字段
        private_field_names -= field_annotation_names

        for line_num, line in enumerate(source_lines, 1):
            for fn in private_field_names:
                if re.search(r'\b' + re.escape(fn) + r'\b', line):
                    # 检查这一行是不是声明行
                    is_decl = False
                    for node, field_name in private_fields:
                        if fn == field_name and node.position and node.position.line == line_num:
                            is_decl = True
                            break
                    if not is_decl:
                        used_field_names.add(fn)

        for node, fn in private_fields:
            if fn in field_annotation_names:
                continue
            if fn not in used_field_names:
                results.append({
                    "relative_path": relative,
                    "filename": filename,
                    "start_line": (node.position.line if node.position else 1),
                    "end_line": (node.position.line if node.position else 1),
                    "issue_type": "未使用的 private 字段",
                    "description": f"private 字段 '{fn}' 声明后未被使用",
                })

        # ---------- 检测 3: 未使用的 private 方法 ----------
        private_methods: List[Tuple[MethodDeclaration, str]] = []
        for path, node in tree:
            if isinstance(node, MethodDeclaration):
                modifiers = set(node.modifiers) if node.modifiers else set()
                if "private" in modifiers:
                    # 豁免 main 方法
                    if node.name == "main":
                        continue
                    private_methods.append((node, node.name))

        used_methods: Set[str] = set()
        private_method_names = {mn for _, mn in private_methods}

        for line_num, line in enumerate(source_lines, 1):
            for mn in private_method_names:
                if re.search(r'\b' + re.escape(mn) + r'\s*\(', line):
                    is_def = False
                    for node, method_name in private_methods:
                        if mn == method_name and node.position and node.position.line == line_num:
                            is_def = True
                            break
                    if not is_def:
                        used_methods.add(mn)

        for node, mn in private_methods:
            if mn not in used_methods:
                results.append({
                    "relative_path": relative,
                    "filename": filename,
                    "start_line": (node.position.line if node.position else 1),
                    "end_line": (node.position.line if node.position else 1),
                    "issue_type": "未使用的 private 方法",
                    "description": f"private 方法 '{mn}' 定义后未被调用",
                })

        # ---------- 检测 4: 未使用的局部变量 ----------
        local_vars: List[Tuple[Any, str, int]] = []  # (node, name, decl_line)
        for path, node in tree:
            if isinstance(node, LocalVariableDeclaration):
                for decl in node.declarators:
                    lv_name = decl.name
                    lv_line = node.position.line if node.position else 1
                    local_vars.append((node, lv_name, lv_line))

        used_locals: Set[str] = set()
        for line_num, line in enumerate(source_lines, 1):
            for lv_node, lv_name, decl_line in local_vars:
                if lv_name in used_locals:
                    continue
                if line_num <= decl_line:
                    continue
                if re.search(r'\b' + re.escape(lv_name) + r'\b', line):
                    # 检查是不是在赋值（= 左侧）
                    if "=" in line and re.search(r'\b' + re.escape(lv_name) + r'\s*=', line):
                        continue
                    used_locals.add(lv_name)

        for lv_node, lv_name, decl_line in local_vars:
            if lv_name not in used_locals:
                results.append({
                    "relative_path": relative,
                    "filename": filename,
                    "start_line": decl_line,
                    "end_line": decl_line,
                    "issue_type": "未使用的局部变量",
                    "description": f"局部变量 '{lv_name}' 声明后仅赋值未读取",
                })

        # 进度提示（每 50 个文件报一次）
        if parsed_count % 50 == 0:
            info(f"已分析 {parsed_count}/{len(java_files)} 个文件...")

    info(f"分析完成: 成功解析 {parsed_count} 个, 跳过 {skipped_count} 个")
    info(f"发现 {len(results)} 处死代码问题")
    return results


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
        m = import_pattern.match(line.strip())
        if not m:
            continue
        full_path = m.group(2)
        short_name = full_path.split(".")[-1]
        if short_name == "*":
            continue
        # 检查是否在文件中被引用
        used = False
        for i, sl in enumerate(source_lines, 1):
            if i == line_num:
                continue
            if re.search(r'\b' + re.escape(short_name) + r'\b', sl):
                used = True
                break
        if not used:
            results.append({
                "relative_path": relative,
                "filename": filename,
                "start_line": line_num,
                "end_line": line_num,
                "issue_type": "未使用的 import (正则回退)",
                "description": f"import '{full_path}' 在文件中未被使用",
            })

    return results


def _find_full_qualifier(line: str, import_path: str) -> Optional[str]:
    """
    在代码行中查找是否使用了某个 import 路径中的全限定类名。
    例如 import 'com.example.util'，检查行中是否出现 'com.example.util.SomeClass'。
    """
    pkg_part = import_path.rstrip("*").rstrip(".")
    if pkg_part and pkg_part in line:
        return pkg_part
    return None


# ====================================================================
# 模块 3: Excel 输出
# ====================================================================

def write_excel(
    dup_results: List[Dict[str, Any]],
    dead_results: List[Dict[str, Any]],
    output_path: str,
) -> Optional[str]:
    """
    将扫描结果写入格式化的 Excel 文件。
    如果无结果则不生成文件。

    Returns:
        输出路径，或 None（无结果时）。
    """
    total = len(dup_results) + len(dead_results)
    if total == 0:
        print("\n" + "=" * 60)
        info("两次扫描均未发现问题，跳过 Excel 生成。")
        return None

    print("\n" + "=" * 60)
    info("聚合结果 & 生成 Excel")
    print("=" * 60)

    # 构建 DataFrame
    header_dup = HEADER_DUPLICATE
    header_dead = HEADER_DEAD_CODE

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

    abspath = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abspath) or ".", exist_ok=True)

    with pd.ExcelWriter(abspath, engine="openpyxl") as writer:
        df_dup.to_excel(writer, sheet_name="冗余重复代码", index=False)
        df_dead.to_excel(writer, sheet_name="无用代码", index=False)

    info(f"已写入: {abspath}")

    # 美化格式
    wb = load_workbook(abspath)
    for sheet in ("冗余重复代码", "无用代码"):
        ws = wb[sheet]
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

    wb.save(abspath)
    ok("格式美化完成")
    print(f"\n  [DONE] 报告: {abspath}")
    print(f"         - 冗余重复代码: {len(df_dup)} 条")
    print(f"         - 无用代码:      {len(df_dead)} 条")

    return abspath


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

    # 3. 创建临时目录
    tmpdir = tempfile.TemporaryDirectory(prefix="java-code-scanner-")
    info(f"临时目录: {tmpdir.name}\n")

    dup_results: List[Dict[str, Any]] = []
    dead_results: List[Dict[str, Any]] = []

    try:
        # 4. 冗余代码扫描
        skip_jscpd = os.environ.get("SKIP_JSCPD", "").lower() in ("1", "true", "yes")
        skip_jscpd2 = os.environ.get("SKIP_JSCPD2", "").lower() in ("1", "true", "yes")
        if skip_jscpd or skip_jscpd2:
            skip("SKIP_JSCPD 已设置，跳过")
        elif not env.get("jscpd", False):
            skip("jscpd 未安装，跳过")
        else:
            dup_results = scan_duplicate(project_root, tmpdir.name)

        # 5. 无用代码扫描
        if not env.get("javalang", False):
            skip("javalang 未安装，跳过")
        else:
            dead_results = scan_dead_code(project_root)

        # 6. 生成 Excel
        write_excel(dup_results, dead_results, output_path)

        # 7. 汇总
        total = len(dup_results) + len(dead_results)
        print(f"\n  {'=' * 58}")
        print(f"  扫描汇总: 共 {total} 处问题")
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
