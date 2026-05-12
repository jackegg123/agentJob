#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Report Generator — 从 jscpd JSON 报告 + 无用代码结果生成 Markdown 报告
========================================================================

用法:
  python generate_report.py --jscpd-report .jscpd-report/jscpd-report.json --output report.md
  python generate_report.py --jscpd-report report.json --dead-code-report dead.json --output report.md

依赖: Python 标准库 (无外部依赖)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

# ====================================================================
# 常量
# ====================================================================

PRIORITY_HIGH = "高"
PRIORITY_MEDIUM = "中"
PRIORITY_LOW = "低"

CST = timezone(timedelta(hours=8))

SEVERITY_LABEL = {PRIORITY_HIGH: "严重", PRIORITY_MEDIUM: "中等", PRIORITY_LOW: "轻微"}

# ====================================================================
# jscpd JSON 解析
# ====================================================================

def parse_jscpd_report(json_path: str) -> Dict[str, Any]:
    """
    解析 jscpd 4.x JSON 报告，返回结构化的重复代码结果。

    Returns:
        { "duplicates": [...], "summary": {...}, "error": None|str }
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {"duplicates": [], "summary": {}, "error": f"文件不存在: {json_path}"}
    except json.JSONDecodeError as e:
        return {"duplicates": [], "summary": {}, "error": f"JSON 解析失败: {e}"}

    stats = data.get("statistics", {}).get("total", {})

    summary = {
        "scanned_files": stats.get("sources", 0),
        "total_clones": stats.get("clones", 0),
        "total_dup_lines": stats.get("duplicatedLines", 0),
        "percentage": stats.get("percentage", 0),
    }

    duplicates_raw = data.get("duplicates", [])
    duplicates: List[Dict[str, Any]] = []

    for dup in duplicates_raw:
        try:
            first = dup.get("firstFile", {})
            second = dup.get("secondFile", {})

            f_file = first.get("name", "") or first.get("path", "")
            s_file = second.get("name", "") or second.get("path", "")
            if not f_file or not s_file:
                continue

            f_start = first.get("start", 0)
            f_end = first.get("end", 0)
            if not isinstance(f_start, int):
                f_start = first.get("startLoc", {}).get("line", 0)
            if not isinstance(f_end, int):
                f_end = first.get("endLoc", {}).get("line", 0)

            s_start = second.get("start", 0)
            s_end = second.get("end", 0)
            if not isinstance(s_start, int):
                s_start = second.get("startLoc", {}).get("line", 0)
            if not isinstance(s_end, int):
                s_end = second.get("endLoc", {}).get("line", 0)

            f_filename = os.path.basename(f_file)
            s_filename = os.path.basename(s_file)
            dup_lines = f_end - f_start + 1
            is_cross_file = f_filename != s_filename

            # 严重程度规则
            if dup_lines >= 20 and is_cross_file:
                priority = PRIORITY_HIGH
            elif dup_lines >= 10:
                priority = PRIORITY_MEDIUM
            else:
                priority = PRIORITY_LOW

            duplicates.append({
                "priority": priority,
                "first_file_rel": f_file,
                "first_filename": f_filename,
                "first_start": f_start,
                "first_end": f_end,
                "second_file_rel": s_file,
                "second_filename": s_filename,
                "second_start": s_start,
                "second_end": s_end,
                "dup_lines": dup_lines,
                "is_cross_file": is_cross_file,
                "fragment": dup.get("fragment", ""),
            })
        except Exception:
            continue

    # 按严重程度 + 重复行数排序
    ord_map = {PRIORITY_HIGH: 0, PRIORITY_MEDIUM: 1, PRIORITY_LOW: 2}
    duplicates.sort(key=lambda x: (ord_map.get(x["priority"], 99), -x["dup_lines"]))

    return {"duplicates": duplicates, "summary": summary, "error": None}


def parse_dead_code_report(json_path: str) -> Dict[str, Any]:
    """解析无用代码 JSON 报告。"""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "results": data.get("results", []),
            "summary": data.get("summary", {}),
            "error": None,
        }
    except FileNotFoundError:
        return {"results": [], "summary": {}, "error": None}
    except (json.JSONDecodeError, Exception) as e:
        return {"results": [], "summary": {}, "error": str(e)}


# ====================================================================
# Markdown 生成
# ====================================================================

def generate_markdown(
    dup_data: Dict[str, Any],
    dead_data: Dict[str, Any],
    scan_dir: Optional[str] = None,
    project_name: Optional[str] = None,
) -> str:
    """合并 jscpd 和无用代码结果，生成中文 Markdown 报告。"""
    duplicates = dup_data.get("duplicates", [])
    dup_summary = dup_data.get("summary", {})
    dup_error = dup_data.get("error")

    dead_results = dead_data.get("results", [])
    dead_summary = dead_data.get("summary", {})
    dead_error = dead_data.get("error")

    total_dup = len(duplicates)
    total_dead = len(dead_results)
    total = total_dup + total_dead

    now_str = datetime.now(CST).strftime("%Y-%m-%d %H:%M CST")
    proj = project_name or os.path.basename(scan_dir or os.getcwd())
    scan_range = scan_dir or os.getcwd()

    lines: List[str] = []
    lines.append("# Java 代码质量分析报告")
    lines.append("")
    lines.append(f"**项目**: {proj}")
    lines.append(f"**扫描时间**: {now_str}")
    lines.append(f"**扫描范围**: {scan_range}")
    lines.append("")

    # ── 概览统计表 ──
    lines.append("## 📊 概览统计")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 重复代码块数量 | {total_dup} 个 |")
    lines.append(f"| 重复代码总行数 | {dup_summary.get('total_dup_lines', 0)} 行 |")
    lines.append(f"| jscpd 扫描文件数 | {dup_summary.get('scanned_files', 0)} 个 |")
    lines.append(f"| jscpd 重复率 | {dup_summary.get('percentage', 0):.2f}% |")
    lines.append(f"| 无用代码问题数 | {total_dead} 处 |")
    lines.append(f"| javalang 分析文件数 | {dead_summary.get('scanned_files', 0)} 个 |")
    lines.append(f"| 问题总数 | {total} 处 |")
    lines.append("")

    # ── 扫描异常 ──
    if dup_error:
        lines.append(f"### ⚠️ jscpd 扫描异常")
        lines.append(f"```")
        lines.append(f"{dup_error}")
        lines.append(f"```")
        lines.append("")
    if dead_error:
        lines.append(f"### ⚠️ 无用代码扫描异常")
        lines.append(f"```")
        lines.append(f"{dead_error}")
        lines.append(f"```")
        lines.append("")

    # 全部无问题
    if total == 0:
        lines.append("## 🎉 扫描结果")
        lines.append("")
        lines.append("太棒了！未发现任何重复代码或无用代码问题。代码质量良好。")
        lines.append("")
        lines.append("### 建议")
        lines.append("")
        lines.append("1. 继续保持良好的编码习惯")
        lines.append("2. 定期使用本工具进行代码质量检查")
        lines.append("3. 新增代码模块时建议再次扫描")
        lines.append("")
        return "\n".join(lines)

    # ── 重复代码严重程度分布 ──
    high_count = sum(1 for d in duplicates if d.get("priority") == PRIORITY_HIGH)
    med_count = sum(1 for d in duplicates if d.get("priority") == PRIORITY_MEDIUM)
    low_count = sum(1 for d in duplicates if d.get("priority") == PRIORITY_LOW)

    if total_dup > 0:
        lines.append("### 重复代码严重程度分布")
        lines.append("")
        lines.append("| 严重程度 | 数量 | 说明 |")
        lines.append("|----------|------|------|")
        if high_count > 0:
            lines.append(f"| 🔴 高 | {high_count} | ≥20行 且跨文件 |")
        if med_count > 0:
            lines.append(f"| 🟡 中 | {med_count} | ≥10行 |")
        if low_count > 0:
            lines.append(f"| 🟢 低 | {low_count} | <10行 或同文件内 |")
        lines.append("")

    # ── 重复代码 Top ──
    if total_dup > 0:
        top_n = min(20, total_dup)
        lines.append(f"## 🔄 重复代码 Top {top_n}")
        lines.append("")
        lines.append(f"共检测到 {total_dup} 处重复，以下是最严重的 {top_n} 处：")
        lines.append("")

        for i, d in enumerate(duplicates[:top_n], 1):
            emoji = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(d["priority"], "")
            lines.append(f"### {i}. {emoji} `{d['first_filename']}` ↔ `{d['second_filename']}`")
            lines.append("")
            lines.append(f"- **文件 A**: `{d['first_file_rel']}` (行 {d['first_start']}-{d['first_end']})")
            lines.append(f"- **文件 B**: `{d['second_file_rel']}` (行 {d['second_start']}-{d['second_end']})")
            lines.append(f"- **重复行数**: {d['dup_lines']} 行")
            lines.append(f"- **严重程度**: {d['priority']} ({SEVERITY_LABEL.get(d['priority'], '')})")

            if d["fragment"]:
                frag = d["fragment"].strip()
                if len(frag) > 300:
                    frag = frag[:300] + "\n... (省略)"
                lines.append(f"- **重复片段**:")
                lines.append(f"  ```java")
                for fl in frag.split("\n"):
                    lines.append(f"  {fl}")
                lines.append(f"  ```")
            lines.append("")

    # ── 无用代码 ──
    if total_dead > 0:
        # 类型分布
        type_counts: Dict[str, int] = {}
        for r in dead_results:
            it = r.get("issue_type", "其他")
            type_counts[it] = type_counts.get(it, 0) + 1

        lines.append("## 🗑️ 无用代码")
        lines.append("")

        lines.append("### 类型分布")
        lines.append("")
        lines.append("| 类型 | 数量 |")
        lines.append("|------|------|")
        for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| {t} | {c} |")
        lines.append("")

        # 按类型+优先级排序
        ord_map = {PRIORITY_HIGH: 0, PRIORITY_MEDIUM: 1, PRIORITY_LOW: 2}
        sorted_dead = sorted(dead_results, key=lambda x: (
            ord_map.get(x.get("priority", PRIORITY_LOW), 99),
            x.get("issue_type", ""),
        ))

        dead_top_n = min(20, len(sorted_dead))
        lines.append(f"### Top {dead_top_n} 项")
        lines.append("")

        for i, item in enumerate(sorted_dead[:dead_top_n], 1):
            prio = item.get("priority", "")
            itype = item.get("issue_type", "?")
            emoji_map = {"未使用的 private 字段": "🔸", "未使用的 private 方法": "🔸",
                         "未使用的 import": "🔹", "未使用的局部变量": "🔹"}
            emoji = emoji_map.get(itype, "")
            lines.append(f"{i}. {emoji} [{prio}] **{itype}** — `{item.get('filename', '?')}`")
            lines.append(f"   - 文件: `{item.get('relative_path', '?')}`")
            lines.append(f"   - 行号: {item.get('start_line', 0)}")
            lines.append(f"   - 说明: {item.get('description', '')}")
            lines.append("")

    # ── 重构建议 ──
    lines.append("## 💡 重构建议")
    lines.append("")

    if high_count > 0:
        lines.append(f"1. **优先处理 {high_count} 处高严重度重复代码**：跨文件且行数 ≥20，建议提取公共基类或工具类")

    if med_count > 0:
        suffix = "，在重构高优先级代码时一并处理" if high_count > 0 else ""
        lines.append(f"2. **关注 {med_count} 处中等严重度重复**{suffix}")

    if total_dead > 0:
        n = 3 if (high_count > 0 or med_count > 0) else 1
        lines.append(f"{n}. **清理 {total_dead} 处无用代码**：未使用的 import、字段、方法和变量可以安全删除，减少代码噪音")
        unused_imports = sum(1 for r in dead_results if "import" in r.get("issue_type", ""))
        if unused_imports > 0:
            lines.append(f"   - 其中 {unused_imports} 个未使用的 import 可直接使用 IDE 自动清理")

    next_n = 4 if (high_count > 0 or med_count > 0) else (3 if total_dead > 0 else 2)
    lines.append(f"{next_n}. 重构后务必运行单元测试，确保功能不受影响")
    lines.append(f"{next_n + 1}. 建议将本工具集成到 CI/CD 流程中，定期扫描代码质量")
    lines.append("")

    return "\n".join(lines)


# ====================================================================
# 主入口
# ====================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="从 jscpd + 无用代码结果生成 Markdown 报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python generate_report.py --jscpd-report rpt.json -o report.md
  python generate_report.py --jscpd-report rpt.json --dead-code-report dead.json -o report.md
  python generate_report.py --jscpd-report rpt.json --scan-dir ./src -o report.md
        """,
    )
    parser.add_argument("--jscpd-report", default=None,
                        help="jscpd JSON 报告路径")
    parser.add_argument("--dead-code-report", default=None,
                        help="无用代码扫描 JSON 结果路径")
    parser.add_argument("--scan-dir", default=None,
                        help="扫描目录（用于报告头部）")
    parser.add_argument("--project-name", default=None,
                        help="项目名称（默认从 --scan-dir 提取）")
    parser.add_argument("--output", "-o", default="java-analysis-report.md",
                        help="输出 Markdown 文件路径")
    args = parser.parse_args()

    # 解析 jscpd 报告
    dup_data: Dict[str, Any] = {"duplicates": [], "summary": {}, "error": None}
    if args.jscpd_report:
        if not os.path.exists(args.jscpd_report):
            dup_data["error"] = f"jscpd 报告文件不存在: {args.jscpd_report}"
        else:
            dup_data = parse_jscpd_report(args.jscpd_report)
    else:
        dup_data["error"] = "未提供 jscpd 报告（--jscpd-report）"

    # 解析无用代码报告
    dead_data: Dict[str, Any] = {"results": [], "summary": {}, "error": None}
    if args.dead_code_report and os.path.exists(args.dead_code_report):
        dead_data = parse_dead_code_report(args.dead_code_report)

    # 生成报告
    md_content = generate_markdown(
        dup_data, dead_data,
        scan_dir=args.scan_dir,
        project_name=args.project_name,
    )

    output_path = args.output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    dup_count = len(dup_data.get("duplicates", []))
    dead_count = len(dead_data.get("results", []))
    print(f"✅ 报告已生成: {output_path}")
    print(f"   - 重复代码: {dup_count} 处")
    print(f"   - 无用代码: {dead_count} 处")
    print(f"   - 总计: {dup_count + dead_count} 处")


if __name__ == "__main__":
    main()
