#!/usr/bin/env python3
"""
Utility Functions
"""
from datetime import datetime


def print_banner():
    """Print application banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║      📊 OPTIONS ANOMALY DETECTOR 📊                   ║
    ║                                                       ║
    ║      Real-time options market anomaly detection      ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    """
    print(banner)
    print(f"    🕐 Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}")
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
    print(f"{'Rank':<6} {'Ticker':<8} {'Total Vol':<15} {'P/C Vol':<10} "
          f"{'Open Int':<15} {'P/C OI':<10} {'Put Vol':<12} {'Call Vol':<12}")
    print("-"*100)

    # Sort by volume
    sorted_data = sorted(data, key=lambda x: x['total_volume'], reverse=True)[:30]

    # Data rows
    for idx, item in enumerate(sorted_data, 1):
        print(f"{idx:<6} {item['ticker']:<8} {item['total_volume']:>14,} "
              f"{item['pc_volume_ratio']:>9.2f} {item['total_oi']:>14,} "
              f"{item['pc_oi_ratio']:>9.2f} {item['put_volume']:>11,} "
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
