#!/usr/bin/env python3
"""
Test Email Sending Functionality
"""
import os
import sys

# Add src to path
sys.path.insert(0, 'src')

from email_sender import EmailSender
from datetime import datetime

def test_email():
    """Test sending a simple email"""

    # Initialize email sender
    email_sender = EmailSender()

    if not email_sender.is_available():
        print("❌ Email credentials not configured!")
        print("   Please set GMAIL_USER, GMAIL_APP_PASSWD, and RECIPIENT_EMAIL")
        return False

    # Get recipient
    recipient = os.getenv('RECIPIENT_EMAIL')
    if not recipient:
        print("❌ RECIPIENT_EMAIL not configured!")
        return False

    print(f"📧 Testing email sending to: {recipient}")
    print(f"📤 Using Gmail account: {email_sender.gmail_user}")
    print()

    # Create test email
    subject = f"🧪 Email Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #1d1d1f;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 20px;
        }}
        .content {{
            background: #f5f5f7;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .success {{
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }}
        .info {{
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }}
        .footer {{
            text-align: center;
            color: #86868b;
            font-size: 12px;
            margin-top: 30px;
        }}
        h1 {{
            margin: 0;
            font-size: 24px;
        }}
        h2 {{
            color: #1d1d1f;
            margin-top: 0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 Email Sending Test</h1>
        <p>Options Anomaly Detection System</p>
    </div>

    <div class="content">
        <h2>✅ Email Configuration Test</h2>

        <div class="success">
            <strong>Success!</strong> If you're reading this email, the email sending functionality is working correctly.
        </div>

        <div class="info">
            <strong>Test Details:</strong><br>
            • Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            • Sender: {email_sender.gmail_user}<br>
            • Recipient: {recipient}<br>
            • SMTP Server: {email_sender.smtp_server}:{email_sender.smtp_port}
        </div>

        <h2>📋 Next Steps</h2>
        <p>If you received this email, your email configuration is correct. The daily workflow should also send emails successfully.</p>

        <p><strong>Common issues if you don't receive workflow emails:</strong></p>
        <ul>
            <li>Check spam/junk folder</li>
            <li>Check email filters and rules</li>
            <li>Verify GitHub Secrets are properly configured</li>
            <li>Check workflow logs for error messages</li>
        </ul>
    </div>

    <div class="footer">
        <p>Options Anomaly Detection System | Email Test</p>
        <p>GitHub: onlinefchen/options-anomaly-detector</p>
    </div>
</body>
</html>
"""

    # Send email
    print("📨 Sending test email...")
    success = email_sender.send_report(recipient, subject, html_content)

    if success:
        print("✅ Email sent successfully!")
        print()
        print("Please check your inbox (and spam folder) for:")
        print(f"   Subject: {subject}")
        return True
    else:
        print("❌ Failed to send email!")
        return False

if __name__ == '__main__':
    success = test_email()
    sys.exit(0 if success else 1)
