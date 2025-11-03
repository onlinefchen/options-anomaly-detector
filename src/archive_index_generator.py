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

    # Import trading calendar to check trading days
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from trading_calendar import is_trading_day

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

                # Check if this date is a trading day
                is_trade_day = is_trading_day(date_str)

                reports.append({
                    'date': date_str,
                    'tickers_count': data.get('tickers_count', 0),
                    'anomalies_count': data.get('anomalies_count', 0),
                    'html_file': f'{date_str}.html',
                    'json_file': f'{date_str}.json',
                    'has_html': os.path.exists(html_path),
                    'is_trading_day': is_trade_day
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
    <title>Options Analysis Archive</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: "Courier New", Courier, monospace;
            background: #ffffff;
            padding: 40px 20px;
            color: #1d1d1f;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}

        .header {{
            text-align: center;
            margin-bottom: 50px;
            padding-bottom: 30px;
            border-bottom: 1px solid #d2d2d7;
        }}

        .header h1 {{
            font-size: 2em;
            margin-bottom: 10px;
            color: #1d1d1f;
            font-weight: 600;
            letter-spacing: -0.5px;
        }}

        .header p {{
            color: #86868b;
            font-size: 0.9em;
        }}

        .nav {{
            text-align: center;
            margin-bottom: 40px;
        }}

        .nav a {{
            display: inline-block;
            padding: 8px 20px;
            margin: 0 8px;
            color: #1d1d1f;
            text-decoration: none;
            border: 1px solid #d2d2d7;
            border-radius: 2px;
            font-size: 13px;
            transition: all 0.2s;
        }}

        .nav a:hover {{
            background: #f5f5f7;
            border-color: #86868b;
        }}

        .section {{
            margin-bottom: 40px;
        }}

        .section-title {{
            font-size: 1.2em;
            margin-bottom: 20px;
            color: #1d1d1f;
            font-weight: 600;
        }}

        .summary {{
            color: #86868b;
            font-size: 0.9em;
            margin-bottom: 30px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}

        table th {{
            background: #f5f5f7;
            color: #1d1d1f;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 1px solid #d2d2d7;
        }}

        table td {{
            padding: 12px;
            border-bottom: 1px solid #f5f5f7;
        }}

        table tr:hover {{
            background: #fafafa;
        }}

        .date-cell {{
            font-family: "Courier New", Courier, monospace;
            font-weight: 600;
            color: #1d1d1f;
        }}

        .badge {{
            display: inline-block;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 500;
            border-radius: 2px;
        }}

        .badge-trading {{
            background: #f5f5f7;
            color: #1d1d1f;
            border: 1px solid #d2d2d7;
        }}

        .badge-non-trading {{
            background: #ffffff;
            color: #86868b;
            border: 1px solid #d2d2d7;
        }}

        .stats {{
            display: inline-block;
            color: #86868b;
            font-size: 12px;
            margin-right: 15px;
        }}

        .link {{
            color: #06c;
            text-decoration: none;
            font-size: 12px;
            margin-right: 12px;
        }}

        .link:hover {{
            text-decoration: underline;
        }}

        .footer {{
            text-align: center;
            color: #86868b;
            font-size: 11px;
            margin-top: 60px;
            padding-top: 20px;
            border-top: 1px solid #d2d2d7;
        }}

        .footer p {{
            margin: 5px 0;
        }}

        @media (max-width: 768px) {{
            body {{
                padding: 20px 15px;
            }}
            .header h1 {{
                font-size: 1.5em;
            }}
            .nav a {{
                display: block;
                margin: 8px 0;
            }}
            table {{
                font-size: 11px;
            }}
            table th, table td {{
                padding: 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Options Analysis Archive</h1>
            <p>Historical Reports & Data Archive</p>
        </div>

        <div class="nav">
            <a href="index.html">Latest Report</a>
            <a href="archive.html">Archive</a>
        </div>

        <div class="section">
            <div class="section-title">Historical Reports</div>
            <div class="summary">
                Total {total_reports} reports | Updated daily
            </div>

            {report_table}
        </div>

        <div class="footer">
            <p>Options Anomaly Detection System | Data Source: Polygon.io</p>
            <p>For informational purposes only. Not investment advice.</p>
        </div>
    </div>
</body>
</html>'''

    # Generate table rows
    if not reports:
        table_html = '<p style="text-align:center; padding:40px; color:#86868b;">No historical reports</p>'
    else:
        rows = []
        for report in reports:
            html_link = f'<a href="{report["html_file"]}" class="link">View Report</a>' if report['has_html'] else '<span style="color:#d2d2d7;">-</span>'
            json_link = f'<a href="{report["json_file"]}" class="link">Download Data</a>'

            # Trading day badge
            if report['is_trading_day']:
                trading_badge = '<span class="badge badge-trading">Trading Day</span>'
            else:
                trading_badge = '<span class="badge badge-non-trading">Non-Trading</span>'

            rows.append(f'''
                <tr>
                    <td class="date-cell">{report['date']}</td>
                    <td>{trading_badge}</td>
                    <td>
                        <span class="stats">{report['tickers_count']} Tickers</span>
                        <span class="stats">{report['anomalies_count']} Anomalies</span>
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
                        <th>Date</th>
                        <th>Trading Day</th>
                        <th>Statistics</th>
                        <th>Actions</th>
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
