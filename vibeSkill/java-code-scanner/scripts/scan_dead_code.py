#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dead Code Scanner — 独立的无用代码扫描脚本
===========================================
使用 javalang AST 解析器检测 Java 项目中的无用代码：
  1. 未使用的 import
  2. 未使用的 private 字段（排除 @Autowired/@Inject 等注入字段）
  3. 未使用的 private 方法
  4. 未使用的局部变量

用法:
  python scan_dead_code.py /path/to/java/src --output results.json
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

try:
    import javalang
except ImportError:
    print("错误: 需要安装 javalang，请运行: pip install javalang", file=sys.stderr)
    sys.exit(1)

# ====================================================================
# 常量
# ====================================================================

PRIORITY_HIGH = "高"
PRIORITY_MEDIUM = "中"
PRIORITY_LOW = "低"

EXCLUDE_DIRS = {".git", "node_modules", "target", "build", "out",
                ".idea", ".vscode", "__pycache__", "dist", "classes"}


def rel_path(project_root: Path, abs_path: str) -> str:
    try:
        return str(Path(abs_path).resolve().relative_to(project_root))
    except (ValueError, RuntimeError):
        return Path(abs_path).name


def warn(msg: str) -> None:
    print(f"  [WARN] {msg}", file=sys.stderr)


# ====================================================================
# 主扫描函数
# ====================================================================

def scan_dead_code(scan_target: Path) -> Dict[str, Any]:
    """
    扫描指定目录中的所有 Java 文件，返回检测结果。

    Returns:
        { "results": [...], "summary": {...} }
    """
    project_root = scan_target.resolve()

    results: List[Dict[str, Any]] = []
    summary = {
        "scanned_files": 0,
        "skipped_files": 0,
        "total_issues": 0,
    }

    # 收集所有 Java 文件
    java_files: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(str(scan_target)):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in filenames:
            if f.endswith(".java"):
                java_files.append(Path(dirpath) / f)

    print(f"  [INFO] 找到 {len(java_files)} 个 Java 文件，开始分析...")
    parsed_count = 0
    skipped_count = 0

    for jf in java_files:
        # 大文件跳过完整分析
        try:
            file_size = jf.stat().st_size
        except OSError:
            skipped_count += 1
            continue

        if file_size > 1024 * 1024:
            warn(f"文件过大，跳过: {rel_path(project_root, str(jf))}")
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

        # 解析 AST
        try:
            tree = javalang.parse.parse(source)
        except javalang.parser.JavaSyntaxError as e:
            at_line = getattr(e.at, "line", "?") if hasattr(e, "at") else "?"
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

        # 分析
        try:
            _analyze_file(tree, source_lines, relative, filename, results)
        except Exception as e:
            warn(f"文件分析异常 ({relative}): {e}")
            skipped_count += 1

        if parsed_count % 100 == 0:
            print(f"  [INFO] 已分析 {parsed_count}/{len(java_files)} 个文件...")

    summary["scanned_files"] = parsed_count
    summary["skipped_files"] = skipped_count
    summary["total_issues"] = len(results)

    print(f"  [INFO] 分析完成: 成功 {parsed_count} 个, 跳过 {skipped_count} 个")
    print(f"  [INFO] 发现 {len(results)} 处死代码问题")

    return {"results": results, "summary": summary}


# ====================================================================
# 单文件分析入口
# ====================================================================

def _analyze_file(tree: Any, source_lines: List[str],
                  relative: str, filename: str,
                  results: List[Dict[str, Any]]) -> None:
    """对单个 Java 文件执行 4 种无用代码检测。"""
    _detect_unused_imports(tree, source_lines, relative, filename, results)
    _detect_unused_fields(tree, source_lines, relative, filename, results)
    _detect_unused_methods(tree, source_lines, relative, filename, results)
    _detect_unused_locals(tree, source_lines, relative, filename, results)


# ====================================================================
# 检测 1: 未使用的 import
# ====================================================================

def _detect_unused_imports(tree: Any, source_lines: List[str],
                           relative: str, filename: str,
                           results: List[Dict[str, Any]]) -> None:
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
                    and re.search(r"\b" + re.escape(short_name) + r"\b", line)
                    for line in source_lines
                )
        except (re.error, Exception):
            continue

        if not used:
            results.append({
                "priority": PRIORITY_LOW,
                "relative_path": relative,
                "filename": filename,
                "start_line": (imp.position.line if imp.position else 1),
                "end_line": (imp.position.line if imp.position else 1),
                "issue_type": "未使用的 import",
                "description": f"import '{imp.path}' 在文件中未被使用",
            })


# ====================================================================
# 检测 2: 未使用的 private 字段
# ====================================================================

def _detect_unused_fields(tree: Any, source_lines: List[str],
                          relative: str, filename: str,
                          results: List[Dict[str, Any]]) -> None:
    from javalang.tree import FieldDeclaration

    private_fields: List[Tuple[Any, str]] = []
    injection_fields: Set[str] = set()
    injection_keywords = {"Autowired", "Inject", "Resource", "Value"}

    for _path, node in tree:
        try:
            if not isinstance(node, FieldDeclaration):
                continue
            modifiers = set(node.modifiers) if node.modifiers else set()
            if "private" not in modifiers:
                continue

            annotations: Set[str] = set()
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

    used_fields: Set[str] = set()
    for line_num, line in enumerate(source_lines, 1):
        for fnode, fn in private_fields:
            if fn in used_fields:
                continue
            try:
                if not re.search(r"\b" + re.escape(fn) + r"\b", line):
                    continue
            except re.error:
                continue
            if fnode.position and fnode.position.line == line_num:
                continue
            used_fields.add(fn)

    for fnode, fn in private_fields:
        if fn not in used_fields:
            results.append({
                "priority": PRIORITY_MEDIUM,
                "relative_path": relative,
                "filename": filename,
                "start_line": (fnode.position.line if fnode.position else 1),
                "end_line": (fnode.position.line if fnode.position else 1),
                "issue_type": "未使用的 private 字段",
                "description": f"private 字段 '{fn}' 声明后未被使用",
            })


# ====================================================================
# 检测 3: 未使用的 private 方法
# ====================================================================

def _detect_unused_methods(tree: Any, source_lines: List[str],
                           relative: str, filename: str,
                           results: List[Dict[str, Any]]) -> None:
    from javalang.tree import MethodDeclaration

    private_methods: List[Tuple[Any, str]] = []
    for _path, node in tree:
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

    used_methods: Set[str] = set()
    for line_num, line in enumerate(source_lines, 1):
        for mnode, mn in private_methods:
            if mn in used_methods:
                continue
            try:
                if not re.search(r"\b" + re.escape(mn) + r"\s*\(", line):
                    continue
            except re.error:
                continue
            if mnode.position and mnode.position.line == line_num:
                continue
            used_methods.add(mn)

    for mnode, mn in private_methods:
        if mn not in used_methods:
            results.append({
                "priority": PRIORITY_MEDIUM,
                "relative_path": relative,
                "filename": filename,
                "start_line": (mnode.position.line if mnode.position else 1),
                "end_line": (mnode.position.line if mnode.position else 1),
                "issue_type": "未使用的 private 方法",
                "description": f"private 方法 '{mn}' 定义后未被调用",
            })


# ====================================================================
# 检测 4: 未使用的局部变量
# ====================================================================

def _detect_unused_locals(tree: Any, source_lines: List[str],
                          relative: str, filename: str,
                          results: List[Dict[str, Any]]) -> None:
    from javalang.tree import LocalVariableDeclaration

    local_vars: List[Tuple[str, int]] = []
    for _path, node in tree:
        try:
            if not isinstance(node, LocalVariableDeclaration):
                continue
            for decl in node.declarators:
                decl_line = node.position.line if node.position else 1
                local_vars.append((decl.name, decl_line))
        except Exception:
            continue

    used_locals: Set[str] = set()
    for line_num, line in enumerate(source_lines, 1):
        for lv_name, decl_line in local_vars:
            if lv_name in used_locals:
                continue
            if line_num <= decl_line:
                continue
            try:
                if not re.search(r"\b" + re.escape(lv_name) + r"\b", line):
                    continue
            except re.error:
                continue
            if "=" in line:
                try:
                    if re.search(r"\b" + re.escape(lv_name) + r"\s*=", line):
                        continue
                except re.error:
                    pass
            used_locals.add(lv_name)

    for lv_name, decl_line in local_vars:
        if lv_name not in used_locals:
            results.append({
                "priority": PRIORITY_LOW,
                "relative_path": relative,
                "filename": filename,
                "start_line": decl_line,
                "end_line": decl_line,
                "issue_type": "未使用的局部变量",
                "description": f"局部变量 '{lv_name}' 声明后仅赋值未读取",
            })


# ====================================================================
# 主入口
# ====================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Java 无用代码扫描器 — javalang AST 分析",
    )
    parser.add_argument("scan_dir", help="要扫描的 Java 源码目录")
    parser.add_argument("--output", "-o", default=".dead-code-results.json",
                        help="输出 JSON 文件路径 (默认: .dead-code-results.json)")
    args = parser.parse_args()

    scan_target = Path(args.scan_dir)
    if not scan_target.exists():
        print(f"错误: 目录不存在: {args.scan_dir}", file=sys.stderr)
        sys.exit(1)
    if not scan_target.is_dir():
        print(f"错误: 不是目录: {args.scan_dir}", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("  无用代码扫描 - javalang AST")
    print("=" * 60)
    print(f"  [INFO] 扫描目标: {scan_target.resolve()}")

    result = scan_dead_code(scan_target)

    output_path = args.output
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n  [DONE] 结果已写入: {output_path}")
    print(f"         共 {result['summary']['total_issues']} 处问题")


if __name__ == "__main__":
    main()
