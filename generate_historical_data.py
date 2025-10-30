#!/usr/bin/env python3
"""
历史数据生成工具
用于生成指定日期或日期区间的模拟历史数据
"""
import os
import sys
import json
import argparse
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from report_generator import HTMLReportGenerator


def get_trading_days_in_range(start_date: str, end_date: str) -> list:
    """
    获取日期区间内的所有交易日（排除周末）

    Args:
        start_date: 开始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD

    Returns:
        交易日期列表
    """
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    trading_days = []
    current = start

    while current <= end:
        # 排除周末 (0=Monday, 5=Saturday, 6=Sunday)
        if current.weekday() < 5:
            trading_days.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)

    return trading_days


def generate_mock_data_for_date(date: str, days_ago: int) -> dict:
    """
    为指定日期生成模拟数据

    Args:
        date: 日期字符串 YYYY-MM-DD
        days_ago: 距离今天的天数（用于生成不同的数据）

    Returns:
        模拟的数据字典
    """
    # 常见活跃标的
    base_tickers = [
        'SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMZN',
        'META', 'GOOGL', 'AMD', 'INTC', 'IWM', 'DIA', 'VIX',
        'NFLX', 'BABA', 'NIO', 'PLTR', 'SOFI', 'BAC',
        'JPM', 'XLE', 'GLD', 'SLV', 'TLT', 'EEM',
        'PFE', 'WMT', 'BA', 'CAT'
    ]

    # 根据距离今天的天数调整数据，模拟市场变化
    # 让一些标的偶尔不出现在 Top 30
    import random
    random.seed(hash(date))  # 使用日期作为种子，保证同一天生成的数据相同

    # 随机选择 25-30 个标的
    num_tickers = random.randint(25, 30)
    selected_tickers = random.sample(base_tickers, min(num_tickers, len(base_tickers)))

    # 某些标的更容易出现（常驻嘉宾）
    常驻嘉宾 = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL']
    for ticker in 常驻嘉宾:
        if ticker not in selected_tickers and random.random() > 0.1:  # 90% 概率出现
            selected_tickers.append(ticker)

    data = []

    for rank, ticker in enumerate(selected_tickers[:30], 1):
        # 基础数据随日期变化
        base_volume = 5000000 - rank * 150000 + days_ago * 80000 + random.randint(-500000, 500000)
        base_oi = 2000000 - rank * 80000 + random.randint(-200000, 200000)

        # 确保数据为正
        base_volume = max(base_volume, 500000)
        base_oi = max(base_oi, 100000)

        put_volume = int(base_volume * random.uniform(0.35, 0.65))
        call_volume = base_volume - put_volume

        put_oi = int(base_oi * random.uniform(0.35, 0.65))
        call_oi = base_oi - put_oi

        # 生成 Top 3 合约（模拟）
        strike_base = random.choice([50, 100, 200, 400, 600])
        top_3_contracts = []

        for i in range(3):
            contract_oi = int(base_oi * random.uniform(0.05, 0.12))
            strike = strike_base + i * 5
            contract_type = random.choice(['call', 'put'])
            expiry_days = random.choice([7, 14, 30, 60])
            expiry = (datetime.strptime(date, '%Y-%m-%d') + timedelta(days=expiry_days)).strftime('%Y-%m-%d')

            top_3_contracts.append({
                'ticker': f'O:{ticker}{expiry.replace("-", "")}{"C" if contract_type == "call" else "P"}{strike:08d}',
                'oi': contract_oi,
                'strike': float(strike),
                'expiry': expiry,
                'type': contract_type,
                'percentage': round(contract_oi / base_oi * 100, 1)
            })

        # 按持仓量排序
        top_3_contracts.sort(key=lambda x: x['oi'], reverse=True)

        # 重新计算百分比
        for contract in top_3_contracts:
            contract['percentage'] = round(contract['oi'] / base_oi * 100, 1)

        # 生成价格区间
        if strike_base < 50:
            range_width = 5
        elif strike_base < 200:
            range_width = 10
        elif strike_base < 500:
            range_width = 20
        else:
            range_width = 50

        range_start = int(strike_base / range_width) * range_width
        range_end = range_start + range_width
        range_oi = int(base_oi * random.uniform(0.15, 0.30))

        item = {
            'ticker': ticker,
            'total_volume': base_volume,
            'put_volume': put_volume,
            'call_volume': call_volume,
            'cp_volume_ratio': round(call_volume / put_volume, 2) if put_volume > 0 else 0,
            'total_oi': base_oi,
            'put_oi': put_oi,
            'call_oi': call_oi,
            'cp_oi_ratio': round(call_oi / put_oi, 2) if put_oi > 0 else 0,
            'contracts_count': random.randint(300, 600),
            'top_3_contracts': top_3_contracts,
            'strike_concentration': {
                'range': f'{range_start}-{range_end}',
                'oi': range_oi,
                'percentage': round(range_oi / base_oi * 100, 1),
                'dominant_strike': strike_base
            }
        }

        data.append(item)

    # 按成交量排序
    data.sort(key=lambda x: x['total_volume'], reverse=True)

    return data


def save_historical_data(date: str, data: list, output_dir: str = 'output'):
    """
    保存历史数据到文件

    Args:
        date: 日期字符串
        data: 数据列表
        output_dir: 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)

    # 生成假的异常数据（空列表）
    anomalies = []
    summary = {'total': 0, 'by_severity': {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}}

    # 保存 JSON
    historical_data = {
        'date': date,
        'timestamp': f'{date}T22:00:00.000000',  # 假设是晚上10点生成的
        'tickers_count': len(data),
        'anomalies_count': 0,
        'data': data,
        'anomalies': anomalies,
        'summary': summary,
        'note': '此数据为历史模拟数据，仅用于测试10日活跃度功能'
    }

    json_file = os.path.join(output_dir, f'{date}.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(historical_data, f, ensure_ascii=False, indent=2)

    print(f'  ✓ JSON saved: {json_file}')

    # 生成 HTML 报告
    reporter = HTMLReportGenerator()
    html_file = os.path.join(output_dir, f'{date}.html')
    reporter.generate(
        data=data,
        anomalies=anomalies,
        summary=summary,
        output_file=html_file
    )

    print(f'  ✓ HTML saved: {html_file}')


def main():
    parser = argparse.ArgumentParser(
        description='生成指定日期或日期区间的历史数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成单个日期的数据
  python generate_historical_data.py --date 2025-10-20

  # 生成日期区间的数据
  python generate_historical_data.py --start 2025-10-20 --end 2025-10-29

  # 生成过去10个交易日的数据
  python generate_historical_data.py --days 10
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--date', help='单个日期 (YYYY-MM-DD)')
    group.add_argument('--start', help='开始日期 (YYYY-MM-DD)，需配合 --end 使用')
    group.add_argument('--days', type=int, help='生成过去N个交易日的数据')

    parser.add_argument('--end', help='结束日期 (YYYY-MM-DD)，配合 --start 使用')
    parser.add_argument('--output', default='output', help='输出目录 (默认: output)')

    args = parser.parse_args()

    print("=" * 70)
    print("历史数据生成工具")
    print("=" * 70)
    print()

    # 确定要生成的日期列表
    dates = []

    if args.date:
        # 单个日期
        dates = [args.date]
        print(f"模式: 生成单个日期")
        print(f"日期: {args.date}")

    elif args.start:
        # 日期区间
        if not args.end:
            parser.error("使用 --start 时必须指定 --end")

        dates = get_trading_days_in_range(args.start, args.end)
        print(f"模式: 生成日期区间")
        print(f"区间: {args.start} 至 {args.end}")
        print(f"交易日: {len(dates)} 天（排除周末）")

    elif args.days:
        # 过去N个交易日
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days * 2)  # 预留足够的天数

        dates = get_trading_days_in_range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )[-args.days:]  # 取最后N个交易日

        print(f"模式: 生成过去N个交易日")
        print(f"天数: {args.days} 个交易日")
        print(f"日期范围: {dates[0]} 至 {dates[-1]}")

    print()
    print("=" * 70)
    print(f"开始生成 {len(dates)} 天的数据...")
    print("=" * 70)
    print()

    # 生成数据
    today = datetime.now()

    for date in dates:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        days_ago = (today - date_obj).days

        print(f"生成 {date} 的数据 (距今 {days_ago} 天)...")

        data = generate_mock_data_for_date(date, days_ago)
        save_historical_data(date, data, args.output)

        print()

    print("=" * 70)
    print(f"✅ 完成！共生成 {len(dates)} 天的数据")
    print("=" * 70)
    print()
    print("生成的文件:")
    print(f"  - {args.output}/*.json  (原始数据)")
    print(f"  - {args.output}/*.html  (HTML报告)")
    print()
    print("下一步:")
    print("  1. 运行 main.py 进行一次完整分析")
    print("  2. 查看报告中的 '10日活跃度' 列")
    print("  3. 应该能看到完整的历史统计数据")
    print()


if __name__ == '__main__':
    main()
