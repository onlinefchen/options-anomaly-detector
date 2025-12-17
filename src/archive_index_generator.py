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
    Scan output directory for archived reports and include all dates from earliest report to today.
    Excludes 'today' unless a report exists.

    Args:
        output_dir: Directory containing reports

    Returns:
        List of report info dicts sorted by date (newest first)
    """
    existing_reports = {}

    # Import trading calendar to check trading days
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from trading_calendar import is_trading_day

    # 1. Scan for existing reports
    if os.path.exists(output_dir):
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

                    # Use date from JSON if available, otherwise use filename date
                    report_date = data.get('date', date_str)
                    
                    existing_reports[report_date] = {
                        'date': report_date,
                        'tickers_count': data.get('tickers_count', 0),
                        'anomalies_count': data.get('anomalies_count', 0),
                        'html_file': f'{date_str}.html',
                        'json_file': f'{date_str}.json',
                        'has_html': os.path.exists(html_path),
                        'exists': True
                    }
                except Exception as e:
                    print(f"Warning: Failed to read {json_path}: {e}")
                    continue

    # 2. Determine date range
    if not existing_reports:
        return []

    earliest_date = min(existing_reports.keys())
    
    # Determine end date: Yesterday by default, or Today if report exists
    from datetime import timedelta
    today_dt = datetime.now()
    today_str = today_dt.strftime('%Y-%m-%d')
    yesterday_dt = today_dt - timedelta(days=1)
    
    if today_str in existing_reports:
        end_dt = today_dt
    else:
        end_dt = yesterday_dt

    start_dt = datetime.strptime(earliest_date, '%Y-%m-%d')
    
    # If start > end (e.g. only report is today and we skipped it? logic covers it), handle safety
    if start_dt > end_dt:
        end_dt = start_dt

    all_reports = []
    
    # Iterate through all dates
    import pandas as pd
    date_range = pd.date_range(start=start_dt, end=end_dt)
    
    for dt in date_range:
        current_date = dt.strftime('%Y-%m-%d')
        is_trade = is_trading_day(current_date)
        weekday_str = dt.strftime('%A')
        
        if current_date in existing_reports:
            # Report exists
            report = existing_reports[current_date]
            report['is_trading_day'] = is_trade
            report['weekday'] = weekday_str
            report['status'] = 'EXISTS'
            all_reports.append(report)
        else:
            # Report missing
            all_reports.append({
                'date': current_date,
                'tickers_count': 0,
                'anomalies_count': 0,
                'html_file': None,
                'json_file': None,
                'has_html': False,
                'exists': False,
                'is_trading_day': is_trade,
                'weekday': weekday_str,
                'status': 'MISSING'
            })

    # Sort by date (newest first)
    all_reports.sort(key=lambda x: x['date'], reverse=True)

    # 3. Refine Status (Identify "Waiting Data")
    # Find the most recent trading day in the list
    most_recent_trading_day = None
    for report in all_reports:
        if report['is_trading_day']:
            most_recent_trading_day = report['date']
            break
    
    # Mark "Waiting Data"
    if most_recent_trading_day:
        for report in all_reports:
            if report['date'] == most_recent_trading_day and not report['exists']:
                report['status'] = 'WAITING'
                break # Only the very latest one can be waiting

    return all_reports


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
            white-space: nowrap;
        }}
        
        .weekday {{
            color: #86868b;
            font-weight: normal;
            font-size: 0.9em;
            margin-left: 5px;
        }}

        .badge {{
            display: inline-block;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 500;
            border-radius: 2px;
        }}

        .badge-trading {{
            background: #e3f2fd;
            color: #0d47a1;
            border: 1px solid #bbdefb;
        }}

        .badge-non-trading {{
            background: #f5f5f7;
            color: #86868b;
            border: 1px solid #d2d2d7;
        }}
        
        .badge-missing {{
            background: #ffebee;
            color: #c62828;
            border: 1px solid #ffcdd2;
        }}
        
        .badge-waiting {{
            background: #fff3e0;
            color: #ef6c00;
            border: 1px solid #ffe0b2;
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
            <div class="section-title">Historical Timeline</div>
            <div class="summary">
                Timeline from {earliest_date} to {latest_date}
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
        earliest = "N/A"
        latest = "N/A"
    else:
        earliest = reports[-1]['date']
        latest = reports[0]['date']
        rows = []
        for report in reports:
            # Determine status and actions
            actions_cell = ''
            stats_cell = ''
            badge_html = ''
            
            if report['exists']:
                # Data exists
                badge_html = '<span class="badge badge-trading">Trading Day</span>'
                stats_cell = f'''
                    <span class="stats">{report['tickers_count']} Tickers</span>
                    <span class="stats">{report['anomalies_count']} Anomalies</span>
                '''
                
                html_link = f'<a href="{report["html_file"]}" class="link">View Report</a>' if report['has_html'] else ''
                json_link = f'<a href="{report["json_file"]}" class="link">Download Data</a>'
                actions_cell = f'{html_link} {json_link}'
                
            else:
                # No data
                status = report.get('status', 'MISSING')
                
                if not report['is_trading_day']:
                     badge_html = '<span class="badge badge-non-trading">Non-Trading</span>'
                     stats_cell = '<span class="stats">Market Closed</span>'
                     actions_cell = '<span style="color:#d2d2d7;">-</span>'
                elif status == 'WAITING':
                     badge_html = '<span class="badge badge-waiting">Waiting Data</span>'
                     stats_cell = '<span class="stats">Pending upload...</span>'
                     actions_cell = '<span style="color:#ef6c00; font-size:11px;">Check back later</span>'
                else:
                     badge_html = '<span class="badge badge-missing">Missing Data</span>'
                     stats_cell = '<span class="stats">-</span>'
                     actions_cell = '<span style="color:#d2d2d7;">-</span>'

            # Add weekday to date
            date_display = f"{report['date']} <span class='weekday'>{report['weekday']}</span>"

            rows.append(f'''
                <tr>
                    <td class="date-cell">{date_display}</td>
                    <td>{badge_html}</td>
                    <td>{stats_cell}</td>
                    <td>{actions_cell}</td>
                </tr>
            ''')

        table_html = f'''
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Status</th>
                        <th>Info</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        '''

    html = template.format(
        earliest_date=earliest,
        latest_date=latest,
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
