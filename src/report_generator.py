#!/usr/bin/env python3
"""
Report Generator Module
Generates HTML reports with charts and tables
"""
from datetime import datetime
from typing import List, Dict
import json
from utils import get_market_times, format_market_time_html


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
        cp_volume_ratios = [d['cp_volume_ratio'] for d in sorted_data]
        cp_oi_ratios = [d['cp_oi_ratio'] for d in sorted_data]
        open_interests = [d['total_oi'] for d in sorted_data]

        # Sort anomalies by severity
        severity_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        sorted_anomalies = sorted(
            anomalies,
            key=lambda x: severity_order.get(x['severity'], 0),
            reverse=True
        )[:20]  # Top 20 anomalies

        # Get market time information with timezones
        time_info = get_market_times()
        time_display = format_market_time_html(time_info)

        # Generate HTML
        html = self.template.format(
            report_date=time_display,
            total_tickers=len(data),
            total_anomalies=summary.get('total', 0),
            high_severity=summary.get('by_severity', {}).get('HIGH', 0),
            medium_severity=summary.get('by_severity', {}).get('MEDIUM', 0),
            low_severity=summary.get('by_severity', {}).get('LOW', 0),
            tickers_json=json.dumps(tickers),
            volumes_json=json.dumps(volumes),
            cp_volume_ratios_json=json.dumps(cp_volume_ratios),
            cp_oi_ratios_json=json.dumps(cp_oi_ratios),
            open_interests_json=json.dumps(open_interests),
            volume_table_rows=self._generate_table_rows(sorted_data),
            anomaly_rows=self._generate_anomaly_rows(sorted_anomalies),
            # Add complete data for client-side sorting
            table_data_json=json.dumps(sorted_data, ensure_ascii=False)
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

    def _format_contract_short(self, contract: Dict) -> str:
        """
        格式化合约为简短格式: 250131C600

        Args:
            contract: Contract dict with expiry, type, strike

        Returns:
            Formatted string
        """
        try:
            expiry = contract.get('expiry', '')
            if expiry:
                # 从 2025-01-31 提取 250131
                expiry = expiry.replace('-', '')[-6:]
            contract_type = contract.get('type', '')[0].upper() if contract.get('type') else 'X'
            strike = int(contract.get('strike', 0))
            return f"{expiry}{contract_type}{strike}"
        except:
            return "N/A"

    def _generate_table_rows(self, data: List[Dict]) -> str:
        """Generate table rows HTML for volume rankings"""
        rows = []
        for idx, item in enumerate(data, 1):
            # 格式化 Top 3 合约
            top3_html = ''
            for i, contract in enumerate(item.get('top_3_contracts', [])[:3], 1):
                contract_short = self._format_contract_short(contract)
                oi_k = contract.get('oi', 0) / 1000
                pct = contract.get('percentage', 0)
                top3_html += f"<div class='contract-item'>① {contract_short} <span class='oi-badge'>{oi_k:.0f}K ({pct:.1f}%)</span></div>"

            if not top3_html:
                top3_html = '<small>N/A</small>'

            # 格式化价格区间
            strike_info = item.get('strike_concentration', {})
            strike_range = strike_info.get('range', 'N/A')
            strike_pct = strike_info.get('percentage', 0)
            dominant = strike_info.get('dominant_strike')

            strike_html = f"""
                <div><strong>{strike_range}</strong> <span class='pct'>({strike_pct:.1f}%)</span></div>
                <div><small>核心: {dominant if dominant else 'N/A'}</small></div>
            """

            # 格式化历史活跃度
            history = item.get('history', {})
            appearances = history.get('appearances', 0)
            icon = history.get('icon', '🆕')
            rank_change = history.get('rank_change')
            avg_rank = history.get('avg_rank')

            # 排名变化符号
            if rank_change is None or rank_change == 0:
                rank_symbol = '↔️'
            elif rank_change > 0:
                rank_symbol = f'↑{rank_change}'
            else:
                rank_symbol = f'↓{abs(rank_change)}'

            history_html = f"""
                <div><strong>{appearances}/10 {icon}</strong> {rank_symbol}</div>
                <div><small>平均排名: {avg_rank if avg_rank else 'N/A'}</small></div>
            """

            rows.append(f"""
                <tr>
                    <td>{idx}</td>
                    <td><strong>{item['ticker']}</strong></td>
                    <td>{item['total_volume']:,}</td>
                    <td>{item['cp_volume_ratio']:.2f}</td>
                    <td>{item['total_oi']:,}</td>
                    <td>{item['cp_oi_ratio']:.2f}</td>
                    <td class="compact-cell">{top3_html}</td>
                    <td class="compact-cell">{strike_html}</td>
                    <td class="compact-cell">{history_html}</td>
                </tr>
            """)
        return ''.join(rows)

    def _generate_anomaly_rows(self, anomalies: List[Dict]) -> str:
        """Generate anomaly rows HTML"""
        if not anomalies:
            return '<tr><td colspan="4" style="text-align:center;">未检测到异常</td></tr>'

        severity_colors = {
            'HIGH': '#dc3545',
            'MEDIUM': '#ffc107',
            'LOW': '#17a2b8'
        }

        severity_names = {
            'HIGH': '高',
            'MEDIUM': '中',
            'LOW': '低'
        }

        rows = []
        for anomaly in anomalies:
            severity = anomaly['severity']
            color = severity_colors.get(severity, '#6c757d')
            severity_cn = severity_names.get(severity, severity)

            rows.append(f"""
                <tr>
                    <td><strong>{anomaly['ticker']}</strong></td>
                    <td><span class="badge" style="background-color:{color}">{severity_cn}</span></td>
                    <td>{anomaly['type'].replace('_', ' ')}</td>
                    <td>{anomaly['description']}</td>
                </tr>
            """)
        return ''.join(rows)

    def _get_template(self) -> str:
        """Get HTML template"""
        return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>期权市场异常分析报告</title>
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

        table th.sortable {{
            cursor: pointer;
            user-select: none;
            position: relative;
            transition: background 0.2s;
        }}

        table th.sortable:hover {{
            background: linear-gradient(135deg, #7688f0 0%, #8655b0 100%);
        }}

        table th.sortable.sorted-asc .sort-icon {{
            color: #ffd700;
        }}

        table th.sortable.sorted-asc .sort-icon::after {{
            content: ' ▲';
        }}

        table th.sortable.sorted-desc .sort-icon {{
            color: #ffd700;
        }}

        table th.sortable.sorted-desc .sort-icon::after {{
            content: ' ▼';
        }}

        .sort-icon {{
            font-size: 0.8em;
            opacity: 0.6;
            margin-left: 5px;
        }}

        table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}

        table tr:hover {{
            background: #f8f9fa;
        }}

        /* 紧凑单元格样式 */
        .compact-cell {{
            font-size: 0.85em;
            line-height: 1.6;
            padding: 10px !important;
        }}

        .compact-cell div {{
            margin: 3px 0;
        }}

        /* 合约项样式 */
        .contract-item {{
            white-space: nowrap;
        }}

        /* OI徽章样式 */
        .oi-badge {{
            background: #e3f2fd;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
            color: #1976d2;
            white-space: nowrap;
        }}

        /* 百分比样式 */
        .pct {{
            color: #666;
            font-size: 0.9em;
        }}

        /* 小号文字 */
        .compact-cell small {{
            color: #888;
            font-size: 0.85em;
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
            <h1>📊 期权市场异常分析报告</h1>
            <p class="date">{report_date}</p>
        </div>

        <div class="nav">
            <a href="index.html">📊 最新报告</a>
            <a href="archive.html">📚 历史报告</a>
        </div>

        <div class="stats">
            <div class="stat-card total">
                <div class="label">分析股票数</div>
                <div class="number">{total_tickers}</div>
            </div>
            <div class="stat-card total">
                <div class="label">异常总数</div>
                <div class="number">{total_anomalies}</div>
            </div>
            <div class="stat-card high">
                <div class="label">高严重</div>
                <div class="number">{high_severity}</div>
            </div>
            <div class="stat-card medium">
                <div class="label">中严重</div>
                <div class="number">{medium_severity}</div>
            </div>
            <div class="stat-card low">
                <div class="label">低严重</div>
                <div class="number">{low_severity}</div>
            </div>
        </div>

        <div class="section">
            <h2>🚨 检测到的异常</h2>
            <table>
                <thead>
                    <tr>
                        <th>股票代码</th>
                        <th>严重程度</th>
                        <th>类型</th>
                        <th>描述</th>
                    </tr>
                </thead>
                <tbody>
                    {anomaly_rows}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>📈 期权成交量Top 30排行</h2>
            <div class="chart-container">
                <canvas id="volumeChart"></canvas>
            </div>
            <table id="volumeTable">
                <thead>
                    <tr>
                        <th>排名</th>
                        <th class="sortable" data-column="ticker" data-type="string">股票代码 <span class="sort-icon">⇅</span></th>
                        <th class="sortable" data-column="total_volume" data-type="number">总成交量 <span class="sort-icon">⇅</span></th>
                        <th class="sortable" data-column="cp_volume_ratio" data-type="number">C/P 成交比 <span class="sort-icon">⇅</span></th>
                        <th class="sortable" data-column="total_oi" data-type="number">持仓量 <span class="sort-icon">⇅</span></th>
                        <th class="sortable" data-column="cp_oi_ratio" data-type="number">C/P 持仓比 <span class="sort-icon">⇅</span></th>
                        <th>Top 3 活跃合约</th>
                        <th>主力价格区间</th>
                        <th>10日活跃度</th>
                    </tr>
                </thead>
                <tbody id="volumeTableBody">
                    {volume_table_rows}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>📊 Call/Put 比例分析</h2>
            <div class="chart-container">
                <canvas id="cpRatioChart"></canvas>
            </div>
        </div>

        <div class="section">
            <h2>💼 持仓量分布</h2>
            <div class="chart-container">
                <canvas id="oiChart"></canvas>
            </div>
        </div>

        <div class="footer">
            <p>期权异常检测系统 | 数据来源: Polygon.io</p>
            <p>⚠️ 本报告仅供参考，不构成投资建议</p>
        </div>
    </div>

    <script>
        // Store table data for sorting
        const tableData = {table_data_json};
        let currentSortColumn = 'total_volume';
        let currentSortOrder = 'desc';

        // Table sorting function
        function sortTable(column, type) {{
            // Toggle sort order if clicking same column
            if (currentSortColumn === column) {{
                currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
            }} else {{
                currentSortColumn = column;
                currentSortOrder = 'desc'; // Default to descending
            }}

            // Sort data
            const sortedData = [...tableData].sort((a, b) => {{
                let valA = a[column];
                let valB = b[column];

                // Handle string comparison
                if (type === 'string') {{
                    valA = String(valA).toLowerCase();
                    valB = String(valB).toLowerCase();
                    return currentSortOrder === 'asc'
                        ? valA.localeCompare(valB)
                        : valB.localeCompare(valA);
                }}

                // Handle number comparison
                valA = Number(valA) || 0;
                valB = Number(valB) || 0;
                return currentSortOrder === 'asc' ? valA - valB : valB - valA;
            }});

            // Update table
            renderTable(sortedData);

            // Update sort indicators
            document.querySelectorAll('th.sortable').forEach(th => {{
                th.classList.remove('sorted-asc', 'sorted-desc');
            }});
            const activeHeader = document.querySelector(`th[data-column="${{column}}"]`);
            if (activeHeader) {{
                activeHeader.classList.add(`sorted-${{currentSortOrder}}`);
            }}
        }}

        // Render table with data
        function renderTable(data) {{
            const tbody = document.getElementById('volumeTableBody');
            tbody.innerHTML = '';

            data.forEach((item, idx) => {{
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${{idx + 1}}</td>
                    <td><strong>${{item.ticker}}</strong></td>
                    <td>${{item.total_volume.toLocaleString()}}</td>
                    <td>${{item.cp_volume_ratio.toFixed(2)}}</td>
                    <td>${{item.total_oi.toLocaleString()}}</td>
                    <td>${{item.cp_oi_ratio.toFixed(2)}}</td>
                    <td>${{item.put_volume.toLocaleString()}}</td>
                    <td>${{item.call_volume.toLocaleString()}}</td>
                `;
                tbody.appendChild(row);
            }});
        }}

        // Add click handlers to sortable headers
        document.addEventListener('DOMContentLoaded', () => {{
            document.querySelectorAll('th.sortable').forEach(th => {{
                th.addEventListener('click', () => {{
                    const column = th.dataset.column;
                    const type = th.dataset.type;
                    sortTable(column, type);
                }});
            }});

            // Set initial sort indicator
            const initialHeader = document.querySelector('th[data-column="total_volume"]');
            if (initialHeader) {{
                initialHeader.classList.add('sorted-desc');
            }}
        }});

        // Volume Chart
        const volumeCtx = document.getElementById('volumeChart').getContext('2d');
        new Chart(volumeCtx, {{
            type: 'bar',
            data: {{
                labels: {tickers_json},
                datasets: [{{
                    label: '总成交量',
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
                        text: '期权成交量'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});

        // C/P Ratio Chart
        const cpCtx = document.getElementById('cpRatioChart').getContext('2d');
        new Chart(cpCtx, {{
            type: 'bar',
            data: {{
                labels: {tickers_json},
                datasets: [
                    {{
                        label: 'C/P 成交比',
                        data: {cp_volume_ratios_json},
                        backgroundColor: 'rgba(255, 99, 132, 0.6)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }},
                    {{
                        label: 'C/P 持仓比',
                        data: {cp_oi_ratios_json},
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
                        text: 'Call/Put 比例对比'
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
                    label: '持仓量',
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
                        text: '持仓量分布'
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
