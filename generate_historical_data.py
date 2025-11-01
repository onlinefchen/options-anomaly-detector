#!/usr/bin/env python3
"""
历史数据生成工具
用于生成指定日期或日期区间的历史数据（从真实CSV文件）
"""
import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from hybrid_fetcher import HybridDataFetcher
from anomaly_detector import OptionsAnomalyDetector
from report_generator import HTMLReportGenerator
from history_analyzer import HistoryAnalyzer
from archive_index_generator import get_archived_reports, generate_archive_index

# Load environment variables
load_dotenv()


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


def generate_data_for_date(date: str, output_dir: str = 'output') -> tuple:
    """
    为指定日期生成数据（从真实CSV文件）

    Args:
        date: 日期字符串 YYYY-MM-DD
        output_dir: 输出目录

    Returns:
        (data, anomalies, summary, metadata) 如果成功下载CSV
        None 如果CSV不存在（跳过该日期）
    """
    try:
        # Initialize fetcher
        fetcher = HybridDataFetcher()

        # Try to fetch data for the specified date using CSV strategy
        data, metadata = fetcher.fetch_data_for_date(date, strategy='csv', top_n_for_oi=30)

        # Check if we got CSV data
        data_source = metadata.get('data_source', 'Unknown')
        if data_source not in ['CSV', 'CSV+API']:
            print(f'  ⊘ No CSV available for {date} (data source: {data_source}), skipping...')
            return None

        if not data:
            print(f'  ⊘ No data available for {date}, skipping...')
            return None

        print(f'  ✓ Downloaded CSV data: {len(data)} tickers')
        print(f'     Data source: {data_source}')

        # Analyze historical activity
        analyzer = HistoryAnalyzer(output_dir=output_dir, lookback_days=10)
        data = analyzer.enrich_data_with_history(data)
        print(f'  ✓ Historical analysis complete')

        # Detect anomalies
        detector = OptionsAnomalyDetector()
        anomalies = detector.detect_all_anomalies(data)
        summary = detector.get_summary()
        print(f'  ✓ Detected {summary["total"]} anomalies')

        return data, anomalies, summary, metadata

    except Exception as e:
        print(f'  ❌ Error processing {date}: {e}')
        import traceback
        traceback.print_exc()
        return None


def save_historical_data(date: str, data: list, anomalies: list, summary: dict,
                         metadata: dict, output_dir: str = 'output'):
    """
    保存历史数据到文件

    Args:
        date: 日期字符串
        data: 数据列表
        anomalies: 异常列表
        summary: 统计摘要
        metadata: 元数据（包含data_source等）
        output_dir: 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)

    # 保存 JSON
    data_source = metadata.get('data_source', 'Unknown')
    historical_data = {
        'date': date,
        'timestamp': datetime.now().isoformat(),
        'tickers_count': len(data),
        'anomalies_count': summary.get('total', 0),
        'data_source': data_source,
        'data': data,
        'anomalies': anomalies,
        'summary': summary
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
        metadata=metadata,
        output_file=html_file
    )

    print(f'  ✓ HTML saved: {html_file}')


def main():
    parser = argparse.ArgumentParser(
        description='生成指定日期或日期区间的历史数据（从真实CSV文件）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 生成单个日期的数据
  python generate_historical_data.py --date 2025-10-20

  # 生成日期区间的数据
  python generate_historical_data.py --start 2025-10-20 --end 2025-10-29

  # 生成过去10个交易日的数据
  python generate_historical_data.py --days 10

注意:
  - 需要配置 POLYGON_S3_ACCESS_KEY 和 POLYGON_S3_SECRET_KEY
  - 只会下载存在CSV文件的日期，不存在的日期会自动跳过
  - 周末和节假日通常没有CSV文件
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
    print("历史数据生成工具 (从真实CSV文件)")
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
    print(f"开始下载 {len(dates)} 天的CSV数据...")
    print("=" * 70)
    print()

    # 生成数据
    today = datetime.now()
    success_count = 0
    skip_count = 0

    for date in dates:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        days_ago = (today - date_obj).days

        print(f"处理 {date} (距今 {days_ago} 天)...")

        result = generate_data_for_date(date, args.output)

        if result is None:
            skip_count += 1
            print(f'  ⊘ 跳过 {date}')
        else:
            data, anomalies, summary, metadata = result
            save_historical_data(date, data, anomalies, summary, metadata, args.output)
            success_count += 1
            print(f'  ✓ 完成 {date}')

        print()

    print("=" * 70)
    print(f"✅ 完成！")
    print("=" * 70)
    print(f"  • 成功: {success_count} 天")
    print(f"  • 跳过: {skip_count} 天（无CSV）")
    print()
    print("生成的文件:")
    print(f"  - {args.output}/*.json  (原始数据)")
    print(f"  - {args.output}/*.html  (HTML报告)")
    print()

    # Generate archive index if we have any reports
    if success_count > 0:
        print("📚 生成归档索引...")
        reports = get_archived_reports(args.output)
        generate_archive_index(reports, args.output)
        print(f"✓ 归档索引更新完成 ({len(reports)} 个报告)")
        print()

    print("下一步:")
    print("  1. 运行 main.py 进行一次完整分析")
    print("  2. 查看报告中的 '10日活跃度' 列")
    print("  3. 应该能看到完整的历史统计数据")
    print()


if __name__ == '__main__':
    main()
