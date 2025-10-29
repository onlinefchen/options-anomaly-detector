#!/usr/bin/env python3
"""
Options Anomaly Detector - Main Entry Point

Analyzes options market data to detect anomalies and generate reports
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from hybrid_fetcher import HybridDataFetcher
from anomaly_detector import OptionsAnomalyDetector
from report_generator import HTMLReportGenerator
from utils import print_banner, print_summary_table, print_anomalies_summary, print_progress


def main():
    """Main execution function"""

    # Load environment variables
    load_dotenv()

    # Print banner
    print_banner()

    try:
        # Initialize components
        print_progress("🔧 Initializing components...")
        fetcher = HybridDataFetcher()
        detector = OptionsAnomalyDetector()
        reporter = HTMLReportGenerator()
        print_progress("✓ Initialization complete\n")

        # Check strategy
        strategy_info = fetcher.get_strategy_info()
        print_progress(f"📋 Data access capabilities:")
        print_progress(f"   • Flat Files access: {'✓' if strategy_info['has_flat_files_access'] else '✗'}")
        print_progress(f"   • Recommended strategy: {strategy_info['recommended_strategy'].upper()}\n")

        # Fetch options data using hybrid strategy
        data = fetcher.fetch_data(strategy='auto', top_n_for_oi=30)

        if not data:
            print("\n❌ Error: No data fetched. Check your API key and network connection.")
            return 1

        print_progress(f"✓ Successfully fetched data for {len(data)} tickers\n")

        # Detect anomalies
        print_progress("🔍 Detecting anomalies...")
        anomalies = detector.detect_all_anomalies(data)
        summary = detector.get_summary()
        print_progress(f"✓ Detected {summary['total']} anomalies\n")

        # Print terminal output
        print_summary_table(data)
        print_anomalies_summary(anomalies, summary)

        # Generate HTML report
        print_progress("📄 Generating HTML report...")
        os.makedirs('output', exist_ok=True)
        reporter.generate(data, anomalies, summary)

        # Success message
        print("\n" + "="*80)
        print("✅ Analysis Complete!")
        print("="*80)
        print(f"\n📊 Results:")
        print(f"   • Tickers analyzed: {len(data)}")
        print(f"   • Anomalies detected: {summary['total']}")
        print(f"   • Report: output/anomaly_report.html")
        print(f"\n💡 View the HTML report in your browser for detailed charts and analysis.")
        print("="*80 + "\n")

        return 0

    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\n💡 Please set POLYGON_API_KEY in .env file or environment variable")
        return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
