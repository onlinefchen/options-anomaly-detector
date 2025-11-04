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
from trading_calendar import get_previous_trading_day, has_trading_days_between


def main():
    """Main execution function"""

    # Load environment variables
    load_dotenv()

    # Print banner
    print_banner()

    try:
        # Algorithm 1: Determine csv_date (previous completed trading day)
        print_progress("📅 Determining target CSV date...")
        current_date = datetime.now().strftime('%Y-%m-%d')
        csv_date = get_previous_trading_day(from_date=current_date)
        print_progress(f"   • Current date: {current_date}")
        print_progress(f"   • Target CSV date: {csv_date}")
        print_progress(f"   • CSV file: {csv_date}.csv.gz\n")

        # Check if this CSV date's data already exists (restored from gh-pages)
        json_file = f'output/{csv_date}.json'
        if os.path.exists(json_file):
            print_progress(f"📦 Found existing data for {csv_date}")
            print_progress(f"   • File: {json_file}")
            print_progress("   • Data already processed and published")
            print_progress("   • Skipping analysis (nothing to do)\n")

            print("\n" + "="*80)
            print("ℹ️  Data Already Exists")
            print("="*80)
            print(f"\n📋 Status:")
            print(f"   • CSV date: {csv_date}")
            print(f"   • Data file: {json_file}")
            print(f"   • Already published to gh-pages")
            print(f"\n💡 No action needed - data is already up to date.")
            print("="*80 + "\n")

            return 0

        # If no existing data, proceed with full analysis
        print_progress(f"🆕 No existing data for {csv_date}, proceeding with analysis\n")

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

        # Download CSV for csv_date
        print_progress(f"📥 Downloading CSV data for {csv_date}...")
        success, data, actual_csv_date = fetcher.csv_handler.try_download_and_parse(date=csv_date, max_retries=1)

        if not success or not data:
            print_progress(f"⊘ CSV download failed for {csv_date}")
            print_progress("   • CSV file not found or inaccessible")
            print_progress("   • Skipping analysis\n")

            print("\n" + "="*80)
            print("⏰ CSV Not Yet Available")
            print("="*80)
            print(f"\n📋 Details:")
            print(f"   • Target CSV date: {csv_date}")
            print(f"   • CSV file expected: {csv_date}.csv.gz")
            print(f"   • The CSV file may not be uploaded yet (post-market processing)")
            print(f"\n💡 Next hourly run will retry automatically.")
            print(f"   Analysis will complete when CSV becomes available.")
            print("="*80 + "\n")
            return 0  # Return success to allow workflow to continue

        print_progress(f"✓ CSV data downloaded successfully")
        print_progress(f"   • CSV date: {actual_csv_date}")
        print_progress(f"   • Tickers: {len(data)}\n")

        # Algorithm 2: Determine if OI should be fetched
        print_progress("🔍 Checking if Open Interest data should be fetched...")
        should_fetch_oi = not has_trading_days_between(csv_date, current_date)

        if should_fetch_oi:
            print_progress(f"   ✓ No new trading days between {csv_date} and {current_date}")
            print_progress(f"   → OI data is meaningful (reflects market state at/after {csv_date} close)")
            print_progress(f"   → Fetching OI for top 35 tickers...\n")

            # Enrich with OI data from API (includes LEAP C/P calculation)
            print_progress("📡 Enriching with Open Interest data from API...")
            data, metadata = fetcher.enrich_with_oi(data, top_n=35, trading_date=csv_date)
            print_progress(f"✓ OI enrichment complete")
            print_progress(f"   • Data source: {metadata.get('data_source', 'CSV+API')}\n")
        else:
            print_progress(f"   ⊘ New trading days exist between {csv_date} and {current_date}")
            print_progress(f"   → OI data would be from today (not meaningful for historical {csv_date})")
            print_progress(f"   → Skipping OI enrichment\n")

            metadata = {
                'data_source': 'CSV',
                'csv_date': actual_csv_date,
                'oi_skipped': 'historical_data',
                'oi_skip_reason': f'New trading days exist between {csv_date} and {current_date}'
            }

            # Even if OI is skipped, still calculate LEAP C/P ratio (volume-based)
            print_progress("📊 Calculating LEAP C/P ratios (volume-based)...")
            data, leap_count = fetcher.enrich_with_leap_cp(data, top_n=35, trading_date=csv_date)
            print_progress(f"✓ LEAP C/P calculation complete")
            print_progress(f"   • Enriched {leap_count} tickers with LEAP C/P data\n")

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
        data_source = metadata.get('data_source', 'CSV')
        historical_data = {
            'date': csv_date,  # CSV date (data date)
            'generated_at': datetime.now().isoformat(),  # When report was generated
            'tickers_count': len(data),
            'anomalies_count': summary['total'],
            'data_source': data_source,
            'data': data,
            'anomalies': anomalies,
            'summary': summary,
            'metadata': metadata  # Include full metadata (OI skip info, etc.)
        }

        json_file = f'output/{csv_date}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(historical_data, f, ensure_ascii=False, indent=2)
        print_progress(f"✓ Raw data saved: {json_file}")

        # Copy current report to dated version
        import shutil
        dated_report = f'output/{csv_date}.html'
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
