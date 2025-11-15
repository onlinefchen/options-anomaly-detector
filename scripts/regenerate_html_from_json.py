#!/usr/bin/env python3
"""
从现有的 JSON 文件重新生成 HTML 报告
用于修复缺失的 HTML 文件
"""
import os
import sys
import json
import argparse

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from report_generator import HTMLReportGenerator


def regenerate_html(json_file: str, output_dir: str = 'output'):
    """
    从 JSON 文件重新生成 HTML 报告

    Args:
        json_file: JSON 文件路径
        output_dir: 输出目录
    """
    if not os.path.exists(json_file):
        print(f'❌ JSON file not found: {json_file}')
        return False

    # 提取日期
    basename = os.path.basename(json_file)
    if not basename.endswith('.json'):
        print(f'❌ Invalid file: {json_file}')
        return False

    date = basename[:-5]  # Remove .json
    print(f'\n{"="*60}')
    print(f'📂 Processing: {date}')
    print(f'{"="*60}')

    # 读取 JSON 数据
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            historical_data = json.load(f)
    except Exception as e:
        print(f'❌ Failed to read JSON: {e}')
        return False

    # 提取数据
    data = historical_data.get('data', [])
    anomalies = historical_data.get('anomalies', [])
    summary = historical_data.get('summary', {})
    metadata = historical_data.get('metadata', {})

    print(f'✓ Loaded data: {len(data)} tickers, {summary.get("total", 0)} anomalies')

    # 生成 HTML
    html_file = os.path.join(output_dir, f'{date}.html')
    print(f'⏳ Generating HTML: {html_file}')

    try:
        reporter = HTMLReportGenerator()
        reporter.generate(
            data=data,
            anomalies=anomalies,
            summary=summary,
            metadata=metadata,
            output_file=html_file
        )

        file_size = os.path.getsize(html_file) / 1024
        print(f'✅ HTML generated: {html_file} ({file_size:.1f} KB)')
        return True
    except Exception as e:
        print(f'❌ Failed to generate HTML: {e}')
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description='从现有的 JSON 文件重新生成 HTML 报告'
    )
    parser.add_argument(
        '--date',
        help='指定日期 (YYYY-MM-DD)，将从 output/YYYY-MM-DD.json 生成 HTML'
    )
    parser.add_argument(
        '--all-missing',
        action='store_true',
        help='自动查找所有缺少 HTML 的 JSON 文件并生成'
    )
    parser.add_argument(
        '--output',
        default='output',
        help='输出目录 (默认: output)'
    )

    args = parser.parse_args()

    if not args.date and not args.all_missing:
        parser.error('请指定 --date 或 --all-missing')

    success_count = 0
    total_count = 0

    if args.date:
        # 处理单个日期
        json_file = os.path.join(args.output, f'{args.date}.json')
        total_count = 1
        if regenerate_html(json_file, args.output):
            success_count = 1

    elif args.all_missing:
        # 查找所有缺少 HTML 的 JSON 文件
        if not os.path.exists(args.output):
            print(f'❌ Output directory not found: {args.output}')
            sys.exit(1)

        print('🔍 Searching for JSON files without corresponding HTML...\n')

        json_files = [
            f for f in os.listdir(args.output)
            if f.endswith('.json') and len(f) == 15  # YYYY-MM-DD.json
        ]

        missing = []
        for json_file in json_files:
            date = json_file[:-5]
            html_file = os.path.join(args.output, f'{date}.html')
            if not os.path.exists(html_file):
                missing.append(date)

        if not missing:
            print('✓ No missing HTML files found!')
            return

        print(f'Found {len(missing)} JSON file(s) without HTML:')
        for date in missing:
            print(f'  • {date}')
        print()

        total_count = len(missing)
        for date in missing:
            json_file = os.path.join(args.output, f'{date}.json')
            if regenerate_html(json_file, args.output):
                success_count += 1

    print(f'\n{"="*60}')
    print(f'✓ Completed: {success_count}/{total_count} HTML files generated')
    print(f'{"="*60}\n')


if __name__ == '__main__':
    main()
