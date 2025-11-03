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
from trading_calendar import has_trading_days_between, get_previous_trading_day, get_trading_calendar

# Load environment variables
load_dotenv()


def get_trading_days_in_range(start_date: str, end_date: str) -> list:
    """
    获取日期区间内的所有交易日（使用 NYSE 交易日历）

    Args:
        start_date: 开始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD

    Returns:
        交易日期列表
    """
    calendar = get_trading_calendar()
    return calendar.get_trading_days_in_range(start_date, end_date)


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
        print(f'📥 STEP 1/4: 下载 CSV 文件')
        print(f'   目标日期: {date}')

        # Initialize fetcher to get CSV handler
        fetcher = HybridDataFetcher()

        # Try to download and parse CSV for the specified date
        print(f'   ⏳ 正在尝试下载 {date}.csv.gz ...')
        success, data, csv_date = fetcher.csv_handler.try_download_and_parse(date=date, max_retries=1)

        if not success or not data:
            print(f'   ❌ CSV下载失败 - 文件不存在或无法访问')
            print(f'   ⊘ 跳过 {date}，不生成任何文件')
            return None

        print(f'   ✅ CSV下载成功！')
        print(f'      - 文件: {csv_date}.csv.gz')
        print(f'      - 数据: {len(data)} 个标的')
        print(f'      - 总成交量: {sum(d["total_volume"] for d in data):,}')
        print()

        # Algorithm 2: Determine if OI should be fetched
        print(f'📡 STEP 2/5: 检查是否需要获取 Open Interest 数据')
        current_date = datetime.now().strftime('%Y-%m-%d')
        should_fetch_oi = not has_trading_days_between(csv_date, current_date)

        if should_fetch_oi:
            print(f'   ✓ {csv_date} 至今无新交易日')
            print(f'   → OI 数据有意义（反映 {csv_date} 盘后市场状态）')
            print(f'   ⏳ 正在为前 35 个标的获取 OI 数据...')
            data, metadata = fetcher.enrich_with_oi(data, top_n=35)
            print(f'   ✅ OI 数据获取完成')
        else:
            print(f'   ⊘ {csv_date} 至今有新交易日')
            print(f'   → OI 数据无意义（会是今天的数据，不是 {csv_date} 的）')
            print(f'   → 跳过 OI 获取')
            metadata = {
                'data_source': 'CSV',
                'csv_date': csv_date,
                'oi_skipped': 'historical_data',
                'oi_skip_reason': f'New trading days exist between {csv_date} and {current_date}'
            }
        print()

        print(f'📊 STEP 3/5: 分析历史活跃度')
        print(f'   ⏳ 正在分析 {date} 的历史数据...')
        analyzer = HistoryAnalyzer(output_dir=output_dir, lookback_days=10)
        data = analyzer.enrich_data_with_history(data)
        print(f'   ✅ 历史分析完成')
        print()

        print(f'🔍 STEP 4/5: 检测异常信号')
        print(f'   ⏳ 正在检测 {date} 的市场异常...')
        detector = OptionsAnomalyDetector()
        anomalies = detector.detect_all_anomalies(data)
        summary = detector.get_summary()
        print(f'   ✅ 异常检测完成')
        print(f'      - 检测到 {summary["total"]} 个异常信号')

        # Show by type breakdown if available
        if summary.get('by_type'):
            print(f'      - 按类型分布:')
            for atype, count in sorted(summary['by_type'].items(), key=lambda x: x[1], reverse=True):
                print(f'        • {atype}: {count}')

        # Show by severity breakdown if available
        if summary.get('by_severity'):
            print(f'      - 按严重程度:')
            for severity, count in sorted(summary['by_severity'].items(), key=lambda x: x[1], reverse=True):
                print(f'        • {severity}: {count}')
        print()

        metadata = {
            'data_source': 'CSV',
            'csv_date': csv_date
        }

        print(f'✅ {date} 数据准备完成，等待保存...')
        return data, anomalies, summary, metadata

    except Exception as e:
        print(f'   ❌ 处理 {date} 时发生错误: {e}')
        print(f'   ⊘ 跳过 {date}，不生成任何文件')
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
    print(f'💾 STEP 5/5: 保存数据文件')
    os.makedirs(output_dir, exist_ok=True)

    # 保存 JSON
    data_source = metadata.get('data_source', 'CSV')
    historical_data = {
        'date': date,  # CSV date (data date)
        'generated_at': datetime.now().isoformat(),  # When report was generated
        'tickers_count': len(data),
        'anomalies_count': summary.get('total', 0),
        'data_source': data_source,
        'data': data,
        'anomalies': anomalies,
        'summary': summary,
        'metadata': metadata  # Include full metadata (OI skip info, etc.)
    }

    json_file = os.path.join(output_dir, f'{date}.json')
    print(f'   ⏳ 正在保存 JSON: {date}.json ...')
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(historical_data, f, ensure_ascii=False, indent=2)
    file_size = os.path.getsize(json_file) / 1024
    print(f'   ✅ JSON 已保存: {json_file} ({file_size:.1f} KB)')

    # 生成 HTML 报告
    html_file = os.path.join(output_dir, f'{date}.html')
    print(f'   ⏳ 正在生成 HTML: {date}.html ...')
    reporter = HTMLReportGenerator()
    reporter.generate(
        data=data,
        anomalies=anomalies,
        summary=summary,
        metadata=metadata,
        output_file=html_file
    )
    file_size = os.path.getsize(html_file) / 1024
    print(f'   ✅ HTML 已保存: {html_file} ({file_size:.1f} KB)')
    print()


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
        # 使用前一个已完成的交易日作为结束日期（不包含今天）
        end_date_str = get_previous_trading_day()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        start_date = end_date - timedelta(days=args.days * 2)  # 预留足够的天数

        dates = get_trading_days_in_range(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )[-args.days:]  # 取最后N个交易日

        print(f"模式: 生成过去N个交易日")
        print(f"天数: {args.days} 个交易日")
        print(f"日期范围: {dates[0]} 至 {dates[-1]}")
        print(f"注意: 结束日期是最后一个已完成的交易日 ({end_date_str})")

    print()
    print("=" * 70)
    print(f"开始下载 {len(dates)} 天的CSV数据...")
    print("=" * 70)
    print()

    # 生成数据
    today = datetime.now()
    success_count = 0
    skip_count = 0
    total_days = len(dates)

    for idx, date in enumerate(dates, 1):
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        days_ago = (today - date_obj).days

        print("━" * 70)
        print(f"📅 [{idx}/{total_days}] 处理日期: {date} (距今 {days_ago} 天)")
        print(f"   进度: {idx}/{total_days} ({idx*100//total_days}%) | 成功: {success_count} | 跳过: {skip_count}")
        print("━" * 70)

        result = generate_data_for_date(date, args.output)

        if result is None:
            skip_count += 1
            print(f'━' * 70)
            print(f'❌ {date} 处理失败 - CSV文件不可用，已跳过')
            print(f'━' * 70)
        else:
            data, anomalies, summary, metadata = result
            save_historical_data(date, data, anomalies, summary, metadata, args.output)
            success_count += 1
            print(f'━' * 70)
            print(f'✅ {date} 处理完成！')
            print(f'━' * 70)

        print(f'📊 汇总统计: 已完成 {idx}/{total_days} | 成功 {success_count} | 跳过 {skip_count} | 剩余 {total_days - idx}')
        print()
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
        generate_archive_index(reports, os.path.join(args.output, 'archive.html'))
        print(f"✓ 归档索引更新完成 ({len(reports)} 个报告)")
        print()

    print("下一步:")
    print("  1. 运行 main.py 进行一次完整分析")
    print("  2. 查看报告中的 '10日活跃度' 列")
    print("  3. 应该能看到完整的历史统计数据")
    print()


if __name__ == '__main__':
    main()
