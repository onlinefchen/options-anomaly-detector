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
                        "content": """你是一位资深的华尔街期权交易分析师和基金经理，拥有15年机构交易经验。

你的专长：
1. 深度基本面分析 - 解读公司财务、现金流、业务模式
2. 市场新闻敏感度 - 掌握最新财报、政策、国际动态
3. 期权流动分析 - 识别机构定位和市场共识
4. 风险管理 - 关注宏观风险和催化剂

你的分析风格：
- 提供洞察而非数据重复（数字已在表格中）
- 解释"为什么"比"是什么"更重要
- 结合基本面+技术面+市场情绪三重验证
- 选择有明确催化剂的标的，而非简单最活跃的
- 专注风险调整后的回报"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000,  # 增加token支持更详细的深度分析
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

        prompt = f"""你是一位资深期权交易分析师。以下是美股期权市场数据，请基于你的市场知识、新闻认知和基本面分析提供深度洞察。

# 原始数据（仅供参考，不要在分析中重复这些数字）
- 总标的数: {market_summary['total_tickers']}
- 异常: {market_summary['anomalies_count']} 个

# Top 15 活跃标的数据
{tickers_str}

---

**分析要求（中文，Markdown）：**

**重要**:
- 不要简单重复数据中的数字（如成交量、C/P比等已在表格中）
- 提供深度洞察：WHY（为什么）比 WHAT（是什么）更重要
- 结合公司基本面、财务状况、业务模式
- 结合最近的市场新闻、财报季、国际动态
- 分析机构意图和市场共识

## 1. 市场整体格局 (150字)
- 当前市场主题是什么？（科技/金融/能源板块轮动？防御性？）
- 最近国际市场发生了什么影响美股的事件？
- 从期权数据看，机构在押注什么？（VIX、防御性、成长股？）

## 2. 板块和标的深度解读 (200字)
选择 3-4 个最有代表性的标的，深入分析：
- **业务基本面**: 这些公司最近有什么财报/业务动态？
- **财务健康度**: 现金流、负债情况如何？
- **市场新闻**: 最近有什么重大新闻影响？
- **期权信号含义**: 主力合约的选择反映了什么市场预期？

例如：
*WMT: 零售巨头，防御性强。最近财报显示电商业务增长强劲，现金流充裕。期权数据显示Call集中在$60，反映市场预期年底购物季表现。机构在押注稳健增长而非爆发。*

## 3. 风险与机会 (100字)
- 当前最大的宏观风险是什么？（通胀、利率、地缘政治）
- 哪些板块有被低估的机会？
- 需要警惕哪些潜在黑天鹅？

## 4. 5个最值得操作的交易建议

**选择标准**:
- 结合基本面 + 期权信号 + 市场时机
- 不要只看成交量，选择有明确催化剂的标的
- 优先选择风险收益比最优的机会

每个建议格式：
**交易 #X: [标的] - [一句话核心逻辑]**
- 操作: [正股/期权具体合约]
- 核心理由:
  * 基本面: [财务/业务/新闻]
  * 期权信号: [主力合约的含义]
  * 催化剂: [近期什么事件会推动]
- 入场/目标/止损
- 风险: [低/中/高]，周期: [1-2周/1-2月]

例如：
**交易 #1: JPM - 押注金融板块复苏**
- 操作: 买入 JPM 2025-11-29 Call $610
- 核心理由:
  * 基本面: 大摩Q3财报超预期，投行业务回暖。JPM作为行业龙头，有望受益于IPO市场复苏。
  * 期权信号: Call OI集中$600-610，机构在押注突破历史高位。
  * 催化剂: 下周美联储会议，市场预期利率政策转向利好银行股。
- 入场: 当前，目标 $620-630，止损 $595
- 风险: 中，周期: 2-3周

总字数 600-800字，深度而非重复数据。
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
            return f"期权市场日报 {date_str} - {top_ticker} 领涨 | {anomalies_count}个异常"
        else:
            return f"期权市场日报 {date_str} - {top_ticker} 领涨"

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
        <h1>期权市场日报</h1>
        <div class="date">{datetime.now().strftime('%Y-%m-%d %A')}</div>

        <div class="summary">
            <div class="summary-item">分析标的数: <strong>{len(data)}</strong></div>
            <div class="summary-item">检测异常: <strong>{summary.get('total', 0)}</strong></div>
            <div class="summary-item">最活跃: <strong>{data[0]['ticker']}</strong> (成交量 {data[0]['total_volume']:,})</div>
        </div>

        <h2>Top 5 活跃标的</h2>
        <table>
            <thead>
                <tr>
                    <th>排名</th>
                    <th>标的</th>
                    <th>成交量</th>
                    <th>C/P比</th>
                    <th>持仓量</th>
                </tr>
            </thead>
            <tbody>
                {''.join(top_5_rows)}
            </tbody>
        </table>

        <h2>AI 市场分析</h2>
        <div class="ai-analysis">
            {analysis_html}
        </div>

        <div class="footer">
            <div><a href="https://onlinefchen.github.io/options-anomaly-detector/">查看完整报告</a> | <a href="https://github.com/onlinefchen/options-anomaly-detector">GitHub</a></div>
            <div style="margin-top: 10px;">自动化报告 - 仅供参考</div>
        </div>
    </div>
</body>
</html>
"""
        return html
