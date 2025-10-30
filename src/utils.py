#!/usr/bin/env python3
"""
Utility Functions
"""
from datetime import datetime
import pytz


def print_banner():
    """Print application banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║      📊 OPTIONS ANOMALY DETECTOR 📊                   ║
    ║                                                       ║
    ║      CSV + API Hybrid Strategy                       ║
    ║      Real-time options market anomaly detection      ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """
    print(banner)

    # Get market times with timezone info
    time_info = get_market_times()
    print(f"    {time_info['session_emoji']} 美东时间: {time_info['et_str']}")
    print(f"    🌏 东八区时间: {time_info['utc8_str']}")
    print(f"    📊 交易时段: {time_info['session_cn']} ({time_info['session_en']})")
    print(f"    {'='*55}\n")


def print_summary_table(data):
    """
    Print summary table of top volume tickers

    Args:
        data: List of aggregated options data
    """
    print("\n" + "="*100)
    print("📊 TOP 30 OPTIONS VOLUME RANKINGS")
    print("="*100)

    # Header
    print(f"{'排名':<6} {'股票':<8} {'总成交量':<15} {'C/P成交比':<12} "
          f"{'持仓量':<15} {'C/P持仓比':<12} {'Put量':<12} {'Call量':<12}")
    print("-"*100)

    # Sort by volume
    sorted_data = sorted(data, key=lambda x: x['total_volume'], reverse=True)[:30]

    # Data rows
    for idx, item in enumerate(sorted_data, 1):
        print(f"{idx:<6} {item['ticker']:<8} {item['total_volume']:>14,} "
              f"{item['cp_volume_ratio']:>11.2f} {item['total_oi']:>14,} "
              f"{item['cp_oi_ratio']:>11.2f} {item['put_volume']:>11,} "
              f"{item['call_volume']:>11,}")

    print("="*100 + "\n")


def print_anomalies_summary(anomalies, summary):
    """
    Print anomalies summary

    Args:
        anomalies: List of detected anomalies
        summary: Summary statistics dict
    """
    print("\n" + "="*100)
    print("🚨 DETECTED ANOMALIES")
    print("="*100)

    print(f"\n📈 Summary:")
    print(f"   Total Anomalies: {summary['total']}")
    print(f"   High Severity:   {summary['by_severity'].get('HIGH', 0)}")
    print(f"   Medium Severity: {summary['by_severity'].get('MEDIUM', 0)}")
    print(f"   Low Severity:    {summary['by_severity'].get('LOW', 0)}")

    if anomalies:
        print(f"\n🔍 Top Anomalies:\n")

        # Sort by severity
        severity_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        sorted_anomalies = sorted(
            anomalies,
            key=lambda x: severity_order.get(x['severity'], 0),
            reverse=True
        )[:15]  # Show top 15

        for idx, anomaly in enumerate(sorted_anomalies, 1):
            severity_icon = {
                'HIGH': '🔴',
                'MEDIUM': '🟡',
                'LOW': '🔵'
            }.get(anomaly['severity'], '⚪')

            print(f"   {idx:>2}. {severity_icon} [{anomaly['ticker']:<6}] "
                  f"{anomaly['type']:<25} - {anomaly['description']}")

    print("\n" + "="*100 + "\n")


def print_progress(message, end='\n'):
    """
    Print progress message

    Args:
        message: Message to print
        end: Line ending
    """
    print(f"  {message}", end=end, flush=True)


def get_market_session(et_time):
    """
    Determine market session based on ET time

    Args:
        et_time: datetime object in ET timezone

    Returns:
        str: 'pre-market', 'market-hours', 'after-hours', or 'closed'
    """
    hour = et_time.hour
    minute = et_time.minute
    time_in_minutes = hour * 60 + minute

    # Market hours in minutes from midnight
    pre_market_start = 4 * 60  # 4:00 AM
    market_open = 9 * 60 + 30  # 9:30 AM
    market_close = 16 * 60     # 4:00 PM
    after_hours_end = 20 * 60  # 8:00 PM

    # Check day of week (0=Monday, 6=Sunday)
    weekday = et_time.weekday()
    if weekday >= 5:  # Saturday or Sunday
        return 'closed'

    if pre_market_start <= time_in_minutes < market_open:
        return 'pre-market'
    elif market_open <= time_in_minutes < market_close:
        return 'market-hours'
    elif market_close <= time_in_minutes < after_hours_end:
        return 'after-hours'
    else:
        return 'closed'


def get_market_session_display(session):
    """
    Get display text for market session

    Args:
        session: Market session string

    Returns:
        tuple: (Chinese text, English text, emoji)
    """
    session_map = {
        'pre-market': ('盘前', 'Pre-Market', '🌅'),
        'market-hours': ('盘中', 'Market Hours', '📈'),
        'after-hours': ('盘后', 'After Hours', '🌙'),
        'closed': ('休市', 'Market Closed', '🔒')
    }
    return session_map.get(session, ('未知', 'Unknown', '❓'))


def get_market_times():
    """
    Get current time in multiple timezones and market session

    Returns:
        dict with time information:
        {
            'et_time': datetime object in ET,
            'et_str': formatted ET time string,
            'utc8_time': datetime object in UTC+8,
            'utc8_str': formatted UTC+8 time string,
            'session': market session identifier,
            'session_cn': Chinese session name,
            'session_en': English session name,
            'session_emoji': session emoji
        }
    """
    # Get current UTC time
    utc_now = datetime.now(pytz.utc)

    # Convert to ET (US/Eastern handles DST automatically)
    et_tz = pytz.timezone('US/Eastern')
    et_time = utc_now.astimezone(et_tz)

    # Convert to UTC+8 (Asia/Shanghai)
    utc8_tz = pytz.timezone('Asia/Shanghai')
    utc8_time = utc_now.astimezone(utc8_tz)

    # Get market session
    session = get_market_session(et_time)
    session_cn, session_en, session_emoji = get_market_session_display(session)

    return {
        'et_time': et_time,
        'et_str': et_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
        'utc8_time': utc8_time,
        'utc8_str': utc8_time.strftime('%Y-%m-%d %H:%M:%S'),
        'session': session,
        'session_cn': session_cn,
        'session_en': session_en,
        'session_emoji': session_emoji
    }


def format_market_time_html(time_info):
    """
    Format market time information for HTML display

    Args:
        time_info: dict from get_market_times()

    Returns:
        str: HTML formatted time string
    """
    return (
        f"{time_info['session_emoji']} "
        f"<strong>美东时间:</strong> {time_info['et_str']} | "
        f"<strong>东八区时间:</strong> {time_info['utc8_str']} | "
        f"<strong>交易时段:</strong> {time_info['session_cn']} ({time_info['session_en']})"
    )
