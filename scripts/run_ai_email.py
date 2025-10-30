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
    # 读取最新的分析结果
    date_str = os.getenv('ANALYSIS_DATE', '')
    if not date_str:
        print('❌ ANALYSIS_DATE environment variable not set')
        sys.exit(1)

    json_file = f'output/{date_str}.json'

    if not os.path.exists(json_file):
        print(f'⚠️  Data file not found: {json_file}')
        sys.exit(0)

    with open(json_file, 'r') as f:
        result = json.load(f)

    data = result.get('data', [])
    anomalies = result.get('anomalies', [])
    summary = result.get('summary', {})

    print(f'\n📊 Loaded data: {len(data)} tickers, {summary.get("total", 0)} anomalies\n')

    # AI 分析
    ai_analyzer = AIAnalyzer()
    email_sender = EmailSender()

    analysis_text = None

    if ai_analyzer.is_available():
        print('🤖 Running AI analysis...')
        analysis_text = ai_analyzer.analyze_market_data(data, anomalies, summary)
        if analysis_text:
            print('✓ AI analysis completed')
            print(f'\nAI Analysis Preview:\n{analysis_text[:200]}...\n')
        else:
            print('⚠️  AI analysis failed')
    else:
        print('⊘ AI analysis not available (no API key)')
        analysis_text = '**AI 分析未配置**\n\n请配置 OPENAI_API_KEY 以启用 AI 智能分析功能。'

    # 发送邮件
    if email_sender.is_available():
        recipient = os.getenv('RECIPIENT_EMAIL', os.getenv('GMAIL_USER'))

        if recipient:
            print(f'\n📧 Sending email to {recipient}...')

            subject = ai_analyzer.generate_email_subject(data, summary.get('total', 0))
            html_content = ai_analyzer.format_for_email(analysis_text, data, summary)

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
