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

    # 主要大盘指数（固定显示，不参与排序）
    INDEX_ETFS = {
        'SPY', 'QQQ', 'IWM', 'SPX'
    }

    def __init__(self):
        """Initialize the report generator"""
        self.template = self._get_template()

    def _classify_ticker(self, ticker: str) -> str:
        """
        Classify ticker as 'index' (major market indices) or 'stock' (stocks & other ETFs)

        Args:
            ticker: Ticker symbol

        Returns:
            'index' for SPY/QQQ/IWM, 'stock' for everything else
        """
        return 'index' if ticker in self.INDEX_ETFS else 'stock'

    def generate(
        self,
        data: List[Dict],
        anomalies: List[Dict],
        summary: Dict,
        metadata: Dict = None,
        output_file: str = "output/anomaly_report.html"
    ):
        """
        Generate HTML report

        Args:
            data: Aggregated options data
            anomalies: Detected anomalies
            summary: Anomaly summary statistics
            metadata: Metadata including data source
            output_file: Output file path
        """
        if metadata is None:
            metadata = {}
        import os
        import shutil

        # 过滤掉不需要显示的ticker
        filtered_data = [d for d in data if d['ticker'] not in ['SPXW', 'VIX']]

        # 将数据分成指数ETF和个股两组
        # 大盘指数：固定顺序显示 SPY, QQQ, IWM, SPX（如果存在的话），不参与排序
        index_order = ['SPY', 'QQQ', 'IWM', 'SPX']
        index_dict = {d['ticker']: d for d in filtered_data if d['ticker'] in self.INDEX_ETFS}
        sorted_index_data = [index_dict[ticker] for ticker in index_order if ticker in index_dict]

        # 个股和ETF：排除指数ETF，取Top 25
        stock_data = [d for d in filtered_data if d['ticker'] not in self.INDEX_ETFS]
        sorted_stock_data = sorted(stock_data, key=lambda x: x['total_volume'], reverse=True)[:25]

        # 用于整体图表的数据（包含所有过滤后数据的Top 30）
        sorted_data = sorted(filtered_data, key=lambda x: x['total_volume'], reverse=True)[:30]

        # Fetch current prices for displayed tickers only
        print("  💰 Fetching current prices for displayed tickers...")
        from price_fetcher import PriceFetcher
        price_fetcher = PriceFetcher()

        # Collect tickers that will be displayed
        display_tickers = list(set(
            [item['ticker'] for item in sorted_index_data] +
            [item['ticker'] for item in sorted_stock_data]
        ))

        if price_fetcher.is_available() and display_tickers:
            prices = price_fetcher.get_batch_quotes(display_tickers)
            # Add prices to all data items
            for item in data:
                item['current_price'] = prices.get(item['ticker'])
            print(f"  ✓ Fetched {len(prices)} prices for {len(display_tickers)} tickers")
        else:
            for item in data:
                item['current_price'] = None
            if not price_fetcher.is_available():
                print("  ⚠️  Polygon API not configured, skipping price fetch")

        # Prepare data for all charts - only use Stocks & ETFs Top 30 (exclude Market Indices)
        tickers = [d['ticker'] for d in sorted_stock_data]
        volumes = [d['total_volume'] for d in sorted_stock_data]
        cp_volume_ratios = [d['cp_volume_ratio'] for d in sorted_stock_data]
        cp_oi_ratios = [d['cp_oi_ratio'] for d in sorted_stock_data]
        open_interests = [d['total_oi'] for d in sorted_stock_data]

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

        # Add data source info to time display
        from datetime import datetime
        current_date = datetime.now().strftime('%Y-%m-%d')

        data_source = metadata.get('data_source', 'Unknown')
        if data_source in ['CSV', 'CSV+API']:
            csv_date = metadata.get('csv_date')

            # If csv_date is None or empty, try to infer from output_file name
            if not csv_date or csv_date == 'Unknown':
                # Try to extract date from output file name (YYYY-MM-DD.html)
                import re
                match = re.search(r'(\d{4}-\d{2}-\d{2})', output_file)
                if match:
                    csv_date = match.group(1)
                else:
                    # Fallback to current date minus 1 trading day
                    from trading_calendar import get_previous_trading_day
                    csv_date = get_previous_trading_day(current_date)

            time_display += f' | <strong>数据来源:</strong> CSV文件 ({csv_date}.csv.gz)'
            # Show trading date with post-market label
            stock_date_info = f"{csv_date} Post-Market Options Analysis"
        else:
            time_display += f' | <strong>数据来源:</strong> API'
            # Use current date for table header when using API
            stock_date_info = f"{current_date} from API"

        # Generate macro outlook analysis using AI
        macro_analysis = ''
        if sorted_index_data:
            from ai_analyzer import AIAnalyzer
            ai_analyzer = AIAnalyzer()
            if ai_analyzer.is_available():
                print("\n  🤖 Generating macro outlook analysis...")
                macro_text = ai_analyzer.analyze_macro_outlook(sorted_index_data)
                if macro_text:
                    # Convert markdown formatting to basic HTML
                    macro_analysis = self._markdown_to_html(macro_text)
                    print("  ✓ Macro analysis generated")
                else:
                    macro_analysis = '<p>Macro analysis unavailable</p>'
            else:
                macro_analysis = '<p>AI analysis not configured (OPENAI_API_KEY required)</p>'
        else:
            macro_analysis = '<p>Insufficient index data for macro analysis</p>'

        # Generate HTML
        html = self.template.format(
            report_date=time_display,
            total_tickers=len(filtered_data),
            total_anomalies=summary.get('total', 0),
            high_severity=summary.get('by_severity', {}).get('HIGH', 0),
            medium_severity=summary.get('by_severity', {}).get('MEDIUM', 0),
            low_severity=summary.get('by_severity', {}).get('LOW', 0),
            # All charts data (stocks/ETFs only, excluding Market Indices)
            tickers_json=json.dumps(tickers),
            volumes_json=json.dumps(volumes),
            cp_volume_ratios_json=json.dumps(cp_volume_ratios),
            cp_oi_ratios_json=json.dumps(cp_oi_ratios),
            open_interests_json=json.dumps(open_interests),
            # 指数ETF表格
            index_table_rows=self._generate_table_rows(sorted_index_data, include_leap_cp=False),
            index_data_json=json.dumps(sorted_index_data, ensure_ascii=False),
            index_count=len(sorted_index_data),
            # 个股表格
            stock_table_rows=self._generate_table_rows(sorted_stock_data, include_leap_cp=True),
            stock_data_json=json.dumps(sorted_stock_data, ensure_ascii=False),
            stock_date=stock_date_info,
            # 保留原有的（用于兼容）
            volume_table_rows=self._generate_table_rows(sorted_data),
            table_data_json=json.dumps(sorted_data, ensure_ascii=False),
            macro_analysis=macro_analysis
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

    def _markdown_to_html(self, text: str) -> str:
        """
        Convert simple markdown to HTML

        Args:
            text: Markdown formatted text

        Returns:
            HTML formatted text
        """
        import re

        # Escape HTML characters
        html_text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # Convert **bold**
        html_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_text)

        # Convert bullet points
        html_text = re.sub(r'^- (.+)$', r'<li>\1</li>', html_text, flags=re.MULTILINE)
        html_text = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', html_text, flags=re.DOTALL)
        html_text = html_text.replace('</ul>\n<ul>', '\n')

        # Convert paragraphs (double newline)
        paragraphs = html_text.split('\n\n')
        html_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if para and not para.startswith('<'):
                html_paragraphs.append(f'<p>{para}</p>')
            else:
                html_paragraphs.append(para)

        return '\n\n'.join(html_paragraphs)

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

    def _generate_table_rows(self, data: List[Dict], include_leap_cp: bool = False) -> str:
        """Generate table rows HTML for volume rankings

        Args:
            data: List of ticker data dicts
            include_leap_cp: Whether to include LEAP C/P ratio column (for stocks table)
        """
        rows = []
        for idx, item in enumerate(data, 1):
            # Format volume in 万 (W) with 2 decimal places
            volume_w = item['total_volume'] / 10000
            oi_w = item['total_oi'] / 10000

            # Format Top 3 contracts by VOLUME with Current Price at the beginning
            top3_volume_html = ''
            current_price = item.get('current_price')
            if current_price:
                top3_volume_html += f"<div><small>Current: ${current_price:.2f}</small></div>"

            # Show top 3 contracts by volume (from CSV)
            for i, contract in enumerate(item.get('top_3_contracts_volume', [])[:3], 1):
                contract_short = self._format_contract_short(contract)
                volume_k = contract.get('volume', 0) / 1000
                pct = contract.get('percentage', 0)
                top3_volume_html += f"<div class='contract-item'>{contract_short} <span class='oi-badge'>{volume_k:.0f}K ({pct:.1f}%)</span></div>"

            if not top3_volume_html or not item.get('top_3_contracts_volume'):
                top3_volume_html = '<small>N/A</small>'

            # Format Top 3 LEAP contracts by VOLUME (3+ months out, from CSV)
            top3_leap_volume_html = ''
            if current_price:
                top3_leap_volume_html += f"<div><small>Current: ${current_price:.2f}</small></div>"

            for i, contract in enumerate(item.get('top_3_leap_volume', [])[:3], 1):
                contract_short = self._format_contract_short(contract)
                volume_k = contract.get('volume', 0) / 1000
                pct = contract.get('percentage', 0)
                top3_leap_volume_html += f"<div class='contract-item'>{contract_short} <span class='oi-badge'>{volume_k:.0f}K ({pct:.1f}%)</span></div>"

            if not top3_leap_volume_html or not item.get('top_3_leap_volume'):
                top3_leap_volume_html = '<small>N/A</small>'

            # Format Top 3 contracts by OI (from API, only for recent post-market data)
            top3_oi_html = ''
            if current_price:
                top3_oi_html += f"<div><small>Current: ${current_price:.2f}</small></div>"

            for i, contract in enumerate(item.get('top_3_oi', [])[:3], 1):
                contract_short = self._format_contract_short(contract)
                oi_k = contract.get('oi', 0) / 1000
                pct = contract.get('percentage', 0)
                top3_oi_html += f"<div class='contract-item'>{contract_short} <span class='oi-badge'>{oi_k:.0f}K ({pct:.1f}%)</span></div>"

            if not top3_oi_html or not item.get('top_3_oi'):
                top3_oi_html = '<small>N/A</small>'

            # Format history activity
            history = item.get('history', {})
            appearances = history.get('appearances', 0)
            icon = history.get('icon', '[NEW]')
            rank_change = history.get('rank_change')
            avg_rank = history.get('avg_rank')

            # Rank change symbol
            if rank_change is None or rank_change == 0:
                rank_symbol = '-'
            elif rank_change > 0:
                rank_symbol = f'+{rank_change}'
            else:
                rank_symbol = f'-{abs(rank_change)}'

            # Build row HTML
            if include_leap_cp:
                # Stocks table - include LEAP C/P column
                leap_cp = item.get('leap_cp_ratio', 0)
                leap_cp_html = f"{leap_cp:.2f}" if leap_cp else "-"
                avg_trade_size = item.get('avg_trade_size', 0)

                rows.append(f"""
                    <tr>
                        <td>{idx}</td>
                        <td><strong>{item['ticker']}</strong></td>
                        <td>{volume_w:.2f}W</td>
                        <td>{item['cp_volume_ratio']:.2f}</td>
                        <td>{avg_trade_size:.1f}</td>
                        <td>{leap_cp_html}</td>
                        <td>{oi_w:.2f}W</td>
                        <td>{item['cp_oi_ratio']:.2f}</td>
                        <td class="compact-cell">{top3_volume_html}</td>
                        <td class="compact-cell">{top3_leap_volume_html}</td>
                        <td class="compact-cell">{top3_oi_html}</td>
                    </tr>
                """)
            else:
                # Index table - only show: Rank, Ticker, Total Volume, C/P Volume, Avg Trade Size
                avg_trade_size = item.get('avg_trade_size', 0)

                rows.append(f"""
                    <tr>
                        <td>{idx}</td>
                        <td><strong>{item['ticker']}</strong></td>
                        <td>{volume_w:.2f}W</td>
                        <td>{item['cp_volume_ratio']:.2f}</td>
                        <td>{avg_trade_size:.1f}</td>
                    </tr>
                """)
        return ''.join(rows)

    def _generate_anomaly_rows(self, anomalies: List[Dict]) -> str:
        """Generate anomaly rows HTML"""
        if not anomalies:
            return '<tr><td colspan="4" style="text-align:center;">No anomalies detected</td></tr>'

        severity_colors = {
            'HIGH': '#000',
            'MEDIUM': '#000',
            'LOW': '#000'
        }

        severity_names = {
            'HIGH': 'HIGH',
            'MEDIUM': 'MED',
            'LOW': 'LOW'
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
            font-family: "Courier New", Courier, monospace;
            background: #f5f5f7;
            padding: 40px 20px;
            color: #1d1d1f;
            line-height: 1.4;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        .header {{
            background: #fff;
            padding: 40px;
            border: 1px solid #d2d2d7;
            margin-bottom: 20px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 32px;
            font-weight: 600;
            margin-bottom: 12px;
            color: #1d1d1f;
            letter-spacing: -0.5px;
        }}

        .header .date {{
            color: #6e6e73;
            font-size: 14px;
        }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1px;
            margin-bottom: 20px;
            background: #d2d2d7;
            border: 1px solid #d2d2d7;
        }}

        .stat-card {{
            background: #fff;
            padding: 24px;
            text-align: center;
        }}

        .stat-card .number {{
            font-size: 36px;
            font-weight: 600;
            margin: 8px 0;
            color: #1d1d1f;
        }}

        .stat-card .label {{
            color: #6e6e73;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .stat-card.high .number {{ color: #1d1d1f; }}
        .stat-card.medium .number {{ color: #1d1d1f; }}
        .stat-card.low .number {{ color: #1d1d1f; }}
        .stat-card.total .number {{ color: #1d1d1f; }}

        .nav {{
            background: #fff;
            padding: 16px 24px;
            border: 1px solid #d2d2d7;
            margin-bottom: 20px;
            text-align: center;
        }}

        .nav a {{
            display: inline-block;
            padding: 8px 16px;
            margin: 0 4px;
            background: #000;
            color: #fff;
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            transition: background 0.2s;
        }}

        .nav a:hover {{
            background: #333;
        }}

        .section {{
            background: #fff;
            padding: 32px;
            border: 1px solid #d2d2d7;
            margin-bottom: 20px;
        }}

        .section h2 {{
            margin-bottom: 24px;
            color: #1d1d1f;
            font-size: 24px;
            font-weight: 600;
            letter-spacing: -0.3px;
        }}

        .chart-container {{
            position: relative;
            height: 400px;
            margin: 24px 0;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 16px;
            border: 1px solid #d2d2d7;
        }}

        table th {{
            background: #f5f5f7;
            color: #1d1d1f;
            padding: 8px 12px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
            border-bottom: 1px solid #d2d2d7;
        }}

        table th.sortable {{
            cursor: pointer;
            position: relative;
        }}

        table th.sortable:hover {{
            background: #e8e8ed;
        }}

        table th.sortable.sorted-asc .sort-icon::after {{
            content: ' ^';
        }}

        table th.sortable.sorted-desc .sort-icon::after {{
            content: ' v';
        }}

        .sort-icon {{
            font-size: 12px;
            opacity: 0.5;
            margin-left: 4px;
        }}

        table td {{
            padding: 8px 12px;
            border-bottom: 1px solid #d2d2d7;
            font-size: 14px;
        }}

        table tr:hover {{
            background: #f5f5f7;
        }}


        .compact-cell {{
            font-size: 12px;
            line-height: 1.4;
            padding: 6px 10px !important;
        }}

        .compact-cell div {{
            margin: 2px 0;
        }}

        .contract-item {{
            white-space: nowrap;
        }}

        .oi-badge {{
            background: #f5f5f7;
            padding: 2px 6px;
            font-size: 11px;
            color: #1d1d1f;
            white-space: nowrap;
        }}

        .pct {{
            color: #6e6e73;
            font-size: 12px;
        }}

        .compact-cell small {{
            color: #86868b;
            font-size: 11px;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 10px;
            color: #fff;
            background: #000;
            font-size: 12px;
            font-weight: 500;
        }}

        .macro-content {{
            line-height: 1.8;
            font-size: 14px;
        }}

        .macro-content p {{
            margin: 16px 0;
        }}

        .macro-content strong {{
            font-weight: 600;
            color: #1d1d1f;
        }}

        .macro-content ul {{
            margin: 12px 0;
            padding-left: 24px;
        }}

        .macro-content li {{
            margin: 8px 0;
        }}

        .footer {{
            text-align: center;
            color: #6e6e73;
            margin-top: 40px;
            padding: 20px;
            font-size: 12px;
        }}

        @media (max-width: 768px) {{
            .stats {{
                grid-template-columns: 1fr;
            }}
            .header h1 {{
                font-size: 24px;
            }}
            .nav a {{
                display: block;
                margin: 8px 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Options Market Anomaly Analysis</h1>
            <p class="date">{report_date}</p>
        </div>

        <div class="nav">
            <a href="index.html">Latest Report</a>
            <a href="archive.html">Archive</a>
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
            <h2>Macro Market Outlook</h2>
            <div class="macro-content">
                {macro_analysis}
            </div>
        </div>

        <div class="section">
            <h2>Market Indices ({index_count})</h2>
            <table id="indexTable">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th class="sortable" data-table="index" data-column="ticker" data-type="string">Ticker <span class="sort-icon"></span></th>
                        <th class="sortable" data-table="index" data-column="total_volume" data-type="number">Total Volume <span class="sort-icon"></span></th>
                        <th class="sortable" data-table="index" data-column="cp_volume_ratio" data-type="number">C/P Volume <span class="sort-icon"></span></th>
                        <th class="sortable" data-table="index" data-column="avg_trade_size" data-type="number">Avg Trade Size <span class="sort-icon"></span></th>
                    </tr>
                </thead>
                <tbody id="indexTableBody">
                    {index_table_rows}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Stocks & ETFs - Top 25 ({stock_date})</h2>
            <table id="stockTable">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th class="sortable" data-table="stock" data-column="ticker" data-type="string">Ticker <span class="sort-icon"></span></th>
                        <th class="sortable" data-table="stock" data-column="total_volume" data-type="number">Total Volume <span class="sort-icon"></span></th>
                        <th class="sortable" data-table="stock" data-column="cp_volume_ratio" data-type="number">C/P Volume <span class="sort-icon"></span></th>
                        <th class="sortable" data-table="stock" data-column="avg_trade_size" data-type="number">Avg Trade Size <span class="sort-icon"></span></th>
                        <th class="sortable" data-table="stock" data-column="leap_cp_ratio" data-type="number">LEAP C/P <span class="sort-icon"></span></th>
                        <th class="sortable" data-table="stock" data-column="total_oi" data-type="number">Total OI <span class="sort-icon"></span></th>
                        <th class="sortable" data-table="stock" data-column="cp_oi_ratio" data-type="number">C/P OI <span class="sort-icon"></span></th>
                        <th>Top 3 Volume</th>
                        <th>Top 3 Volume Leap</th>
                        <th>Top 3 OI</th>
                    </tr>
                </thead>
                <tbody id="stockTableBody">
                    {stock_table_rows}
                </tbody>
            </table>

            <div style="margin-top: 20px; padding: 15px; background-color: #f5f5f7; border-radius: 8px; font-size: 14px;">
                <h3 style="margin-top: 0; font-size: 15px; color: #1d1d1f;">📊 Top 3 列说明</h3>
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
                    <div>
                        <strong style="color: #06c;">Top 3 Volume</strong>
                        <p style="margin: 5px 0 0 0; color: #86868b;">成交量最大的前3个期权合约（基于当日成交量）</p>
                    </div>
                    <div>
                        <strong style="color: #06c;">Top 3 Volume Leap</strong>
                        <p style="margin: 5px 0 0 0; color: #86868b;">距到期日≥90天且成交量最大的前3个期权合约</p>
                    </div>
                    <div>
                        <strong style="color: #06c;">Top 3 OI</strong>
                        <p style="margin: 5px 0 0 0; color: #86868b;">持仓量（Open Interest）最大的前3个期权合约</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Call/Put Ratio Analysis ({stock_date})</h2>
            <div class="chart-container">
                <canvas id="cpRatioChart"></canvas>
            </div>
        </div>

        <div class="section">
            <h2>Volume Analysis ({stock_date})</h2>
            <div class="chart-container">
                <canvas id="volumeOIChart"></canvas>
            </div>
        </div>

        <div class="footer">
            <p>Options Anomaly Detection System | Data: Polygon.io</p>
            <p>For reference only. Not investment advice.</p>
        </div>
    </div>

    <script>
        // Store table data for sorting
        const indexData = {index_data_json};
        const stockData = {stock_data_json};

        let indexSortColumn = 'total_volume';
        let indexSortOrder = 'desc';
        let stockSortColumn = 'total_volume';
        let stockSortOrder = 'desc';

        // Table sorting function
        function sortTable(tableType, column, type) {{
            const tableData = tableType === 'index' ? indexData : stockData;
            const currentSortColumn = tableType === 'index' ? indexSortColumn : stockSortColumn;
            const currentSortOrder = tableType === 'index' ? indexSortOrder : stockSortOrder;
            // Toggle sort order if clicking same column
            let newSortOrder;
            if (currentSortColumn === column) {{
                newSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
            }} else {{
                newSortOrder = 'desc'; // Default to descending
            }}

            // Update state
            if (tableType === 'index') {{
                indexSortColumn = column;
                indexSortOrder = newSortOrder;
            }} else {{
                stockSortColumn = column;
                stockSortOrder = newSortOrder;
            }}

            // Sort data
            const sortedData = [...tableData].sort((a, b) => {{
                let valA = a[column];
                let valB = b[column];

                // Handle string comparison
                if (type === 'string') {{
                    valA = String(valA).toLowerCase();
                    valB = String(valB).toLowerCase();
                    return newSortOrder === 'asc'
                        ? valA.localeCompare(valB)
                        : valB.localeCompare(valA);
                }}

                // Handle number comparison
                valA = Number(valA) || 0;
                valB = Number(valB) || 0;
                return newSortOrder === 'asc' ? valA - valB : valB - valA;
            }});

            // Update table
            renderTable(tableType, sortedData);

            // Update sort indicators (only for this table)
            const tableSelector = tableType === 'index' ? '#indexTable' : '#stockTable';
            document.querySelectorAll(`${{tableSelector}} th.sortable`).forEach(th => {{
                th.classList.remove('sorted-asc', 'sorted-desc');
            }});
            const activeHeader = document.querySelector(`${{tableSelector}} th[data-column="${{column}}"]`);
            if (activeHeader) {{
                activeHeader.classList.add(`sorted-${{newSortOrder}}`);
            }}
        }}

        // Helper: Format contract short form (e.g., 250131C600)
        function formatContractShort(contract) {{
            try {{
                let expiry = contract.expiry || '';
                if (expiry) {{
                    // Extract YYMMDD from 2025-01-31
                    expiry = expiry.replace(/-/g, '').slice(-6);
                }}
                const contractType = (contract.type || 'X')[0].toUpperCase();
                const strike = Math.floor(contract.strike || 0);
                return `${{expiry}}${{contractType}}${{strike}}`;
            }} catch (e) {{
                return 'N/A';
            }}
        }}

        // Render table with data
        function renderTable(tableType, data) {{
            const tbodyId = tableType === 'index' ? 'indexTableBody' : 'stockTableBody';
            const tbody = document.getElementById(tbodyId);
            tbody.innerHTML = '';

            data.forEach((item, idx) => {{
                // Format volume and OI in 万 (W) with 2 decimal places
                const volumeW = (item.total_volume / 10000).toFixed(2) + 'W';
                const oiW = (item.total_oi / 10000).toFixed(2) + 'W';
                const avgTradeSize = item.avg_trade_size || 0;
                const currentPrice = item.current_price;

                const row = document.createElement('tr');

                // For stock table, include LEAP C/P column and all 3 Top 3 columns
                if (tableType === 'stock') {{
                    const leapCp = item.leap_cp_ratio || 0;
                    const leapCpHtml = leapCp ? leapCp.toFixed(2) : '-';

                    // Format Top 3 Volume
                    let top3VolumeHtml = '';
                    if (currentPrice) {{
                        top3VolumeHtml += `<div><small>Current: $${{currentPrice.toFixed(2)}}</small></div>`;
                    }}
                    const top3ContractsVolume = item.top_3_contracts_volume || [];
                    top3ContractsVolume.slice(0, 3).forEach((contract) => {{
                        const ticker = contract.ticker || 'N/A';
                        const volumeK = (contract.volume || 0) / 1000;
                        const pct = contract.percentage || 0;
                        top3VolumeHtml += `<div class='contract-item'>${{ticker}} <span class='oi-badge'>${{Math.round(volumeK)}}K (${{pct.toFixed(1)}}%)</span></div>`;
                    }});
                    if (!top3VolumeHtml || top3ContractsVolume.length === 0) {{
                        top3VolumeHtml = '<small>N/A</small>';
                    }}

                    // Format Top 3 Volume Leap
                    let top3LeapVolumeHtml = '';
                    if (currentPrice) {{
                        top3LeapVolumeHtml += `<div><small>Current: $${{currentPrice.toFixed(2)}}</small></div>`;
                    }}
                    const top3LeapVolume = item.top_3_leap_volume || [];
                    top3LeapVolume.slice(0, 3).forEach((contract) => {{
                        const ticker = contract.ticker || 'N/A';
                        const volumeK = (contract.volume || 0) / 1000;
                        const pct = contract.percentage || 0;
                        top3LeapVolumeHtml += `<div class='contract-item'>${{ticker}} <span class='oi-badge'>${{Math.round(volumeK)}}K (${{pct.toFixed(1)}}%)</span></div>`;
                    }});
                    if (!top3LeapVolumeHtml || top3LeapVolume.length === 0) {{
                        top3LeapVolumeHtml = '<small>N/A</small>';
                    }}

                    // Format Top 3 OI
                    let top3OIHtml = '';
                    if (currentPrice) {{
                        top3OIHtml += `<div><small>Current: $${{currentPrice.toFixed(2)}}</small></div>`;
                    }}
                    const top3OI = item.top_3_oi || [];
                    top3OI.slice(0, 3).forEach((contract) => {{
                        const ticker = contract.ticker || 'N/A';
                        const oiK = (contract.oi || 0) / 1000;
                        const pct = contract.percentage || 0;
                        top3OIHtml += `<div class='contract-item'>${{ticker}} <span class='oi-badge'>${{Math.round(oiK)}}K (${{pct.toFixed(1)}}%)</span></div>`;
                    }});
                    if (!top3OIHtml || top3OI.length === 0) {{
                        top3OIHtml = '<small>N/A</small>';
                    }}

                    row.innerHTML = `
                        <td>${{idx + 1}}</td>
                        <td><strong>${{item.ticker}}</strong></td>
                        <td>${{volumeW}}</td>
                        <td>${{item.cp_volume_ratio.toFixed(2)}}</td>
                        <td>${{avgTradeSize.toFixed(1)}}</td>
                        <td>${{leapCpHtml}}</td>
                        <td>${{oiW}}</td>
                        <td>${{item.cp_oi_ratio.toFixed(2)}}</td>
                        <td class="compact-cell">${{top3VolumeHtml}}</td>
                        <td class="compact-cell">${{top3LeapVolumeHtml}}</td>
                        <td class="compact-cell">${{top3OIHtml}}</td>
                    `;
                }} else {{
                    // Index table - only show: Rank, Ticker, Total Volume, C/P Volume, Avg Trade Size
                    row.innerHTML = `
                        <td>${{idx + 1}}</td>
                        <td><strong>${{item.ticker}}</strong></td>
                        <td>${{volumeW}}</td>
                        <td>${{item.cp_volume_ratio.toFixed(2)}}</td>
                        <td>${{avgTradeSize.toFixed(1)}}</td>
                    `;
                }}

                tbody.appendChild(row);
            }});
        }}

        // Add click handlers to sortable headers
        document.addEventListener('DOMContentLoaded', () => {{
            // Setup sorting for index table
            document.querySelectorAll('#indexTable th.sortable').forEach(th => {{
                th.addEventListener('click', () => {{
                    const column = th.dataset.column;
                    const type = th.dataset.type;
                    sortTable('index', column, type);
                }});
            }});

            // Setup sorting for stock table
            document.querySelectorAll('#stockTable th.sortable').forEach(th => {{
                th.addEventListener('click', () => {{
                    const column = th.dataset.column;
                    const type = th.dataset.type;
                    sortTable('stock', column, type);
                }});
            }});

            // Set initial sort indicators for both tables
            const indexHeader = document.querySelector('#indexTable th[data-column="total_volume"]');
            if (indexHeader) {{
                indexHeader.classList.add('sorted-desc');
            }}
            const stockHeader = document.querySelector('#stockTable th[data-column="total_volume"]');
            if (stockHeader) {{
                stockHeader.classList.add('sorted-desc');
            }}
        }});

        // Combined Volume & OI Chart
        const volumeData = {volumes_json};
        const oiData = {open_interests_json};
        const volumeOICtx = document.getElementById('volumeOIChart').getContext('2d');

        new Chart(volumeOICtx, {{
            type: 'bar',
            data: {{
                labels: {tickers_json},
                datasets: [
                    {{
                        label: '总成交量',
                        data: volumeData,
                        backgroundColor: 'rgba(102, 126, 234, 0.8)',
                        borderColor: 'rgba(102, 126, 234, 1)',
                        borderWidth: 1
                    }},
                    {{
                        label: '持仓量',
                        data: oiData,
                        backgroundColor: 'rgba(75, 192, 192, 0.6)',
                        borderColor: 'rgba(75, 192, 192, 1)',
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
                        text: '成交量 & 持仓量对比'
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
    </script>
</body>
</html>'''
