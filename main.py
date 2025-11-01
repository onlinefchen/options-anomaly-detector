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
            print_progress(f"   • Loading from: {json_file}")
            print_progress("   • Skipping data fetch to save API quota\n")

            # Load existing data
            with open(json_file, 'r', encoding='utf-8') as f:
                historical_data = json.load(f)

            data = historical_data.get('data', [])
            anomalies = historical_data.get('anomalies', [])
            summary = historical_data.get('summary', {})
            metadata = {
                'data_source': historical_data.get('data_source', 'CSV'),
                'csv_date': historical_data.get('date', date_str)
            }

            print_progress(f"✓ Loaded {len(data)} tickers from existing data\n")

            # Generate HTML report from existing data
            print_progress("📄 Generating HTML report from existing data...")
            os.makedirs('output', exist_ok=True)
            reporter = HTMLReportGenerator()
            reporter.generate(data, anomalies, summary, metadata=metadata)

            # Copy current report to dated version
            import shutil
            dated_report = f'output/{date_str}.html'
            shutil.copy2('output/anomaly_report.html', dated_report)
            print_progress(f"✓ HTML report saved: {dated_report}")

            # Generate archive index page
            print_progress("📚 Generating archive index...")
            reports = get_archived_reports()
            generate_archive_index(reports)
            print_progress(f"✓ Archive index updated ({len(reports)} reports)\n")

            # Success message
            print("\n" + "="*80)
            print("✅ Report Generated from Existing Data!")
            print("="*80)
            print(f"\n📊 Results:")
            print(f"   • Tickers: {len(data)}")
            print(f"   • Anomalies: {summary.get('total', 0)}")
            print(f"   • Report: output/index.html")
            print(f"   • Data source: {metadata.get('data_source', 'Unknown')}")
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

        # Fetch options data using hybrid strategy
        # Use top_n_for_oi=30 to ensure we get OI data for top 25 stocks after excluding 3-5 indices
        data, metadata = fetcher.fetch_data(strategy='auto', top_n_for_oi=30)

        if not data:
            print("\n❌ Error: No data fetched. Check your API key and network connection.")
            return 1

        print_progress(f"✓ Successfully fetched data for {len(data)} tickers")
        print_progress(f"   • Data source: {metadata.get('data_source', 'Unknown')}\n")

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

        # Only save JSON file if data is from CSV (not API-only)
        data_source = metadata.get('data_source', 'Unknown')
        if data_source in ['CSV', 'CSV+API']:
            # Save raw data as JSON
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
        else:
            print_progress(f"⊘ Skipping JSON save (data source: {data_source}, CSV required)")

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
