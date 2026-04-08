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
                        'top_3_oi': item.get('top_3_oi', [])[:3],
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

            # 调用 GPT-5（2025年8月发布的最新最强模型）
            response = self.client.chat.completions.create(
                model="gpt-5",  # GPT-5 - OpenAI最新旗舰模型（2025年8月发布）
                messages=[
                    {
                        "role": "system",
                        "content": """你是一位资深的华尔街期权交易分析师和基金经理，拥有15年机构交易经验。你管理着一支10亿美元的对冲基金，专注于期权策略。

你的核心竞争力：
1. 深度基本面分析 - 精通财务报表、现金流分析、ROE/ROIC等核心指标，能识别价值陷阱和隐藏宝藏
2. 市场新闻敏感度 - 实时追踪财报电话会议、监管文件、管理层动态、行业趋势
3. 期权流动解读 - 能从期权链数据反推机构意图、对冲策略、市场预期
4. 宏观视野 - 深刻理解美联储政策、地缘政治、供应链、行业周期对标的的影响
5. 风险管理大师 - 精确量化风险收益比，识别尾部风险和黑天鹅

你的分析哲学：
- 提供深度洞察，而非表面数据重复
- 解释"为什么会这样"和"接下来会怎样"
- 每个观点都有基本面+期权信号+催化剂的三重验证
- 优先寻找市场错误定价的机会
- 专注asymmetric risk/reward（不对称风险回报）
- 诚实指出不确定性和风险

重要：请写出深度的、有见地的分析。不要吝啬笔墨，充分展开你的论述。"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
                # GPT-5 只支持 temperature=1（默认值），移除自定义temperature参数
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
            top_contracts = item.get('top_3_oi', [])

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

            # 添加新指标
            avg_trade_size = item.get('avg_trade_size', 0)
            leap_cp = item.get('leap_cp_ratio', 0)

            # Format Top 3 LEAP contracts
            leap_contracts = item.get('top_3_leap_oi', [])
            leap_contracts_list = []
            for j, contract in enumerate(leap_contracts[:3], 1):
                expiry = contract.get('expiry', '')
                if expiry:
                    expiry = expiry.replace('-', '')[-6:]
                contract_type = contract.get('type', '')[0].upper() if contract.get('type') else 'X'
                strike = int(contract.get('strike', 0))
                oi = contract.get('oi', 0)
                pct = contract.get('percentage', 0)
                leap_contract_detail = f"{expiry}{contract_type}{strike} (OI: {oi:,}, {pct:.1f}%)"
                leap_contracts_list.append(leap_contract_detail)
            leap_contracts_str = "\n     " + "\n     ".join(leap_contracts_list) if leap_contracts_list else " N/A"

            detail = (
                f"{i}. **{item['ticker']}**:\n"
                f"   - Total Volume: {item['total_volume']:,} | Total OI: {item['total_oi']:,}\n"
                f"   - Volume: Call {item['call_volume']:,} / Put {item['put_volume']:,} "
                f"(C/P Ratio {item['cp_volume_ratio']:.2f})\n"
                f"   - OI: Call {item['call_oi']:,} / Put {item['put_oi']:,} "
                f"(C/P Ratio {item['cp_oi_ratio']:.2f})\n"
                f"   - **Avg Trade Size: {avg_trade_size:.1f}** "
                f"({'机构主导' if avg_trade_size > 15 else '散户为主' if avg_trade_size < 8 else '混合参与'})\n"
                f"   - **LEAP C/P: {leap_cp:.2f}** "
                f"({'长期看多' if leap_cp > 1.2 else '长期看空' if leap_cp < 0.8 else '中性'})\n"
                f"   - Contracts: {item['contracts_count']}\n"
                f"   - Strike Concentration: {strike_info}\n"
                f"   - Top 3 Contracts:{contracts_str}\n"
                f"   - Top 3 LEAP Contracts:{leap_contracts_str}"
            )
            tickers_detail.append(detail)

        tickers_str = "\n\n".join(tickers_detail)

        anomalies_str = ""
        if market_summary['key_anomalies']:
            anomalies_str = "\n\n# 主要异常\n" + "\n".join([
                f"- **{a['ticker']}**: {a['description']} (严重程度: {a['severity']})"
                for a in market_summary['key_anomalies']
            ])

        prompt = f"""你是一位资深期权交易分析师。以下是美股期权市场数据，请基于你的市场知识、新闻认知、宏观政策和市场情绪提供深度洞察和操作建议。

# 数据字段说明
表格中的关键指标含义：
- **Rank**: 按成交量排名
- **Ticker**: 标的代码
- **Total Volume**: 期权总成交量（单位：万手）
- **C/P Volume**: 看涨/看跌期权成交量比例（>1偏多，<1偏空）
- **Avg Trade Size**: 平均每笔成交手数（成交量/成交笔数），数值越大说明机构参与度越高
- **LEAP C/P**: 长期期权（3个月以上）的看涨/看跌比例，反映长期市场预期
- **Total OI**: 期权总持仓量（单位：万手）
- **C/P OI**: 看涨/看跌期权持仓量比例
- **Top 3 Contracts**: 持仓量最大的3个期权合约（格式：到期日+类型+行权价）
- **Top 3 LEAP**: 3个月以后到期的持仓量最大的3个期权合约，反映长期市场定位

# 原始数据（仅供参考，不要在分析中重复这些数字）
- 总标的数: {market_summary['total_tickers']}
- 异常: {market_summary['anomalies_count']} 个

# Top 15 活跃标的数据
{tickers_str}

---

**分析要求（中文，Markdown）：**

**重要分析维度**:
- **宏观政策背景**: 结合当前美联储货币政策、利率环境、地缘政治、经济数据（CPI、就业等）
- **市场情绪**: 从Avg Trade Size看机构vs散户参与度，从LEAP C/P看长期预期
- **板块轮动**: 分析哪些板块在领涨/领跌，资金流向哪里
- **机构意图**: 从OI分布、Top Contracts看机构在布局什么策略
- **深度洞察**: WHY（为什么）比 WHAT（是什么）更重要
- **操作建议**: 明确指出应该关注哪些标的，如何操作（正股/期权/观察）

---

## 📊 市场环境与情绪综述

请先简要分析（200-300字）：
1. **当前宏观环境**: 美联储政策、经济数据、地缘政治对市场的影响
2. **整体市场情绪**: 从数据看机构和散户的参与度、多空情绪
3. **主要资金流向**: 哪些板块在吸金，哪些在流出
4. **当前操作策略**: 在这个市场环境下，应该采取什么样的整体策略（进攻/防御/观察）

---

## 💡 5个最值得操作的交易建议

**请务必结合上述市场环境分析给出建议！**

**重要：正股 vs 期权的选择原则**
不要全部推荐期权！请根据以下原则灵活选择：

**适合买正股的情况**:
- 长期价值投资机会，估值严重低估
- 股息收益率高，适合长期持有
- 波动率较低，期权权利金过高不划算
- 趋势明确但时间窗口不确定，不适合期权时间衰减
- 风险承受能力低的投资者

**适合买期权的情况**:
- 有明确催化剂和时间窗口（财报、FDA批准等）
- 需要杠杆放大收益
- 隐含波动率相对较低，期权权利金合理
- 趋势明确且时间窗口明确
- 想控制风险敞口（期权最大损失=权利金）

**选择标准**:
- 结合基本面 + 期权信号 + 市场时机
- 不要只看成交量，选择有明确催化剂的标的
- 优先选择风险收益比最优的机会
- **只分析个股，不要推荐任何ETF**（如SPY、QQQ、GLD、XLE等都不要）
- **目标：5个建议中应该包含2-3个正股，2-3个期权，灵活搭配**

每个建议请充分展开，包含：

**交易 #X: [标的] - [核心投资论点]**

- **操作**: [正股/期权具体合约]
  * **为什么选择正股/期权**: 清楚解释为什么这个标的更适合买正股或期权

- **深度分析**:
  * **基本面支撑**:
    - 公司财务状况和业务动态（用具体数据说话）
    - 与行业/竞争对手的对比
    - 管理层质量和战略
  * **期权信号解读**:
    - 主力合约的选择反映了什么？
    - OI分布告诉我们什么？
    - 机构可能在布局什么策略？
  * **催化剂时间表**:
    - 近期有什么事件会推动？
    - 时间窗口是什么？
  * **风险因素**:
    - 可能出错的地方
    - 如何应对

- **具体交易计划**:
  * 入场: [价位和时机]
  * 目标: [第一目标/第二目标]
  * 止损: [明确止损位]
  * 仓位建议: [建议投入资金比例]
  * 风险收益比: [计算的R/R]

- **风险评级**: [低/中/高]，**持仓周期**: [短期/中期]

例如深度建议（正股示例）：
**交易 #1: WMT 正股 - 防御性价值投资，长期持有收息**

- **操作**: 买入 WMT 正股
  * **为什么选择正股**:
    - 股息收益率 1.5%，适合长期持有
    - 防御性标的，波动率低，期权权利金偏贵
    - 没有明确短期催化剂，长期价值投资更适合正股
    - 避免期权时间衰减，长期趋势向上

- **深度分析**:
  * **基本面支撑**:
    - Q3财报：营收$1600亿，同比+5.2%。线上销售增长13%，占比达到15%。
    - FCF $250亿/年，充沛现金流支撑持续回购和分红。
    - 净利润率3.5%虽不高，但规模效应和全球布局带来护城河。
    - 管理层注重股东回报，过去5年平均分红增长8%/年。
  * **市场地位**:
    - 全球最大零售商，美国市占率23%，护城河深厚。
    - 供应链优势明显，通胀环境下议价能力强。
  * **催化剂**:
    - 年底购物季（Q4传统旺季）
    - 线上业务持续增长
    - 长期：墨西哥/印度市场扩张
  * **风险**:
    - 亚马逊竞争
    - 人力成本上升
    - 宏观经济衰退影响消费

- **具体交易计划**:
  * 入场: $58-60区间分批买入
  * 目标: 长期持有，$70+ (3年目标)
  * 止损: $52 (-13%)，基本面恶化才离场
  * 仓位建议: 10-15%账户资金（可以重仓防御股）
  * 预期回报: 年化8-12% (资本利得+股息)

- **风险评级**: 低，**持仓周期**: 1-3年

---

例如深度建议（期权示例）：
**交易 #2: NVDA Call - 押注AI浪潮，有明确催化剂**

- **操作**: 买入 NVDA 2025-11-21 Call $450
  * **为什么选择期权**:
    - 11月20日财报是明确催化剂，时间窗口清晰
    - AI主题热度高，财报超预期可能带来爆发
    - 需要杠杆放大收益（期权5-10倍杠杆）
    - 控制风险：最多损失权利金，不会被爆仓

- **深度分析**:
  * **基本面支撑**:
    - Q3财报：投行收入$18.5B (+28% YoY)，M&A管道强劲。交易收入虽下滑但在预期内。
    - ROE 15.2%领先同业(高盛13.8%，BAC 12.1%)，显示盈利质量优异。
    - 资本充足率14.3%，有提高股息的空间。管理层在电话会议暗示Q4可能宣布。
    - 商业地产敞口$500B需关注，但管理层表示已充分计提准备金。
  * **期权信号解读**:
    - **Avg Trade Size: 18.5** - 机构主导，说明大资金在积极建仓
    - **LEAP C/P: 1.35** - 长期看多情绪强烈，机构在布局3个月以上的call
    - Call OI在$600-610高度集中，说明机构在这个价位建立看涨仓位。
    - Put OI集中在$580，是典型的保护性put，说明机构在做有保护的看涨。
    - Dec到期的call明显多于Nov，说明机构预期年底前有催化剂，但不急于赌短期。
    - Put/Call OI比0.52，远低于历史均值0.75，显示看涨共识强。
  * **催化剂时间表**:
    - 11月FOMC会议(11/1)：市场预期暂停加息，利好银行NIM
    - 年底股息宣布窗口(12月中)：可能提高股息10-15%
    - Q4财报季前的预期升温
  * **风险因素**:
    - 商业地产如果爆雷会冲击估值
    - 如果美联储再次加息会打压银行股
    - 经济衰退风险会压制信贷需求

- **具体交易计划**:
  * 入场: $605-607区间，等回调建仓
  * 第一目标: $620 (+2.1%)，部分止盈
  * 第二目标: $635 (+4.6%)，突破历史高位
  * 止损: $590 (-2.5%)，跌破支撑位果断离场
  * 仓位建议: 3-5%账户资金
  * 风险收益比: 1:2 (考虑到期权杠杆，实际更高)

- **风险评级**: 中等，**持仓周期**: 1-2个月

---

请充分展开每个交易建议，提供足够的信息支持投资决策。总字数不限，追求深度和实用性。
"""

        return prompt

    def generate_email_subject(self, data: List[Dict], anomalies_count: int, csv_date: str = None) -> str:
        """
        生成邮件主题

        Args:
            data: 市场数据
            anomalies_count: 异常数量
            csv_date: CSV文件日期

        Returns:
            邮件主题
        """
        from datetime import datetime

        # 使用CSV日期，如果没有则使用当前日期
        if csv_date and csv_date != 'Unknown':
            date_str = csv_date
        else:
            date_str = datetime.now().strftime('%Y-%m-%d')

        return f"{date_str}交易日 盘后数据分析"

    def format_for_email(self, analysis: str, data: List[Dict], summary: Dict, csv_date: str = None) -> str:
        """
        格式化为邮件内容（HTML）

        Args:
            analysis: AI 分析结果
            data: 市场数据
            summary: 异常摘要
            csv_date: CSV文件日期

        Returns:
            HTML 格式的邮件内容
        """
        from datetime import datetime
        import markdown

        # 使用CSV日期，如果没有则使用当前日期
        if csv_date and csv_date != 'Unknown':
            date_str = csv_date
            # 尝试解析CSV日期以获取星期几
            try:
                date_obj = datetime.strptime(csv_date, '%Y-%m-%d')
                date_with_weekday = date_obj.strftime('%Y-%m-%d %A')
            except:
                date_with_weekday = csv_date
        else:
            date_str = datetime.now().strftime('%Y-%m-%d')
            date_with_weekday = datetime.now().strftime('%Y-%m-%d %A')

        # 转换 Markdown 到 HTML（如果有内容）
        analysis_html = markdown.markdown(analysis) if analysis and analysis.strip() else ""

        # Filter and prepare data same as HTML report's "Stocks & ETFs - Top 25"
        # 1. Filter out SPXW, VIX
        filtered_data = [d for d in data if d['ticker'] not in ['SPXW', 'VIX']]

        # 2. Exclude market indices (SPY, QQQ, IWM, SPX)
        INDEX_ETFS = {'SPY', 'QQQ', 'IWM', 'SPX'}
        stock_data = [d for d in filtered_data if d['ticker'] not in INDEX_ETFS]

        # 3. Sort by volume and take top 25
        sorted_stock_data = sorted(stock_data, key=lambda x: x['total_volume'], reverse=True)[:25]

        # Top 25 详细表格
        top_25_rows = []
        for i, item in enumerate(sorted_stock_data, 1):
            # Format volume and OI in 万 (W) with 2 decimal places
            volume_w = item['total_volume'] / 10000
            oi_w = item['total_oi'] / 10000

            # Avg Trade Size
            avg_trade_size = item.get('avg_trade_size', 0)

            # LEAP C/P ratio
            leap_cp = item.get('leap_cp_ratio', 0)
            leap_cp_text = f"{leap_cp:.2f}" if leap_cp else "-"

            # Top 3 Volume (volume-based, from CSV)
            top3_volume_text = ""
            current_price = item.get('current_price')
            if current_price:
                top3_volume_text += f"Current: ${current_price:.2f}<br>"

            for j, contract in enumerate(item.get('top_3_contracts_volume', [])[:3], 1):
                ticker = contract.get('ticker', 'N/A')
                volume_k = contract.get('volume', 0) / 1000
                pct = contract.get('percentage', 0)
                top3_volume_text += f"{j}. {ticker} {volume_k:.0f}K ({pct:.1f}%)<br>"

            if not top3_volume_text or not item.get('top_3_contracts_volume'):
                top3_volume_text = "N/A"

            # Top 3 Volume Leap (volume-based, 3+ months out, from CSV)
            top3_leap_volume_text = ""
            if current_price:
                top3_leap_volume_text += f"Current: ${current_price:.2f}<br>"

            for j, contract in enumerate(item.get('top_3_leap_volume', [])[:3], 1):
                ticker = contract.get('ticker', 'N/A')
                volume_k = contract.get('volume', 0) / 1000
                pct = contract.get('percentage', 0)
                top3_leap_volume_text += f"{j}. {ticker} {volume_k:.0f}K ({pct:.1f}%)<br>"

            if not top3_leap_volume_text or not item.get('top_3_leap_volume'):
                top3_leap_volume_text = "N/A"

            # Top 3 OI (OI-based, from API for recent post-market data)
            top3_oi_text = ""
            if current_price:
                top3_oi_text += f"Current: ${current_price:.2f}<br>"

            for j, contract in enumerate(item.get('top_3_oi', [])[:3], 1):
                ticker = contract.get('ticker', 'N/A')
                oi_k = contract.get('oi', 0) / 1000
                pct = contract.get('percentage', 0)
                top3_oi_text += f"{j}. {ticker} {oi_k:.0f}K ({pct:.1f}%)<br>"

            if not top3_oi_text or not item.get('top_3_oi'):
                top3_oi_text = "N/A"

            # History
            history = item.get('history', {})
            appearances = history.get('appearances', 0)
            icon = history.get('icon', '[NEW]')
            rank_change = history.get('rank_change')

            if rank_change is None or rank_change == 0:
                rank_symbol = '-'
            elif rank_change > 0:
                rank_symbol = f'+{rank_change}'
            else:
                rank_symbol = f'{rank_change}'

            top_25_rows.append(f"""
                <tr>
                    <td style="text-align: center;">{i}</td>
                    <td><strong>{item['ticker']}</strong></td>
                    <td style="text-align: right;">{volume_w:.2f}W</td>
                    <td style="text-align: center;">{item['cp_volume_ratio']:.2f}</td>
                    <td style="text-align: center;">{avg_trade_size:.1f}</td>
                    <td style="text-align: center;">{leap_cp_text}</td>
                    <td style="text-align: right;">{oi_w:.2f}W</td>
                    <td style="text-align: center;">{item.get('cp_oi_ratio', 0):.2f}</td>
                    <td style="font-size: 11px; line-height: 1.4;">{top3_volume_text}</td>
                    <td style="font-size: 11px; line-height: 1.4;">{top3_leap_volume_text}</td>
                    <td style="font-size: 11px; line-height: 1.4;">{top3_oi_text}</td>
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
            line-height: 1.4;
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
            padding: 8px 8px;
            text-align: left;
            font-weight: 600;
            border-bottom: 1px solid #d2d2d7;
        }}
        td {{
            padding: 8px 8px;
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
        <div class="date">{date_with_weekday}</div>

        <div class="summary">
            <div class="summary-item">分析标的数: <strong>{len(data)}</strong></div>
            <div class="summary-item">检测异常: <strong>{summary.get('total', 0)}</strong></div>
            <div class="summary-item">最活跃: <strong>{sorted_stock_data[0]['ticker']}</strong> (成交量 {sorted_stock_data[0]['total_volume']:,})</div>
        </div>

        {f'<div class="ai-analysis"><h2>🤖 AI 市场分析</h2>{analysis_html}</div>' if analysis_html else ''}

        <h2>Stocks & ETFs - Top 25</h2>
        <table>
            <thead>
                <tr>
                    <th style="text-align: center;">排名</th>
                    <th>标的</th>
                    <th style="text-align: right;">成交量</th>
                    <th style="text-align: center;">C/P Volume</th>
                    <th style="text-align: center;">Avg Size</th>
                    <th style="text-align: center;">LEAP C/P</th>
                    <th style="text-align: right;">持仓量</th>
                    <th style="text-align: center;">C/P OI</th>
                    <th>Top 3 Volume</th>
                    <th>Top 3 Volume Leap</th>
                    <th>Top 3 OI</th>
                </tr>
            </thead>
            <tbody>
                {''.join(top_25_rows)}
            </tbody>
        </table>

        <h2 style="font-size: 16px; margin-top: 40px;">📊 表格列说明</h2>
        <table style="font-size: 12px; margin-top: 10px;">
            <tbody>
                <tr>
                    <td style="border: none; padding: 4px 8px;"><strong>Rank</strong></td>
                    <td style="border: none; padding: 4px 8px;">按成交量排名</td>
                </tr>
                <tr>
                    <td style="border: none; padding: 4px 8px;"><strong>Ticker</strong></td>
                    <td style="border: none; padding: 4px 8px;">标的代码</td>
                </tr>
                <tr>
                    <td style="border: none; padding: 4px 8px;"><strong>Total Volume</strong></td>
                    <td style="border: none; padding: 4px 8px;">期权总成交量（单位：万手）</td>
                </tr>
                <tr>
                    <td style="border: none; padding: 4px 8px;"><strong>C/P Volume</strong></td>
                    <td style="border: none; padding: 4px 8px;">看涨/看跌期权成交量比例</td>
                </tr>
                <tr>
                    <td style="border: none; padding: 4px 8px;"><strong>Avg Trade Size</strong></td>
                    <td style="border: none; padding: 4px 8px;">平均每笔成交手数（成交量/成交笔数），数值越大说明机构参与度越高</td>
                </tr>
                <tr>
                    <td style="border: none; padding: 4px 8px;"><strong>LEAP C/P</strong></td>
                    <td style="border: none; padding: 4px 8px;">长期期权（3个月以上）的看涨/看跌比例，反映长期市场预期</td>
                </tr>
                <tr>
                    <td style="border: none; padding: 4px 8px;"><strong>Total OI</strong></td>
                    <td style="border: none; padding: 4px 8px;">期权总持仓量（单位：万手）</td>
                </tr>
                <tr>
                    <td style="border: none; padding: 4px 8px;"><strong>C/P OI</strong></td>
                    <td style="border: none; padding: 4px 8px;">看涨/看跌期权持仓量比例</td>
                </tr>
                <tr>
                    <td style="border: none; padding: 4px 8px;"><strong>Top 3 Contracts</strong></td>
                    <td style="border: none; padding: 4px 8px;">持仓量最大的3个期权合约（格式：到期日+类型+行权价）</td>
                </tr>
                <tr>
                    <td style="border: none; padding: 4px 8px;"><strong>Top 3 Leap</strong></td>
                    <td style="border: none; padding: 4px 8px;">3个月以后到期的持仓量最大的3个期权合约，反映长期市场定位</td>
                </tr>
            </tbody>
        </table>

        <div class="footer">
            <div><a href="https://devfchen.github.io/options-anomaly-detector/">查看完整报告</a> | <a href="https://github.com/devfchen/options-anomaly-detector">GitHub</a></div>
            <div style="margin-top: 10px;">自动化报告 - 仅供参考</div>
        </div>
    </div>
</body>
</html>
"""
        return html

    def analyze_macro_outlook(
        self,
        indices_data: List[Dict],
        max_tokens: int = 1500
    ) -> Optional[str]:
        """
        Analyze macro economic outlook using SPY/QQQ/IWM data

        Args:
            indices_data: Data for SPY, QQQ, IWM
            max_tokens: Maximum tokens to generate

        Returns:
            AI-generated macro analysis (Markdown format)
        """
        if not self.is_available():
            return None

        try:
            # Prepare indices summary
            indices_summary = []
            for item in indices_data:
                indices_summary.append({
                    'ticker': item['ticker'],
                    'total_volume': item['total_volume'],
                    'put_volume': item.get('put_volume', 0),
                    'call_volume': item.get('call_volume', 0),
                    'cp_volume_ratio': item['cp_volume_ratio'],
                    'total_oi': item['total_oi'],
                    'put_oi': item.get('put_oi', 0),
                    'call_oi': item.get('call_oi', 0),
                    'cp_oi_ratio': item['cp_oi_ratio'],
                    'top_3_oi': item.get('top_3_oi', [])[:3],
                    'strike_concentration': item.get('strike_concentration', {})
                })

            # Build prompt
            prompt = self._build_macro_prompt(indices_summary)

            # Call GPT-4o
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a senior macro economist and market strategist with 20+ years experience at top hedge funds and central banks.

Your expertise:
1. Federal Reserve policy analysis - deeply understand rate decisions, QT/QE, yield curve dynamics
2. Global macro trends - geopolitical risks, supply chains, energy markets, currency flows
3. Market structure - institutional positioning, systematic flows, volatility regimes
4. Economic cycles - recession indicators, credit markets, employment data
5. Options market interpretation - what major indices options tell us about institutional sentiment

Your analysis philosophy:
- Connect the dots between macro conditions and market behavior
- Explain the "why" behind current market positioning
- Identify key risks and opportunities
- Be honest about uncertainties
- Focus on what matters most for investors

Write concise but insightful analysis in English."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=max_tokens
            )

            analysis = response.choices[0].message.content
            return analysis

        except Exception as e:
            print(f"❌ Macro analysis failed: {e}")
            return None

    def _build_macro_prompt(self, indices_summary: List[Dict]) -> str:
        """
        Build macro analysis prompt

        Args:
            indices_summary: Summary of SPY/QQQ/IWM data

        Returns:
            Prompt string
        """
        # Build detailed indices data
        indices_detail = []
        for item in indices_summary:
            strike_conc = item.get('strike_concentration', {})
            top_contracts = item.get('top_3_oi', [])

            contracts_str = ""
            if top_contracts:
                contracts_list = []
                for c in top_contracts:
                    contract_detail = (
                        f"{c.get('type', 'N/A').upper()} ${c.get('strike', 'N/A')} "
                        f"Exp {c.get('expiry', 'N/A')} "
                        f"(OI {c.get('oi', 0):,}, {c.get('percentage', 0):.1f}%)"
                    )
                    contracts_list.append(contract_detail)
                contracts_str = "\n     " + "\n     ".join(contracts_list)

            detail = f"""
{item['ticker']}:
  Volume: {item['total_volume']:,} (Put: {item['put_volume']:,}, Call: {item['call_volume']:,})
  C/P Volume Ratio: {item['cp_volume_ratio']:.2f}
  Open Interest: {item['total_oi']:,} (Put: {item['put_oi']:,}, Call: {item['call_oi']:,})
  C/P OI Ratio: {item['cp_oi_ratio']:.2f}
  Strike Concentration: {strike_conc.get('range', 'N/A')} ({strike_conc.get('percentage', 0):.1f}%)
  Top 3 Contracts:{contracts_str}
"""
            indices_detail.append(detail)

        prompt = f"""Analyze the current macro market environment based on these major indices options data:

{''.join(indices_detail)}

Please provide:

**Market Sentiment & Positioning**
- What does the C/P ratio tell us about institutional sentiment?
- How are smart money positioning (based on OI and top contracts)?
- Any unusual patterns suggesting hedging or directional bets?

**Macro Outlook**
- What's the current macro environment (Fed policy, inflation, growth)?
- Key risks and opportunities in the near term
- What should investors watch for?

**Key Takeaways**
- 3-5 bullet points summarizing the most important insights

Keep it concise, actionable, and focused on what matters most."""

        return prompt
