#!/usr/bin/env python3
"""
Email Sender Module
使用 Gmail SMTP 发送邮件报告
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional


class EmailSender:
    """Gmail 邮件发送器"""

    def __init__(
        self,
        gmail_user: Optional[str] = None,
        gmail_app_password: Optional[str] = None
    ):
        """
        Initialize Email Sender

        Args:
            gmail_user: Gmail 邮箱地址
            gmail_app_password: Gmail 应用专用密码
        """
        self.gmail_user = gmail_user or os.getenv('GMAIL_USER')
        self.gmail_password = gmail_app_password or os.getenv('GMAIL_APP_PASSWD')

        # SMTP 配置
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def is_available(self) -> bool:
        """
        Check if email sending is available

        Returns:
            True if Gmail credentials are configured
        """
        return bool(self.gmail_user and self.gmail_password)

    def send_report(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        发送 HTML 邮件

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            html_content: HTML 内容
            text_content: 纯文本内容（可选，作为 HTML 的备选）

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_available():
            print("⚠️  Gmail credentials not configured")
            return False

        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['From'] = self.gmail_user
            msg['To'] = to_email
            msg['Subject'] = subject

            # 添加纯文本版本（如果提供）
            if text_content:
                part1 = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(part1)

            # 添加 HTML 版本
            part2 = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(part2)

            # 连接 SMTP 服务器并发送
            print(f"📧 Connecting to Gmail SMTP server...")
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # 启用 TLS
                print(f"🔐 Logging in as {self.gmail_user}...")
                server.login(self.gmail_user, self.gmail_password)
                print(f"📤 Sending email to {to_email}...")
                server.send_message(msg)

            print(f"✅ Email sent successfully!")
            return True

        except smtplib.SMTPAuthenticationError:
            print("❌ Gmail authentication failed")
            print("   Please check:")
            print("   1. Gmail address is correct")
            print("   2. App password is correct (not your regular password)")
            print("   3. 2-Step Verification is enabled on your Google account")
            return False

        except smtplib.SMTPException as e:
            print(f"❌ SMTP error: {e}")
            return False

        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False

    def send_test_email(self, to_email: str) -> bool:
        """
        发送测试邮件

        Args:
            to_email: 收件人邮箱

        Returns:
            True if sent successfully
        """
        from datetime import datetime

        subject = "📧 期权市场分析系统 - 测试邮件"
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .container {{
            background: #f9f9f9;
            padding: 30px;
            border-radius: 10px;
            border: 2px solid #667eea;
        }}
        h1 {{
            color: #667eea;
        }}
        .success {{
            background: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .info {{
            background: #e3f2fd;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ 邮件配置成功！</h1>

        <div class="success">
            <strong>测试通过！</strong> 您的邮件发送功能已正常工作。
        </div>

        <div class="info">
            <h3>📋 配置信息</h3>
            <ul>
                <li><strong>发件人：</strong>{self.gmail_user}</li>
                <li><strong>收件人：</strong>{to_email}</li>
                <li><strong>测试时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                <li><strong>SMTP 服务器：</strong>{self.smtp_server}:{self.smtp_port}</li>
            </ul>
        </div>

        <h3>🎯 下一步</h3>
        <p>系统将在每天早上 <strong>8:00 AM（东八区）</strong>自动发送期权市场分析报告到此邮箱。</p>

        <h3>📊 报告将包含：</h3>
        <ul>
            <li>🤖 AI 智能分析和市场洞察</li>
            <li>📈 Top 5 活跃标的数据</li>
            <li>⚠️ 异常检测提醒</li>
            <li>🔗 完整在线报告链接</li>
        </ul>

        <hr style="margin: 30px 0; border: 1px solid #ddd;">

        <p style="color: #666; font-size: 0.9em; text-align: center;">
            此邮件由 Options Anomaly Detector 自动生成<br>
            <a href="https://github.com/devfchen/options-anomaly-detector">GitHub 项目</a>
        </p>
    </div>
</body>
</html>
"""

        text_content = f"""
✅ 邮件配置成功！

您的邮件发送功能已正常工作。

配置信息：
- 发件人：{self.gmail_user}
- 收件人：{to_email}
- 测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

系统将在每天早上 8:00 AM（东八区）自动发送期权市场分析报告。

报告将包含：
- AI 智能分析和市场洞察
- Top 5 活跃标的数据
- 异常检测提醒
- 完整在线报告链接

此邮件由 Options Anomaly Detector 自动生成
GitHub: https://github.com/devfchen/options-anomaly-detector
"""

        return self.send_report(to_email, subject, html_content, text_content)
