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

from data_fetcher import PolygonDataFetcher
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
        fetcher = PolygonDataFetcher()
        detector = OptionsAnomalyDetector()
        reporter = HTMLReportGenerator()
        print_progress("✓ Initialization complete\n")

        # Get list of tickers to analyze
        print_progress("📋 Getting list of active tickers...")
        tickers = fetcher.get_top_active_tickers(limit=50)
        print_progress(f"✓ Analyzing {len(tickers)} tickers\n")

        # Fetch options data
        print_progress("📡 Fetching options data from Polygon.io...\n")
        data = fetcher.aggregate_options_by_underlying(tickers)

        if not data:
            print("\n❌ Error: No data fetched. Check your API key and network connection.")
            return 1

        print_progress(f"\n✓ Successfully fetched data for {len(data)} tickers\n")

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
