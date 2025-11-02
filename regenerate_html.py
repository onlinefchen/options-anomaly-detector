#!/usr/bin/env python3
"""
重新生成所有HTML报告（从现有JSON数据）
"""
import os
import sys
import json
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from report_generator import HTMLReportGenerator
from archive_index_generator import get_archived_reports, generate_archive_index

load_dotenv()


def regenerate_html_from_json(json_file: str):
    """
    从JSON文件重新生成HTML

    Args:
        json_file: JSON文件路径
    """
    print(f'Processing {json_file}...')

    try:
        # Load JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            historical_data = json.load(f)

        date = historical_data.get('date')
        data = historical_data.get('data', [])
        anomalies = historical_data.get('anomalies', [])
        summary = historical_data.get('summary', {})
        metadata = historical_data.get('metadata', {})

        # Generate HTML
        html_file = json_file.replace('.json', '.html')
        reporter = HTMLReportGenerator()
        reporter.generate(
            data=data,
            anomalies=anomalies,
            summary=summary,
            metadata=metadata,
            output_file=html_file
        )

        print(f'  ✓ Generated {html_file}')
        return True

    except Exception as e:
        print(f'  ✗ Error: {e}')
        return False


def main():
    """Main execution"""
    print("=" * 70)
    print("重新生成HTML报告（从现有JSON数据）")
    print("=" * 70)
    print()

    output_dir = 'output'

    # Find all JSON files
    json_files = []
    for filename in os.listdir(output_dir):
        if filename.endswith('.json') and len(filename) == 15:  # YYYY-MM-DD.json
            json_files.append(os.path.join(output_dir, filename))

    json_files.sort()

    print(f"找到 {len(json_files)} 个JSON文件")
    print()

    # Regenerate HTML for each JSON
    success_count = 0
    for json_file in json_files:
        if regenerate_html_from_json(json_file):
            success_count += 1

    print()
    print("=" * 70)
    print(f"完成！成功生成 {success_count}/{len(json_files)} 个HTML文件")
    print("=" * 70)
    print()

    # Regenerate archive index
    print("📚 重新生成归档索引...")
    reports = get_archived_reports(output_dir)
    generate_archive_index(reports, os.path.join(output_dir, 'archive.html'))
    print(f"✓ 归档索引更新完成 ({len(reports)} 个报告)")
    print()

    # Copy latest report to index.html
    if json_files:
        latest_date = max([f.split('/')[-1].replace('.json', '') for f in json_files])
        latest_html = os.path.join(output_dir, f'{latest_date}.html')
        index_html = os.path.join(output_dir, 'index.html')

        if os.path.exists(latest_html):
            import shutil
            shutil.copy2(latest_html, index_html)
            print(f"✓ 复制最新报告到 index.html ({latest_date})")

    print()
    print("完成！")


if __name__ == '__main__':
    main()
