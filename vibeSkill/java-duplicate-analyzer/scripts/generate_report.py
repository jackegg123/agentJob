#!/usr/bin/env python3
"""
Markdown 报告生成脚本

根据 jscpd 的 JSON 报告生成 Markdown 格式的分析报告。

Usage:
    python generate_report.py <jscpd-report.json> <output-markdown.md>
    
Example:
    python generate_report.py .jscpd-report/jscpd-report.json ./duplicate-report.md
"""

import sys
import json
from pathlib import Path
from datetime import datetime


def extract_filename(filepath):
    """从完整路径中提取文件名"""
    # 处理 dict 类型的 firstFile（如 jscpd 新版本）
    if isinstance(filepath, dict):
        filepath = filepath.get('name', '')
    if not filepath:
        return ""
    filepath = str(filepath).replace("\\", "/")
    return filepath.split("/")[-1]


def extract_path(filepath):
    """从完整路径中提取相对路径"""
    # 处理 dict 类型的 firstFile（如 jscpd 新版本）
    if isinstance(filepath, dict):
        filepath = filepath.get('name', '')
    if not filepath:
        return ""
    filepath = str(filepath).replace("\\", "/")
    return filepath


def get_line_info(dup, key):
    """获取行号信息，兼容新旧版本"""
    file_info = dup.get(key, {})
    if isinstance(file_info, dict):
        start = file_info.get('start', 0)
        end = file_info.get('end', 0)
    else:
        start = dup.get(f'{key}Start', 0)
        end = dup.get(f'{key}End', 0)
    return start, end


def generate_markdown_report(json_path, output_path):
    """根据 JSON 报告生成 Markdown 文件"""
    
    # 检查输入文件
    json_file = Path(json_path)
    if not json_file.exists():
        print(f"Error: JSON report not found: {json_path}")
        return False
    
    # 读取 JSON 数据
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return False
    
    # 获取统计数据
    stats = data.get('statistics', {})
    duplicates = data.get('duplicates', [])
    
    # 计算总重复行数
    total_lines = sum(dup.get('lines', 0) for dup in duplicates)
    
    # 获取检测时间
    detection_date = stats.get('detectionDate', 'N/A')
    if detection_date != 'N/A':
        try:
            # 解析 ISO 时间格式
            dt = datetime.fromisoformat(detection_date.replace('Z', '+00:00'))
            detection_date = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass
    
    # 按重复行数排序
    sorted_duplicates = sorted(duplicates, key=lambda x: x.get('lines', 0), reverse=True)
    
    # 生成 Markdown 内容
    md_content = f"""# Java 代码重复分析报告

## 概览

| 指标 | 数值 |
|------|------|
| 扫描时间 | {detection_date} |
| 重复块数量 | {len(duplicates)} 个 |
| 总重复行数 | {total_lines:,} 行 |
| 扫描范围 | hss-domain/src 目录 |

## 详细分析

### Top 10 严重重复代码

| 序号 | 第一个文件 | 第二个文件 | 重复位置 | 重复行数 | 严重程度 | 重构建议 |
|------|------------|------------|----------|----------|----------|----------|
"""
    
    # 添加 Top 10 数据
    for i, dup in enumerate(sorted_duplicates[:10], start=1):
        first_file = extract_filename(dup.get('firstFile', ''))
        second_file = extract_filename(dup.get('secondFile', ''))
        first_path = extract_path(dup.get('firstFile', ''))
        second_path = extract_path(dup.get('secondFile', ''))
        lines = dup.get('lines', 0)
        
        # 获取行号信息
        first_start, first_end = get_line_info(dup, 'firstFile')
        second_start, second_end = get_line_info(dup, 'secondFile')
        
        # 确定严重程度
        if lines >= 100:
            severity = "🔴 严重"
            refactor = "建议提取公共基类或工具类"
        elif lines >= 50:
            severity = "🟠 较严重"
            refactor = "建议抽取公共方法"
        elif lines >= 20:
            severity = "🟡 一般"
            refactor = "可考虑抽取公共方法"
        else:
            severity = "🟢 轻微"
            refactor = "保持观察"
        
        md_content += f"| {i} | {first_file} | {second_file} | {first_file} (行 {first_start}-{first_end}) ↔ {second_file} (行 {second_start}-{second_end}) | {lines} 行 | {severity} | {refactor} |\n"
    
    # 添加分析总结
    md_content += f"""
## 分析总结

### 重复代码类型分布

"""
    
    # 分类统计
    test_dups = []
    vo_dups = []
    entity_dups = []
    other_dups = []
    
    for dup in duplicates:
        # 处理 dict 类型的 firstFile
        first_file_obj = dup.get('firstFile', {})
        second_file_obj = dup.get('secondFile', {})
        
        first_file = first_file_obj.get('name', '') if isinstance(first_file_obj, dict) else str(first_file_obj)
        second_file = second_file_obj.get('name', '') if isinstance(second_file_obj, dict) else str(second_file_obj)
        
        first_file = first_file.lower()
        second_file = second_file.lower()
        
        if 'test' in first_file or 'test' in second_file:
            test_dups.append(dup)
        elif 'vo' in first_file or 'vo' in second_file:
            vo_dups.append(dup)
        elif 'entity' in first_file or 'entity' in second_file:
            entity_dups.append(dup)
        else:
            other_dups.append(dup)
    
    md_content += f"""| 类型 | 数量 | 占比 |
|------|------|------|
| 测试类重复 | {len(test_dups)} 个 | {len(test_dups)*100/len(duplicates):.1f}% |
| VO类重复 | {len(vo_dups)} 个 | {len(vo_dups)*100/len(duplicates):.1f}% |
| Entity类重复 | {len(entity_dups)} 个 | {len(entity_dups)*100/len(duplicates):.1f}% |
| 其他类重复 | {len(other_dups)} 个 | {len(other_dups)*100/len(duplicates):.1f}% |

### 重构建议

1. **测试类重复** ({len(test_dups)} 个): 测试代码中有大量重复的验证逻辑，这是测试框架的常见模式。暂不重构，保持观察。

2. **VO类重复** ({len(vo_dups)} 个): 图像/数据传输相关的VO类有大量相同字段，建议可提取公共基类，使用继承或组合。

3. **Entity类重复** ({len(entity_dups)} 个): Entity和对应的ExportVO有重复字段定义，建议使用MapStruct等映射工具自动生成。

4. **其他类重复** ({len(other_dups)} 个): 建议根据具体业务逻辑评估是否需要重构。

### 后续行动

1. 优先处理 Top 10 严重重复项
2. 建议使用工具类提取通用逻辑
3. 重构后建议运行单元测试确保功能正常
4. 可使用 Excel 报告查看完整重复列表（运行 `python scripts/generate_excel.py` 生成）

---

*本报告由 java-duplicate-analyzer skill 自动生成*
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    # 保存文件
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"Markdown report generated: {output_path}")
        return True
    except Exception as e:
        print(f"Error saving Markdown file: {e}")
        return False


def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_report.py <jscpd-report.json> <output-markdown.md>")
        print("Example: python generate_report.py .jscpd-report/jscpd-report.json ./duplicate-report.md")
        sys.exit(1)
    
    json_path = sys.argv[1]
    output_path = sys.argv[2]
    
    success = generate_markdown_report(json_path, output_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()