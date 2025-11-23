#!/usr/bin/env python3
"""
统一的 CLI 工具 - 处理所有 workflow 操作

Commands:
  daily-analysis     运行每日分析
  regenerate-html    重新生成 HTML 报告
  test-email         测试邮件发送
  restore-data       从 gh-pages 恢复历史数据
"""
import os
import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def restore_historical_data(source_dir: str, output_dir: str = 'output'):
    """
    从 gh-pages 分支恢复历史 JSON 文件

    Args:
        source_dir: gh-pages 数据目录
        output_dir: 输出目录

    Returns:
        恢复的文件数量
    """
    print("📂 Restoring historical data...")
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(source_dir):
        print(f"⚠️  No historical data found (first run?)")
        return 0

    # Copy all JSON files
    count = 0
    for file in Path(source_dir).rglob('*.json'):
        if file.name.endswith('.json'):
            dest = os.path.join(output_dir, file.name)
            shutil.copy2(file, dest)
            count += 1

    print(f"✓ Historical data restored: {count} files")
    return count


def daily_analysis_command(args):
    """运行每日分析"""
    print("=" * 80)
    print("📊 Daily Analysis")
    print("=" * 80)
    print()

    # Restore historical data if available
    if args.restore_from:
        restore_historical_data(args.restore_from)
        print()

    # 根据参数决定运行哪个脚本
    if args.days_back and args.days_back > 0:
        # 生成历史数据
        print(f"📊 Generating past {args.days_back} trading days")
        print()

        cmd_args = ['--days', str(args.days_back)]

        # Import and run
        import generate_historical_data
        sys.argv = ['generate_historical_data.py'] + cmd_args
        generate_historical_data.main()
    else:
        # 运行正常的每日分析
        print("🔍 Running daily analysis")
        print()

        import main
        exit_code = main.main()
        if exit_code != 0:
            sys.exit(exit_code)

    # 生成 archive index
    print()
    print("📚 Generating archive index...")
    from archive_index_generator import get_archived_reports, generate_archive_index
    reports = get_archived_reports('output')
    generate_archive_index(reports, 'output/archive.html')
    print(f"✓ Archive index generated: {len(reports)} reports")

    print()
    print("=" * 80)
    print("✅ Daily analysis complete!")
    print("=" * 80)


def regenerate_html_command(args):
    """重新生成 HTML 报告"""
    from trading_calendar import get_trading_calendar

    print("=" * 80)
    print("🔄 Regenerate HTML Reports")
    print("=" * 80)
    print()

    # Restore data from gh-pages
    if args.restore_from:
        count = restore_historical_data(args.restore_from)
        if count == 0:
            print("❌ No gh-pages data found")
            sys.exit(1)
        print()

    output_dir = args.output_dir or 'output'

    # 收集需要处理的 JSON 文件
    json_files = []

    if args.specific_date:
        # 特定日期模式
        print(f"Mode: Regenerate specific date {args.specific_date}")

        # Check if trading day
        calendar = get_trading_calendar()
        if not calendar.is_trading_day(args.specific_date):
            print(f"❌ {args.specific_date} is not a trading day")
            print("   Only trading days can have valid data")
            sys.exit(1)

        json_file = os.path.join(output_dir, f'{args.specific_date}.json')
        if not os.path.exists(json_file):
            print(f"❌ No JSON file found for {args.specific_date}")
            sys.exit(1)

        json_files = [json_file]
    else:
        # 最近 N 天模式
        days = args.days or 7
        print(f"Mode: Regenerate last {days} days")
        print()

        # 查找所有 JSON 文件并排序
        all_files = sorted(
            [f for f in os.listdir(output_dir)
             if f.endswith('.json') and len(f) == 15],  # YYYY-MM-DD.json
            reverse=True
        )[:days]

        if not all_files:
            print("❌ No JSON files found")
            sys.exit(1)

        json_files = [os.path.join(output_dir, f) for f in all_files]

    # 处理每个文件
    print(f"Processing {len(json_files)} file(s)...")
    print()

    success_count = 0
    calendar = get_trading_calendar()

    for idx, json_file in enumerate(json_files, 1):
        date = Path(json_file).stem
        print(f"[{idx}/{len(json_files)}] Processing {date}...")

        # Check if trading day
        if not calendar.is_trading_day(date):
            print(f"  ⊘ Skipped (not a trading day)")
            print()
            continue

        # Load JSON
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Generate HTML
            from report_generator import HTMLReportGenerator
            reporter = HTMLReportGenerator()
            html_file = json_file.replace('.json', '.html')

            reporter.generate(
                data=data.get('data', []),
                anomalies=data.get('anomalies', []),
                summary=data.get('summary', {}),
                metadata=data.get('metadata', {}),
                output_file=html_file
            )

            print(f"  ✓ Success")
            success_count += 1
        except Exception as e:
            print(f"  ✗ Failed: {e}")

        print()

    print("=" * 80)
    print(f"Complete! Generated {success_count}/{len(json_files)} HTML files")
    print("=" * 80)
    print()

    # Regenerate archive index
    print("📚 Regenerating archive index...")
    from archive_index_generator import get_archived_reports, generate_archive_index
    reports = get_archived_reports(output_dir)
    generate_archive_index(reports, os.path.join(output_dir, 'archive.html'))
    print(f"✓ Archive index updated ({len(reports)} reports)")
    print()

    # Update index.html with latest
    html_files = sorted(
        [f for f in os.listdir(output_dir)
         if f.endswith('.html') and len(f) == 15],  # YYYY-MM-DD.html
        reverse=True
    )

    if html_files:
        latest_html = os.path.join(output_dir, html_files[0])
        index_html = os.path.join(output_dir, 'index.html')
        shutil.copy2(latest_html, index_html)
        date = Path(html_files[0]).stem
        print(f"✓ Copied latest report to index.html ({date})")
    else:
        print("⚠️  No HTML files found")

    print()
    print("=" * 80)
    print("✅ HTML regeneration complete!")
    print("=" * 80)


def test_email_command(args):
    """测试邮件发送"""
    print("=" * 80)
    print("📧 Testing Email Sending")
    print("=" * 80)
    print()

    gmail_user = os.getenv('GMAIL_USER')
    recipient = os.getenv('RECIPIENT_EMAIL')

    print(f"Gmail User: {gmail_user}")
    print(f"Recipient: {recipient}")
    print()

    # Run test_email.py
    import test_email
    test_email.main()

    print()
    print("=" * 80)
    print("✅ Email test complete!")
    print("=" * 80)


def restore_data_command(args):
    """恢复历史数据"""
    print("=" * 80)
    print("📂 Restore Historical Data")
    print("=" * 80)
    print()

    if not args.source:
        print("❌ Error: --source is required")
        sys.exit(1)

    count = restore_historical_data(args.source, args.output_dir or 'output')

    print()
    print("=" * 80)
    print(f"✅ Restored {count} files")
    print("=" * 80)


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description='统一的 CLI 工具 - 处理所有 workflow 操作',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # daily-analysis 命令
    daily_parser = subparsers.add_parser('daily-analysis', help='运行每日分析')
    daily_parser.add_argument('--days-back', type=int, default=0,
                            help='生成过去N个交易日的数据（0=只生成今天）')
    daily_parser.add_argument('--restore-from',
                            help='从指定目录恢复历史数据（如 gh-pages-data）')

    # regenerate-html 命令
    regen_parser = subparsers.add_parser('regenerate-html', help='重新生成 HTML 报告')
    regen_parser.add_argument('--days', type=int, default=7,
                            help='更新最近N天的HTML报告')
    regen_parser.add_argument('--specific-date',
                            help='指定特定日期 (YYYY-MM-DD)')
    regen_parser.add_argument('--restore-from',
                            help='从指定目录恢复历史数据（如 gh-pages-data）')
    regen_parser.add_argument('--output-dir', default='output',
                            help='输出目录')

    # test-email 命令
    email_parser = subparsers.add_parser('test-email', help='测试邮件发送')

    # restore-data 命令
    restore_parser = subparsers.add_parser('restore-data', help='恢复历史数据')
    restore_parser.add_argument('--source', required=True,
                              help='源数据目录（如 gh-pages-data）')
    restore_parser.add_argument('--output-dir', default='output',
                              help='输出目录')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 执行对应的命令
    if args.command == 'daily-analysis':
        daily_analysis_command(args)
    elif args.command == 'regenerate-html':
        regenerate_html_command(args)
    elif args.command == 'test-email':
        test_email_command(args)
    elif args.command == 'restore-data':
        restore_data_command(args)


if __name__ == '__main__':
    main()
