#!/usr/bin/env python3
"""
Archive Index Generator
Creates an index page listing all historical reports
"""
import os
import json
from datetime import datetime
from typing import List, Dict


def get_archived_reports(output_dir: str = 'output') -> List[Dict]:
    """
    Scan output directory for archived reports

    Args:
        output_dir: Directory containing reports

    Returns:
        List of report info dicts sorted by date (newest first)
    """
    reports = []

    if not os.path.exists(output_dir):
        return reports

    for filename in os.listdir(output_dir):
        # Look for dated JSON files (YYYY-MM-DD.json)
        if filename.endswith('.json') and len(filename) == 15:  # YYYY-MM-DD.json
            date_str = filename[:-5]
            json_path = os.path.join(output_dir, filename)
            html_path = os.path.join(output_dir, f'{date_str}.html')

            try:
                # Load JSON to get metadata
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                reports.append({
                    'date': date_str,
                    'tickers_count': data.get('tickers_count', 0),
                    'anomalies_count': data.get('anomalies_count', 0),
                    'html_file': f'{date_str}.html',
                    'json_file': f'{date_str}.json',
                    'has_html': os.path.exists(html_path)
                })
            except Exception as e:
                print(f"Warning: Failed to read {json_path}: {e}")
                continue

    # Sort by date (newest first)
    reports.sort(key=lambda x: x['date'], reverse=True)
    return reports


def generate_archive_index(reports: List[Dict], output_file: str = 'output/archive.html'):
    """
    Generate HTML index page for archived reports

    Args:
        reports: List of report info dicts
        output_file: Output HTML file path
    """
    template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>期权异常分析 - 历史报告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        .header {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .nav {{
            background: white;
            padding: 15px 30px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            text-align: center;
        }}

        .nav a {{
            display: inline-block;
            padding: 10px 25px;
            margin: 0 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 25px;
            font-weight: 600;
            transition: transform 0.2s;
        }}

        .nav a:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }}

        .section {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}

        .section h2 {{
            margin-bottom: 20px;
            color: #333;
            border-left: 5px solid #667eea;
            padding-left: 15px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}

        table th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}

        table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}

        table tr:hover {{
            background: #f8f9fa;
        }}

        .btn {{
            display: inline-block;
            padding: 8px 16px;
            margin: 0 5px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 0.9em;
            transition: background 0.2s;
        }}

        .btn:hover {{
            background: #5568d3;
        }}

        .btn-secondary {{
            background: #6c757d;
        }}

        .btn-secondary:hover {{
            background: #5a6268;
        }}

        .stats {{
            display: inline-block;
            padding: 4px 10px;
            background: #f0f0f0;
            border-radius: 4px;
            font-size: 0.9em;
            margin: 0 5px;
        }}

        .footer {{
            text-align: center;
            color: white;
            margin-top: 30px;
            padding: 20px;
        }}

        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 1.8em;
            }}
            .nav a {{
                display: block;
                margin: 10px 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 期权异常分析 - 历史报告</h1>
            <p class="date">数据归档与历史查询</p>
        </div>

        <div class="nav">
            <a href="index.html">📊 最新报告</a>
            <a href="archive.html">📚 历史报告</a>
        </div>

        <div class="section">
            <h2>📅 历史报告列表</h2>
            <p style="color: #666; margin-bottom: 20px;">
                共 <strong>{total_reports}</strong> 份历史报告，每日自动更新并归档
            </p>

            {report_table}
        </div>

        <div class="footer">
            <p>期权异常检测系统 | 数据来源: Polygon.io</p>
            <p>⚠️ 本报告仅供参考，不构成投资建议</p>
        </div>
    </div>
</body>
</html>'''

    # Generate table rows
    if not reports:
        table_html = '<p style="text-align:center; padding:40px;">暂无历史报告</p>'
    else:
        rows = []
        for report in reports:
            html_link = f'<a href="{report["html_file"]}" class="btn">查看报告</a>' if report['has_html'] else '-'
            json_link = f'<a href="{report["json_file"]}" class="btn btn-secondary">下载数据</a>'

            rows.append(f'''
                <tr>
                    <td><strong>{report['date']}</strong></td>
                    <td>
                        <span class="stats">📊 {report['tickers_count']} 只股票</span>
                        <span class="stats">🚨 {report['anomalies_count']} 个异常</span>
                    </td>
                    <td>
                        {html_link}
                        {json_link}
                    </td>
                </tr>
            ''')

        table_html = f'''
            <table>
                <thead>
                    <tr>
                        <th>日期</th>
                        <th>统计</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        '''

    html = template.format(
        total_reports=len(reports),
        report_table=table_html
    )

    # Write to file
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✓ Archive index generated: {output_file}")


if __name__ == '__main__':
    reports = get_archived_reports()
    generate_archive_index(reports)
    print(f"Found {len(reports)} historical reports")
