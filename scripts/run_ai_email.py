#!/usr/bin/env python3
"""
AI 分析和邮件发送脚本
用于 GitHub Actions workflow
处理所有标记为新生成的数据文件
"""
import sys
import os
import json
import glob

# Add src to path
sys.path.insert(0, 'src')

from ai_analyzer import AIAnalyzer
from email_sender import EmailSender


def process_date(csv_date: str, output_dir: str = 'output'):
    """
    处理单个日期的AI分析和邮件发送

    Args:
        csv_date: CSV日期
        output_dir: 输出目录

    Returns:
        True if successful, False otherwise
    """
    json_file = os.path.join(output_dir, f'{csv_date}.json')

    if not os.path.exists(json_file):
        print(f'⚠️  Data file not found: {json_file}')
        return False

    print(f'\n{"="*60}')
    print(f'📂 Processing: {csv_date}')
    print(f'{"="*60}')

    # 加载数据
    with open(json_file, 'r') as f:
        result = json.load(f)

    # 检查数据来源
    data_source = result.get('data_source', 'Unknown')
    print(f'📊 Data source: {data_source}')

    # 只有当数据来自CSV时才执行AI分析和邮件发送
    if data_source not in ['CSV', 'CSV+API']:
        print(f'⊘ Data is from API only, skipping AI analysis and email')
        print(f'   (AI and email are only sent for CSV data)')
        return True

    print(f'✓ Data is from CSV, proceeding with AI analysis and email')

    data = result.get('data', [])
    anomalies = result.get('anomalies', [])
    summary = result.get('summary', {})
    metadata = result.get('metadata', {})

    print(f'\n📊 Loaded data: {len(data)} tickers, {summary.get("total", 0)} anomalies')
    print(f'📅 CSV date: {csv_date}\n')

    # 初始化组件
    ai_analyzer = AIAnalyzer()
    email_sender = EmailSender()

    # 运行AI分析（如果配置了OpenAI API Key）
    analysis = ''
    if ai_analyzer.is_available():
        print('🤖 Running AI analysis...')
        analysis = ai_analyzer.analyze_market_data(data, anomalies, summary)

        if analysis:
            print('✓ AI analysis completed')
        else:
            print('⚠️  AI analysis returned empty result')
    else:
        print('⊘ OpenAI API Key not configured, skipping AI analysis')

    # 发送邮件
    if email_sender.is_available():
        recipient = os.getenv('RECIPIENT_EMAIL', os.getenv('GMAIL_USER'))

        if recipient:
            print(f'\n📧 Sending email to {recipient}...')

            subject = ai_analyzer.generate_email_subject(data, summary.get('total', 0), csv_date)
            html_content = ai_analyzer.format_for_email(analysis, data, summary, csv_date)

            success = email_sender.send_report(recipient, subject, html_content)

            if success:
                print('✅ Email sent successfully!')
                return True
            else:
                print('❌ Failed to send email')
                return False
        else:
            print('⚠️  No recipient email configured')
            return True
    else:
        print('⊘ Email not available (no Gmail credentials)')
        return True


def main():
    output_dir = 'output'

    # 查找所有NEW_DATA_GENERATED_*标记文件
    flag_pattern = os.path.join(output_dir, 'NEW_DATA_GENERATED_*')
    flag_files = glob.glob(flag_pattern)

    if not flag_files:
        print('⊘ No new data generated (no flag files found)')
        print('   → Skipping AI analysis and email')
        sys.exit(0)

    print(f'✓ Found {len(flag_files)} new data file(s) to process')

    # 处理每个标记的日期
    success_count = 0
    for flag_file in flag_files:
        # 从标记文件名提取日期
        # NEW_DATA_GENERATED_2025-11-13 -> 2025-11-13
        basename = os.path.basename(flag_file)
        csv_date = basename.replace('NEW_DATA_GENERATED_', '')

        # 处理这个日期
        if process_date(csv_date, output_dir):
            success_count += 1
            # 删除标记文件（避免重复处理）
            try:
                os.remove(flag_file)
                print(f'✓ Flag file removed: {basename}')
            except Exception as e:
                print(f'⚠️  Failed to remove flag file: {e}')

    print(f'\n{"="*60}')
    print(f'✓ AI & Email processing completed')
    print(f'   Processed: {success_count}/{len(flag_files)} files')
    print(f'{"="*60}\n')


if __name__ == '__main__':
    main()
