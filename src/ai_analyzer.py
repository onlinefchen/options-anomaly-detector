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
                model="gpt-4o-mini",  # 使用更经济的模型
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位专业的期权市场分析师，擅长解读期权数据并提供清晰的市场洞察。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
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
        # 构建更详细的标的信息
        tickers_detail = []
        for i, item in enumerate(market_summary['top_15'], 1):
            strike_conc = item.get('strike_concentration', {})
            top_contracts = item.get('top_3_contracts', [])

            # 构建合约详情
            contracts_str = ""
            if top_contracts:
                contracts_str = " | 主力合约: " + ", ".join([
                    f"{c.get('type', 'N/A').upper()} {c.get('strike', 'N/A')} "
                    f"({c.get('expiry', 'N/A')}, OI {c.get('oi', 0):,})"
                    for c in top_contracts[:2]  # 只显示前2个合约
                ])

            detail = (
                f"{i}. **{item['ticker']}**:\n"
                f"   - 成交: Call {item['call_volume']:,} / Put {item['put_volume']:,} "
                f"(C/P比 {item['cp_volume_ratio']:.2f})\n"
                f"   - 持仓: Call {item['call_oi']:,} / Put {item['put_oi']:,} "
                f"(C/P比 {item['cp_oi_ratio']:.2f})\n"
                f"   - 合约数: {item['contracts_count']}, "
                f"主力价格区间: {strike_conc.get('range', 'N/A')} "
                f"(集中度 {strike_conc.get('percentage', 0):.1f}%){contracts_str}"
            )
            tickers_detail.append(detail)

        tickers_str = "\n\n".join(tickers_detail)

        anomalies_str = ""
        if market_summary['key_anomalies']:
            anomalies_str = "\n\n# 主要异常\n" + "\n".join([
                f"- **{a['ticker']}**: {a['description']} (严重程度: {a['severity']})"
                for a in market_summary['key_anomalies']
            ])

        prompt = f"""请分析以下美股期权市场数据，并提供专业的市场洞察：

# 市场概况
- 分析标的总数: {market_summary['total_tickers']}
- 检测到异常: {market_summary['anomalies_count']} 个 (高: {market_summary['high_severity']}, 中: {market_summary['medium_severity']}, 低: {market_summary['low_severity']})

# Top 15 活跃标的详细数据

{tickers_str}
{anomalies_str}

请提供以下分析（用中文，Markdown 格式）：

1. **市场整体趋势分析**
   - 根据 Top 15 标的的 C/P 成交比和持仓比，综合判断市场情绪（看涨/看跌/中性）
   - 分析 Call 和 Put 的成交量对比，判断资金流向

2. **热门标的深度解读**
   - 分析前 5 个最活跃标的的特点、主力合约和可能的市场原因
   - 结合价格区间和合约集中度，判断市场预期

3. **主力合约和价格区间分析**
   - 解读主力价格区间和合约到期日反映的市场预期
   - 识别重要的支撑/阻力位

4. **资金流向和市场情绪**
   - 分析成交量和持仓量的变化趋势
   - 识别可能的机构操作或市场共识

5. **异常和风险提醒**
   - 如果有异常，指出需要特别关注的风险点
   - 提示可能的市场波动因素

6. **交易策略建议**
   - 基于数据提供 2-3 条具体的交易方向建议
   - 标注风险等级和建议持仓周期

请保持分析专业且实用（400-600字），重点突出，适合早晨快速决策。
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
            return f"📊 期权市场日报 {date_str} - {top_ticker} 领涨 | ⚠️ {anomalies_count}个异常"
        else:
            return f"📊 期权市场日报 {date_str} - {top_ticker} 领涨"

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

        # Top 5 表格
        top_5_rows = []
        for i, item in enumerate(data[:5], 1):
            history = item.get('history', {})
            top_5_rows.append(f"""
                <tr>
                    <td>{i}</td>
                    <td><strong>{item['ticker']}</strong></td>
                    <td>{item['total_volume']:,}</td>
                    <td>{item['cp_volume_ratio']:.2f}</td>
                    <td>{item['total_oi']:,}</td>
                    <td>{history.get('appearances', 0)}/10 {history.get('icon', '')}</td>
                </tr>
            """)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #764ba2;
            margin-top: 25px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{
            background: #f0f0f0;
        }}
        .summary {{
            background: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .ai-analysis {{
            background: #f3e5f5;
            padding: 20px;
            border-radius: 5px;
            border-left: 4px solid #764ba2;
            margin: 20px 0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 0.9em;
        }}
        a {{
            color: #667eea;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 期权市场日报</h1>
        <p><strong>日期：</strong>{datetime.now().strftime('%Y年%m月%d日 %A')}</p>

        <div class="summary">
            <h3>📈 市场摘要</h3>
            <ul>
                <li>分析标的总数: <strong>{len(data)}</strong></li>
                <li>检测到异常: <strong>{summary.get('total', 0)}</strong> 个</li>
                <li>Top 1 活跃: <strong>{data[0]['ticker']}</strong> (成交量 {data[0]['total_volume']:,})</li>
            </ul>
        </div>

        <h2>🔝 Top 5 活跃标的</h2>
        <table>
            <thead>
                <tr>
                    <th>排名</th>
                    <th>标的</th>
                    <th>总成交量</th>
                    <th>C/P比</th>
                    <th>持仓量</th>
                    <th>10日活跃度</th>
                </tr>
            </thead>
            <tbody>
                {''.join(top_5_rows)}
            </tbody>
        </table>

        <div class="ai-analysis">
            <h2>🤖 AI 市场分析</h2>
            {analysis_html}
        </div>

        <div class="footer">
            <p>
                📊 <a href="https://onlinefchen.github.io/options-anomaly-detector/">查看完整报告</a>
                | 📚 <a href="https://github.com/onlinefchen/options-anomaly-detector">GitHub 项目</a>
            </p>
            <p>此邮件由自动化系统生成 | AI 分析仅供参考，不构成投资建议</p>
        </div>
    </div>
</body>
</html>
"""
        return html
