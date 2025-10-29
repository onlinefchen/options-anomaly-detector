#!/usr/bin/env python3
"""
Report Generator Module
Generates HTML reports with charts and tables
"""
from datetime import datetime
from typing import List, Dict
import json


class HTMLReportGenerator:
    """Generate HTML reports for options anomaly analysis"""

    def __init__(self):
        """Initialize the report generator"""
        self.template = self._get_template()

    def generate(
        self,
        data: List[Dict],
        anomalies: List[Dict],
        summary: Dict,
        output_file: str = "output/anomaly_report.html"
    ):
        """
        Generate HTML report

        Args:
            data: Aggregated options data
            anomalies: Detected anomalies
            summary: Anomaly summary statistics
            output_file: Output file path
        """
        import os
        import shutil
        # Sort data by volume
        sorted_data = sorted(data, key=lambda x: x['total_volume'], reverse=True)[:30]

        # Prepare data for charts
        tickers = [d['ticker'] for d in sorted_data]
        volumes = [d['total_volume'] for d in sorted_data]
        pc_volume_ratios = [d['pc_volume_ratio'] for d in sorted_data]
        pc_oi_ratios = [d['pc_oi_ratio'] for d in sorted_data]
        open_interests = [d['total_oi'] for d in sorted_data]

        # Sort anomalies by severity
        severity_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        sorted_anomalies = sorted(
            anomalies,
            key=lambda x: severity_order.get(x['severity'], 0),
            reverse=True
        )[:20]  # Top 20 anomalies

        # Generate HTML
        html = self.template.format(
            report_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S ET'),
            total_tickers=len(data),
            total_anomalies=summary.get('total', 0),
            high_severity=summary.get('by_severity', {}).get('HIGH', 0),
            medium_severity=summary.get('by_severity', {}).get('MEDIUM', 0),
            low_severity=summary.get('by_severity', {}).get('LOW', 0),
            tickers_json=json.dumps(tickers),
            volumes_json=json.dumps(volumes),
            pc_volume_ratios_json=json.dumps(pc_volume_ratios),
            pc_oi_ratios_json=json.dumps(pc_oi_ratios),
            open_interests_json=json.dumps(open_interests),
            volume_table_rows=self._generate_table_rows(sorted_data),
            anomaly_rows=self._generate_anomaly_rows(sorted_anomalies)
        )

        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"\n✓ HTML report generated: {output_file}")

        # Also create index.html for GitHub Pages
        output_dir = os.path.dirname(output_file)
        index_file = os.path.join(output_dir, 'index.html')
        shutil.copy2(output_file, index_file)
        print(f"✓ GitHub Pages index created: {index_file}")

    def _generate_table_rows(self, data: List[Dict]) -> str:
        """Generate table rows HTML for volume rankings"""
        rows = []
        for idx, item in enumerate(data, 1):
            rows.append(f"""
                <tr>
                    <td>{idx}</td>
                    <td><strong>{item['ticker']}</strong></td>
                    <td>{item['total_volume']:,}</td>
                    <td>{item['pc_volume_ratio']:.2f}</td>
                    <td>{item['total_oi']:,}</td>
                    <td>{item['pc_oi_ratio']:.2f}</td>
                    <td>{item['put_volume']:,}</td>
                    <td>{item['call_volume']:,}</td>
                </tr>
            """)
        return ''.join(rows)

    def _generate_anomaly_rows(self, anomalies: List[Dict]) -> str:
        """Generate anomaly rows HTML"""
        if not anomalies:
            return '<tr><td colspan="4" style="text-align:center;">No anomalies detected</td></tr>'

        severity_colors = {
            'HIGH': '#dc3545',
            'MEDIUM': '#ffc107',
            'LOW': '#17a2b8'
        }

        rows = []
        for anomaly in anomalies:
            severity = anomaly['severity']
            color = severity_colors.get(severity, '#6c757d')

            rows.append(f"""
                <tr>
                    <td><strong>{anomaly['ticker']}</strong></td>
                    <td><span class="badge" style="background-color:{color}">{severity}</span></td>
                    <td>{anomaly['type'].replace('_', ' ')}</td>
                    <td>{anomaly['description']}</td>
                </tr>
            """)
        return ''.join(rows)

    def _get_template(self) -> str:
        """Get HTML template"""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Options Anomaly Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
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
            max-width: 1400px;
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

        .header .date {{
            color: #666;
            font-size: 1.1em;
        }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            text-align: center;
        }}

        .stat-card .number {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}

        .stat-card .label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
        }}

        .stat-card.high .number {{ color: #dc3545; }}
        .stat-card.medium .number {{ color: #ffc107; }}
        .stat-card.low .number {{ color: #17a2b8; }}
        .stat-card.total .number {{ color: #667eea; }}

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

        .chart-container {{
            position: relative;
            height: 400px;
            margin: 30px 0;
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

        .badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            color: white;
            font-size: 0.85em;
            font-weight: bold;
        }}

        .footer {{
            text-align: center;
            color: white;
            margin-top: 30px;
            padding: 20px;
        }}

        @media (max-width: 768px) {{
            .stats {{
                grid-template-columns: 1fr;
            }}
            .header h1 {{
                font-size: 1.8em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Options Market Anomaly Report</h1>
            <p class="date">{report_date}</p>
        </div>

        <div class="stats">
            <div class="stat-card total">
                <div class="label">Total Tickers Analyzed</div>
                <div class="number">{total_tickers}</div>
            </div>
            <div class="stat-card total">
                <div class="label">Total Anomalies</div>
                <div class="number">{total_anomalies}</div>
            </div>
            <div class="stat-card high">
                <div class="label">High Severity</div>
                <div class="number">{high_severity}</div>
            </div>
            <div class="stat-card medium">
                <div class="label">Medium Severity</div>
                <div class="number">{medium_severity}</div>
            </div>
            <div class="stat-card low">
                <div class="label">Low Severity</div>
                <div class="number">{low_severity}</div>
            </div>
        </div>

        <div class="section">
            <h2>🚨 Detected Anomalies</h2>
            <table>
                <thead>
                    <tr>
                        <th>Ticker</th>
                        <th>Severity</th>
                        <th>Type</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    {anomaly_rows}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>📈 Top 30 Options Volume Rankings</h2>
            <div class="chart-container">
                <canvas id="volumeChart"></canvas>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Ticker</th>
                        <th>Total Volume</th>
                        <th>P/C Volume Ratio</th>
                        <th>Open Interest</th>
                        <th>P/C OI Ratio</th>
                        <th>Put Volume</th>
                        <th>Call Volume</th>
                    </tr>
                </thead>
                <tbody>
                    {volume_table_rows}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>📊 Put/Call Ratios Analysis</h2>
            <div class="chart-container">
                <canvas id="pcRatioChart"></canvas>
            </div>
        </div>

        <div class="section">
            <h2>💼 Open Interest Distribution</h2>
            <div class="chart-container">
                <canvas id="oiChart"></canvas>
            </div>
        </div>

        <div class="footer">
            <p>Generated by Options Anomaly Detector | Data: Polygon.io</p>
            <p>⚠️ This report is for informational purposes only. Not financial advice.</p>
        </div>
    </div>

    <script>
        // Volume Chart
        const volumeCtx = document.getElementById('volumeChart').getContext('2d');
        new Chart(volumeCtx, {{
            type: 'bar',
            data: {{
                labels: {tickers_json},
                datasets: [{{
                    label: 'Total Volume',
                    data: {volumes_json},
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    title: {{
                        display: true,
                        text: 'Options Trading Volume'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});

        // P/C Ratio Chart
        const pcCtx = document.getElementById('pcRatioChart').getContext('2d');
        new Chart(pcCtx, {{
            type: 'bar',
            data: {{
                labels: {tickers_json},
                datasets: [
                    {{
                        label: 'Volume P/C Ratio',
                        data: {pc_volume_ratios_json},
                        backgroundColor: 'rgba(255, 99, 132, 0.6)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }},
                    {{
                        label: 'OI P/C Ratio',
                        data: {pc_oi_ratios_json},
                        backgroundColor: 'rgba(54, 162, 235, 0.6)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Put/Call Ratios Comparison'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});

        // OI Chart
        const oiCtx = document.getElementById('oiChart').getContext('2d');
        new Chart(oiCtx, {{
            type: 'bar',
            data: {{
                labels: {tickers_json},
                datasets: [{{
                    label: 'Open Interest',
                    data: {open_interests_json},
                    backgroundColor: 'rgba(75, 192, 192, 0.6)',
                    borderColor: 'rgba(75, 192, 192, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Open Interest Distribution'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>'''
