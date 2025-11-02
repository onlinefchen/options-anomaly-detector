#!/usr/bin/env python3
"""
AI 分析和邮件发送脚本
用于 GitHub Actions workflow
"""
import sys
import os
import json

# Add src to path
sys.path.insert(0, 'src')

from ai_analyzer import AIAnalyzer
from email_sender import EmailSender


def main():
    # 查找最新的分析结果文件
    output_dir = 'output'
    if not os.path.exists(output_dir):
        print(f'⚠️  Output directory not found: {output_dir}')
        sys.exit(0)

    # 获取所有JSON文件，按修改时间排序
    json_files = [
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.endswith('.json')
    ]

    if not json_files:
        print(f'⚠️  No data files found in {output_dir}')
        sys.exit(0)

    # 使用最新的文件
    json_file = max(json_files, key=os.path.getmtime)
    print(f'📂 Using latest data file: {json_file}')

    if not os.path.exists(json_file):
        print(f'⚠️  Data file not found: {json_file}')
        sys.exit(0)

    with open(json_file, 'r') as f:
        result = json.load(f)

    # 检查数据来源
    data_source = result.get('data_source', 'Unknown')
    print(f'📊 Data source: {data_source}')

    # 只有当数据来自CSV时才执行AI分析和邮件发送
    if data_source not in ['CSV', 'CSV+API']:
        print(f'⊘ Data is from API only, skipping AI analysis and email')
        print(f'   (AI and email are only sent for CSV data)')
        sys.exit(0)

    print(f'✓ Data is from CSV, proceeding with AI analysis and email')

    data = result.get('data', [])
    anomalies = result.get('anomalies', [])
    summary = result.get('summary', {})

    print(f'\n📊 Loaded data: {len(data)} tickers, {summary.get("total", 0)} anomalies\n')

    # 初始化组件
    ai_analyzer = AIAnalyzer()
    email_sender = EmailSender()

    # 运行AI分析（如果配置了OpenAI API Key）
    analysis = ''
    if ai_analyzer.is_available():
        print('🤖 Running AI analysis...')
        analysis = ai_analyzer.analyze(anomalies, data, summary)

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

            subject = ai_analyzer.generate_email_subject(data, summary.get('total', 0))
            html_content = ai_analyzer.format_for_email(analysis, data, summary)

            success = email_sender.send_report(recipient, subject, html_content)

            if success:
                print('✅ Email sent successfully!')
            else:
                print('❌ Failed to send email')
        else:
            print('⚠️  No recipient email configured')
    else:
        print('⊘ Email not available (no Gmail credentials)')

    print('\n✓ AI & Email step completed')


if __name__ == '__main__':
    main()
