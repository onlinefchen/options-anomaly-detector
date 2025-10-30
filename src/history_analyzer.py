#!/usr/bin/env python3
"""
History Analyzer Module
Analyzes historical data to track ticker activity over time
"""
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class HistoryAnalyzer:
    """分析历史数据，统计标的活跃度"""

    def __init__(self, output_dir='output', lookback_days=10):
        """
        Initialize history analyzer

        Args:
            output_dir: Directory containing historical JSON files
            lookback_days: Number of trading days to look back
        """
        self.output_dir = output_dir
        self.lookback_days = lookback_days

    def get_trading_days(self, end_date: Optional[datetime] = None, count: int = 10) -> List[str]:
        """
        获取过去N个交易日的日期列表

        只统计有JSON文件的日期（实际交易日）

        Args:
            end_date: End date for lookback (defaults to today)
            count: Number of trading days to retrieve

        Returns:
            List of date strings in YYYY-MM-DD format, sorted oldest to newest
        """
        if end_date is None:
            end_date = datetime.now()

        trading_days = []
        current = end_date
        max_lookback = 30  # 最多向前查找30天
        days_checked = 0

        while len(trading_days) < count and days_checked < max_lookback:
            date_str = current.strftime('%Y-%m-%d')
            json_file = os.path.join(self.output_dir, f"{date_str}.json")

            # 只统计存在JSON文件的日期
            if os.path.exists(json_file):
                trading_days.append(date_str)

            current -= timedelta(days=1)
            days_checked += 1

        return trading_days[::-1]  # 从旧到新排序

    def load_historical_data(self, dates: List[str]) -> Dict[str, List[Dict]]:
        """
        加载历史数据

        Args:
            dates: List of date strings

        Returns:
            Dict mapping date to list of ticker data
        """
        history = {}

        for date in dates:
            json_file = os.path.join(self.output_dir, f"{date}.json")

            if os.path.exists(json_file):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # 只取Top 30的数据
                        history[date] = data.get('data', [])[:30]
                except Exception as e:
                    print(f"  ⚠️  Failed to load {date}: {e}")

        return history

    def analyze_ticker_history(self, ticker: str, history: Dict[str, List[Dict]]) -> Dict:
        """
        分析单个ticker的历史表现

        Args:
            ticker: Ticker symbol
            history: Historical data dict

        Returns:
            Dict with historical statistics
        """
        appearances = []
        ranks = []

        # 遍历历史数据，找到该ticker的出现记录
        for date in sorted(history.keys()):
            data = history[date]
            for idx, item in enumerate(data, 1):
                if item['ticker'] == ticker:
                    appearances.append(date)
                    ranks.append(idx)
                    break

        total_days = len(history)

        # 如果没有历史记录，返回新标的信息
        if not appearances:
            return {
                'appearances': 0,
                'appearance_rate': 0.0,
                'avg_rank': None,
                'best_rank': None,
                'worst_rank': None,
                'today_rank': None,
                'rank_change': None,
                'trend': 'new',
                'streak': 0,
                'icon': '🆕'
            }

        appear_count = len(appearances)
        avg_rank = sum(ranks) / len(ranks)

        # 计算排名变化（今天 vs 昨天）
        rank_change = 0
        if len(ranks) >= 2:
            rank_change = ranks[-2] - ranks[-1]  # 正数=排名上升（数字变小）

        # 判断趋势
        trend = self._determine_trend(ranks)

        # 计算连续出现天数
        streak = 0
        for date in reversed(sorted(history.keys())):
            if date in appearances:
                streak += 1
            else:
                break

        # 选择图标
        icon = self._get_icon(appear_count, total_days)

        return {
            'appearances': appear_count,
            'appearance_rate': round(appear_count / total_days * 100, 1),
            'avg_rank': round(avg_rank, 1),
            'best_rank': min(ranks),
            'worst_rank': max(ranks),
            'today_rank': ranks[-1],
            'rank_change': rank_change,
            'trend': trend,
            'streak': streak,
            'icon': icon
        }

    def _determine_trend(self, ranks: List[int]) -> str:
        """
        判断排名趋势

        Args:
            ranks: List of historical ranks

        Returns:
            'rising', 'falling', or 'stable'
        """
        if len(ranks) < 3:
            return 'stable'

        # 比较最近3天和之前的平均排名
        recent_avg = sum(ranks[-3:]) / 3
        earlier_ranks = ranks[:-3]

        if not earlier_ranks:
            return 'stable'

        earlier_avg = sum(earlier_ranks) / len(earlier_ranks)

        # 排名数字变小 = 排名上升
        if recent_avg < earlier_avg - 2:
            return 'rising'
        elif recent_avg > earlier_avg + 2:
            return 'falling'
        else:
            return 'stable'

    def _get_icon(self, appearances: int, total_days: int) -> str:
        """
        根据出现次数选择图标

        Args:
            appearances: Number of appearances
            total_days: Total days analyzed

        Returns:
            Icon string
        """
        rate = appearances / total_days if total_days > 0 else 0

        if rate >= 0.9:
            return '🔥'  # 常驻榜单
        elif rate >= 0.6:
            return '🌟'  # 活跃标的
        elif rate >= 0.3:
            return '⚡'  # 偶尔出现
        else:
            return '🆕'  # 新上榜

    def enrich_data_with_history(self, current_data: List[Dict]) -> List[Dict]:
        """
        给当前数据添加历史统计信息

        Args:
            current_data: Current day's data

        Returns:
            Enriched data with history field
        """
        # 获取过去N个交易日
        trading_days = self.get_trading_days(count=self.lookback_days)

        if not trading_days:
            print("  ⚠️  No historical data found")
            # 所有标的标记为新上榜
            for item in current_data:
                item['history'] = {
                    'appearances': 0,
                    'appearance_rate': 0.0,
                    'trend': 'new',
                    'icon': '🆕'
                }
            return current_data

        print(f"  ✓ Found {len(trading_days)} trading days of historical data")
        print(f"    Date range: {trading_days[0]} to {trading_days[-1]}")

        # 加载历史数据
        history = self.load_historical_data(trading_days)
        print(f"  ✓ Loaded data for {len(history)} days")

        # 为每个ticker添加历史统计
        for item in current_data:
            ticker = item['ticker']
            item['history'] = self.analyze_ticker_history(ticker, history)

        return current_data
