#!/usr/bin/env python3
"""
AI Analyzer Module
使用 OpenAI GPT 对期权市场数据进行智能分析和总结
"""
import os
import json
from typing import Dict, List, Optional


class AIAnalyzer:
    """使用 OpenAI API 分析期权市场数据"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AI Analyzer

        Args:
            api_key: OpenAI API key (optional, will use env var if not provided)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.client = None

        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except ImportError:
                print("⚠️  OpenAI package not installed. Run: pip install openai")
            except Exception as e:
                print(f"⚠️  Failed to initialize OpenAI client: {e}")

    def is_available(self) -> bool:
        """
        Check if AI analysis is available

        Returns:
            True if OpenAI API is configured and available
        """
        return self.client is not None

    def analyze_market_data(
        self,
        data: List[Dict],
        anomalies: List[Dict],
        summary: Dict,
        max_tokens: int = 1000
    ) -> Optional[str]:
        """
        使用 GPT 分析市场数据并生成总结

        Args:
            data: Top 30 市场数据
            anomalies: 异常列表
            summary: 异常摘要
            max_tokens: 最大返回 tokens 数

        Returns:
            AI 生成的市场分析报告（Markdown 格式）
        """
        if not self.is_available():
            return None

        try:
            # 准备更完整的数据供 GPT 分析（增加到 Top 15）
            top_15 = data[:15]
            market_summary = {
                'total_tickers': len(data),
                'top_15': [
                    {
                        'ticker': item['ticker'],
                        'total_volume': item['total_volume'],
                        'put_volume': item.get('put_volume', 0),
                        'call_volume': item.get('call_volume', 0),
                        'cp_volume_ratio': item['cp_volume_ratio'],
                        'total_oi': item['total_oi'],
                        'put_oi': item.get('put_oi', 0),
                        'call_oi': item.get('call_oi', 0),
                        'cp_oi_ratio': item['cp_oi_ratio'],
                        'contracts_count': item.get('contracts_count', 0),
                        'top_3_contracts': item.get('top_3_contracts', [])[:3],
                        'strike_concentration': item.get('strike_concentration', {}),
                        'history': {
                            'appearances': item.get('history', {}).get('appearances', 0),
                            'icon': item.get('history', {}).get('icon', ''),
                            'trend': item.get('history', {}).get('trend', 'N/A')
                        }
                    }
                    for item in top_15
                ],
                'anomalies_count': summary.get('total', 0),
                'high_severity': summary.get('by_severity', {}).get('HIGH', 0),
                'medium_severity': summary.get('by_severity', {}).get('MEDIUM', 0),
                'low_severity': summary.get('by_severity', {}).get('LOW', 0),
                'key_anomalies': anomalies[:5] if anomalies else []
            }

            # 构建 prompt
            prompt = self._build_analysis_prompt(market_summary)

            # 调用 GPT
            response = self.client.chat.completions.create(
                model="gpt-4o",  # 使用更强大的模型以获得更好的市场洞察
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior options trading analyst with 15+ years of experience in institutional trading. You excel at interpreting options flow data, identifying institutional positioning, and providing actionable trade recommendations. You stay current on market news, global macro trends, and sector dynamics. Your analysis is concise, data-driven, and focused on risk-adjusted returns."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1500,  # 增加token以支持更详细的分析
                temperature=0.7
            )

            analysis = response.choices[0].message.content

            return analysis

        except Exception as e:
            print(f"❌ AI 分析失败: {e}")
            return None

    def _build_analysis_prompt(self, market_summary: Dict) -> str:
        """
        构建 GPT 分析 prompt

        Args:
            market_summary: 市场数据摘要

        Returns:
            Prompt 字符串
        """
        # 构建更详细的标的信息（包含网页数据的所有字段）
        tickers_detail = []
        for i, item in enumerate(market_summary['top_15'], 1):
            strike_conc = item.get('strike_concentration', {})
            top_contracts = item.get('top_3_contracts', [])

            # 构建完整的合约详情（包含所有3个合约及其占比）
            contracts_str = ""
            if top_contracts:
                contracts_list = []
                for c in top_contracts:  # 显示所有3个合约
                    contract_detail = (
                        f"{c.get('type', 'N/A').upper()} Strike ${c.get('strike', 'N/A')} "
                        f"Exp {c.get('expiry', 'N/A')} "
                        f"(OI {c.get('oi', 0):,}, {c.get('percentage', 0):.1f}% of total)"
                    )
                    contracts_list.append(contract_detail)
                contracts_str = "\n     " + "\n     ".join(contracts_list)

            # 完整的价格区间信息
            strike_info = (
                f"Range {strike_conc.get('range', 'N/A')}, "
                f"Dominant Strike ${strike_conc.get('dominant_strike', 'N/A')}, "
                f"Concentration {strike_conc.get('percentage', 0):.1f}% "
                f"(OI {strike_conc.get('oi', 0):,})"
            )

            detail = (
                f"{i}. **{item['ticker']}**:\n"
                f"   - Total Volume: {item['total_volume']:,} | Total OI: {item['total_oi']:,}\n"
                f"   - Volume: Call {item['call_volume']:,} / Put {item['put_volume']:,} "
                f"(C/P Ratio {item['cp_volume_ratio']:.2f})\n"
                f"   - OI: Call {item['call_oi']:,} / Put {item['put_oi']:,} "
                f"(C/P Ratio {item['cp_oi_ratio']:.2f})\n"
                f"   - Contracts: {item['contracts_count']}\n"
                f"   - Strike Concentration: {strike_info}\n"
                f"   - Top 3 Contracts:{contracts_str}"
            )
            tickers_detail.append(detail)

        tickers_str = "\n\n".join(tickers_detail)

        anomalies_str = ""
        if market_summary['key_anomalies']:
            anomalies_str = "\n\n# 主要异常\n" + "\n".join([
                f"- **{a['ticker']}**: {a['description']} (严重程度: {a['severity']})"
                for a in market_summary['key_anomalies']
            ])

        prompt = f"""Analyze the following US options market data and provide professional market insights:

# Market Overview
- Total Tickers Analyzed: {market_summary['total_tickers']}
- Anomalies Detected: {market_summary['anomalies_count']} (High: {market_summary['high_severity']}, Medium: {market_summary['medium_severity']}, Low: {market_summary['low_severity']})

# Top 15 Active Tickers - Complete Data

{tickers_str}
{anomalies_str}

Please provide comprehensive analysis in ENGLISH (Markdown format):

## 1. Market Sentiment Analysis
- Based on C/P ratios across Top 15 tickers, assess overall market sentiment (Bullish/Bearish/Neutral)
- Analyze Call vs Put volume/OI to determine fund flow direction
- Consider current global market context (equity indices, VIX, bond yields)
- Factor in any recent market-moving news or events

## 2. Deep Dive on Top 5 Tickers
- Analyze characteristics of top 5 most active tickers
- Examine dominant contracts (strikes, expiries) and what they imply
- Assess strike concentration and market expectations
- Consider sector rotation and institutional positioning

## 3. Key Contract Analysis
- Interpret significance of dominant strikes and expiry dates
- Identify critical support/resistance levels based on strike concentration
- Analyze unusual contract activity (high OI with specific strikes/dates)

## 4. Risk Factors & Market Catalysts
- Highlight any anomalies requiring attention
- Identify potential market volatility drivers
- Note sector-specific or macro risks

## 5. TOP 5 ACTIONABLE TRADE RECOMMENDATIONS
For each recommendation, specify:
- **Ticker & Action**: Stock or Options (specify contract details if options)
- **Direction**: Long/Short, Call/Put
- **Rationale**: Why this trade based on the data
- **Entry/Target**: Suggested levels
- **Risk Level**: Low/Medium/High
- **Time Horizon**: Short-term (1-2 weeks) / Medium-term (1-2 months)

Example format:
**Trade #1: WMT Stock Long**
- Action: Buy WMT stock
- Rationale: Strong Call volume (3.05M) with C/P 1.54, dominant Call strike at $60 suggests bullish bias
- Entry: Current levels, Target: $62-65
- Risk: Medium, Stop below $57
- Horizon: 1-2 weeks

Keep analysis concise (500-700 words), actionable, and suitable for morning decision-making.
"""

        return prompt

    def generate_email_subject(self, data: List[Dict], anomalies_count: int) -> str:
        """
        生成邮件主题

        Args:
            data: 市场数据
            anomalies_count: 异常数量

        Returns:
            邮件主题
        """
        from datetime import datetime

        date_str = datetime.now().strftime('%Y-%m-%d')
        top_ticker = data[0]['ticker'] if data else 'N/A'

        if anomalies_count > 0:
            return f"Options Market Report {date_str} - {top_ticker} Leading | {anomalies_count} Anomalies"
        else:
            return f"Options Market Report {date_str} - {top_ticker} Leading"

    def format_for_email(self, analysis: str, data: List[Dict], summary: Dict) -> str:
        """
        格式化为邮件内容（HTML）

        Args:
            analysis: AI 分析结果
            data: 市场数据
            summary: 异常摘要

        Returns:
            HTML 格式的邮件内容
        """
        from datetime import datetime
        import markdown

        # 转换 Markdown 到 HTML
        analysis_html = markdown.markdown(analysis)

        # Top 5 表格（简洁风格，无图标）
        top_5_rows = []
        for i, item in enumerate(data[:5], 1):
            top_5_rows.append(f"""
                <tr>
                    <td>{i}</td>
                    <td><strong>{item['ticker']}</strong></td>
                    <td>{item['total_volume']:,}</td>
                    <td>{item['cp_volume_ratio']:.2f}</td>
                    <td>{item['total_oi']:,}</td>
                </tr>
            """)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Courier New', Courier, monospace;
            line-height: 1.8;
            color: #1d1d1f;
            max-width: 700px;
            margin: 0 auto;
            padding: 40px 20px;
            background-color: #ffffff;
        }}
        .container {{
            background: #ffffff;
            padding: 0;
        }}
        h1 {{
            font-size: 24px;
            font-weight: 600;
            color: #1d1d1f;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }}
        .date {{
            font-size: 13px;
            color: #86868b;
            margin-bottom: 40px;
        }}
        h2 {{
            font-size: 18px;
            font-weight: 600;
            color: #1d1d1f;
            margin-top: 40px;
            margin-bottom: 20px;
            letter-spacing: -0.3px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0 40px 0;
            font-size: 13px;
        }}
        th {{
            background: #f5f5f7;
            color: #1d1d1f;
            padding: 12px 8px;
            text-align: left;
            font-weight: 600;
            border-bottom: 1px solid #d2d2d7;
        }}
        td {{
            padding: 12px 8px;
            border-bottom: 1px solid #f5f5f7;
            color: #1d1d1f;
        }}
        .summary {{
            background: #f5f5f7;
            padding: 20px;
            margin: 30px 0;
            font-size: 13px;
            line-height: 1.6;
        }}
        .summary-item {{
            margin: 8px 0;
        }}
        .ai-analysis {{
            margin: 40px 0;
            padding: 0;
            font-size: 14px;
            line-height: 1.8;
        }}
        .ai-analysis h1,
        .ai-analysis h2,
        .ai-analysis h3 {{
            font-size: 16px;
            font-weight: 600;
            color: #1d1d1f;
            margin-top: 24px;
            margin-bottom: 12px;
        }}
        .ai-analysis p {{
            margin: 12px 0;
        }}
        .ai-analysis ul, .ai-analysis ol {{
            margin: 12px 0;
            padding-left: 20px;
        }}
        .ai-analysis li {{
            margin: 8px 0;
        }}
        .footer {{
            margin-top: 60px;
            padding-top: 20px;
            border-top: 1px solid #d2d2d7;
            text-align: center;
            color: #86868b;
            font-size: 11px;
            line-height: 1.6;
        }}
        a {{
            color: #06c;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        strong {{
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Options Market Daily Report</h1>
        <div class="date">{datetime.now().strftime('%Y-%m-%d %A')}</div>

        <div class="summary">
            <div class="summary-item">Tickers Analyzed: <strong>{len(data)}</strong></div>
            <div class="summary-item">Anomalies Detected: <strong>{summary.get('total', 0)}</strong></div>
            <div class="summary-item">Top Active: <strong>{data[0]['ticker']}</strong> (Volume {data[0]['total_volume']:,})</div>
        </div>

        <h2>Top 5 Active Tickers</h2>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Ticker</th>
                    <th>Volume</th>
                    <th>C/P Ratio</th>
                    <th>Open Interest</th>
                </tr>
            </thead>
            <tbody>
                {''.join(top_5_rows)}
            </tbody>
        </table>

        <h2>AI Market Analysis</h2>
        <div class="ai-analysis">
            {analysis_html}
        </div>

        <div class="footer">
            <div><a href="https://onlinefchen.github.io/options-anomaly-detector/">View Full Report</a> | <a href="https://github.com/onlinefchen/options-anomaly-detector">GitHub</a></div>
            <div style="margin-top: 10px;">Automated Report - For Reference Only</div>
        </div>
    </div>
</body>
</html>
"""
        return html
