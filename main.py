#!/usr/bin/env python3
"""
Options Anomaly Detector - Main Entry Point

Analyzes options market data to detect anomalies and generate reports
"""
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from hybrid_fetcher import HybridDataFetcher
from anomaly_detector import OptionsAnomalyDetector
from report_generator import HTMLReportGenerator
from archive_index_generator import get_archived_reports, generate_archive_index
from history_analyzer import HistoryAnalyzer
from utils import print_banner, print_summary_table, print_anomalies_summary, print_progress


def main():
    """Main execution function"""

    # Load environment variables
    load_dotenv()

    # Print banner
    print_banner()

    try:
        # Generate date stamp
        date_str = datetime.now().strftime('%Y-%m-%d')
        json_file = f'output/{date_str}.json'

        # Check if today's data already exists (restored from gh-pages)
        if os.path.exists(json_file):
            print_progress(f"📦 Found existing data for {date_str}")
            print_progress(f"   • File: {json_file}")
            print_progress("   • Data already processed and published")
            print_progress("   • Skipping analysis (nothing to do)\n")

            print("\n" + "="*80)
            print("ℹ️  Data Already Exists")
            print("="*80)
            print(f"\n📋 Status:")
            print(f"   • Date: {date_str}")
            print(f"   • Data file: {json_file}")
            print(f"   • Already published to gh-pages")
            print(f"\n💡 No action needed - data is already up to date.")
            print("="*80 + "\n")

            return 0

        # If no existing data, proceed with full analysis
        print_progress(f"🆕 No existing data for {date_str}, proceeding with full analysis\n")

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

        # Fetch options data using CSV (no API fallback)
        # Try to download CSV for today
        print_progress("📥 Checking for CSV data...")
        today = datetime.now().strftime('%Y-%m-%d')
        success, data, csv_date = fetcher.csv_handler.try_download_and_parse(date=today, max_retries=1)

        if not success or not data:
            print_progress(f"⊘ No CSV data available for {today}")
            print_progress("   • CSV file not found (likely a non-trading day)")
            print_progress("   • Skipping analysis - will only generate reports for days with CSV data\n")

            print("\n" + "="*80)
            print("ℹ️  No Analysis Performed")
            print("="*80)
            print(f"\n📋 Reason:")
            print(f"   • No CSV data available for {today}")
            print(f"   • This is expected for weekends, holidays, and days before market close")
            print(f"\n💡 Analysis will run automatically when CSV data becomes available.")
            print("="*80 + "\n")
            return 0

        # CSV data found - enrich with OI data from API
        print_progress(f"✓ CSV data found for {csv_date}")
        print_progress(f"   • Downloaded {len(data)} tickers from CSV")

        # Enrich top tickers with OI data from API
        print_progress("📡 Enriching top 30 tickers with Open Interest data from API...")
        data, metadata = fetcher.enrich_with_oi(data, top_n=30)
        print_progress(f"✓ Successfully enriched data")
        print_progress(f"   • Data source: {metadata.get('data_source', 'CSV+API')}\n")

        # Analyze historical activity
        print_progress("📊 Analyzing historical activity (past 10 trading days)...")
        analyzer = HistoryAnalyzer(output_dir='output', lookback_days=10)
        data = analyzer.enrich_data_with_history(data)
        print_progress("✓ Historical analysis complete\n")

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
        reporter.generate(data, anomalies, summary, metadata=metadata)

        # Archive historical data
        print_progress("💾 Archiving historical data...")

        # Save raw data as JSON
        data_source = metadata.get('data_source', 'CSV+API')
        historical_data = {
            'date': date_str,
            'timestamp': datetime.now().isoformat(),
            'tickers_count': len(data),
            'anomalies_count': summary['total'],
            'data_source': data_source,
            'data': data,
            'anomalies': anomalies,
            'summary': summary
        }

        json_file = f'output/{date_str}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(historical_data, f, ensure_ascii=False, indent=2)
        print_progress(f"✓ Raw data saved: {json_file}")

        # Copy current report to dated version
        import shutil
        dated_report = f'output/{date_str}.html'
        shutil.copy2('output/anomaly_report.html', dated_report)
        print_progress(f"✓ Historical report saved: {dated_report}")

        # Generate archive index page
        print_progress("📚 Generating archive index...")
        reports = get_archived_reports()
        generate_archive_index(reports)
        print_progress(f"✓ Archive index updated ({len(reports)} reports)\n")

        # Success message
        print("\n" + "="*80)
        print("✅ Analysis Complete!")
        print("="*80)
        print(f"\n📊 Results:")
        print(f"   • Tickers analyzed: {len(data)}")
        print(f"   • Anomalies detected: {summary['total']}")
        print(f"   • Latest report: output/index.html")
        print(f"   • Historical report: {dated_report}")
        print(f"   • Raw data: {json_file}")
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
