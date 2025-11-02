#!/usr/bin/env python3
"""
Hybrid Data Fetcher Module
Combines CSV (volume) and API (open interest) for optimal performance
"""
import os
from typing import List, Dict, Optional
from data_fetcher import PolygonDataFetcher
from csv_handler import PolygonCSVHandler
from options_utils import aggregate_oi_from_contracts


class HybridDataFetcher:
    """
    Hybrid data fetching strategy:
    1. Try CSV for volume data (fast, complete)
    2. Use API for top N tickers to get OI (targeted, efficient)
    3. Fall back to pure API if CSV unavailable
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize hybrid fetcher

        Args:
            api_key: Polygon.io API key
        """
        self.api_key = api_key or os.getenv('POLYGON_API_KEY')
        if not self.api_key or self.api_key == 'YOUR_API_KEY_HERE':
            raise ValueError("POLYGON_API_KEY not set")

        # Get S3 credentials for Flat Files
        s3_access_key = os.getenv('POLYGON_S3_ACCESS_KEY')
        s3_secret_key = os.getenv('POLYGON_S3_SECRET_KEY')

        self.api_fetcher = PolygonDataFetcher(self.api_key)
        self.csv_handler = PolygonCSVHandler(self.api_key, s3_access_key, s3_secret_key)

    def fetch_data(
        self,
        strategy: str = 'auto',
        top_n_for_oi: int = 30
    ):
        """
        Fetch options data using CSV as primary source

        Args:
            strategy: 'auto' or 'csv' (both use CSV)
            top_n_for_oi: Number of top tickers to fetch OI for

        Returns:
            Tuple of (data, metadata) where:
            - data: List of aggregated data dicts
            - metadata: Dict with 'data_source' key ('CSV' or 'CSV+API')
        """
        print(f"\n{'='*80}")
        print(f"📡 DATA FETCHING STRATEGY")
        print(f"{'='*80}")

        if strategy == 'csv':
            print(f"  Strategy: CSV only (forced)\n")
            success, data, csv_date = self.csv_handler.try_download_and_parse()
            if success:
                return data, {'data_source': 'CSV', 'csv_date': csv_date}
            else:
                print(f"\n  ❌ CSV fetch failed - no fallback available\n")
                return [], {'data_source': 'FAILED', 'error': 'CSV unavailable'}

        # Auto strategy: CSV + optional OI enrichment
        print(f"  Strategy: AUTO (CSV + OI enrichment)\n")
        return self._fetch_auto(top_n_for_oi)

    def _fetch_auto(self, top_n_for_oi: int):
        """
        Auto strategy: CSV for volume + API for OI enrichment

        Args:
            top_n_for_oi: Number of top tickers to enrich with OI

        Returns:
            Tuple of (data, metadata)
        """
        # Step 1: Get CSV data (required)
        print(f"📦 STEP 1: Downloading CSV for volume data")
        print(f"{'-'*80}")

        success, data, csv_date = self.csv_handler.try_download_and_parse()

        if not success or not data:
            print(f"\n❌ CSV download failed or no data available")
            print(f"   Cannot proceed without CSV data")
            return [], {'data_source': 'FAILED', 'error': 'CSV unavailable'}

        print(f"\n✅ CSV download successful!")
        print(f"   • Total tickers: {len(data)}")
        print(f"   • Total volume: {sum(d['total_volume'] for d in data):,}")

        # Step 2: Enrich top N with OI via API
        print(f"\n📊 STEP 2: Enriching top {top_n_for_oi} tickers with Open Interest")
        print(f"{'-'*80}")

        top_tickers = [d['ticker'] for d in data[:top_n_for_oi]]
        print(f"   Fetching OI for: {', '.join(top_tickers[:10])}" +
              (f"... (+{len(top_tickers)-10} more)" if len(top_tickers) > 10 else ""))
        print()

        enriched_count = 0
        for idx, item in enumerate(data[:top_n_for_oi], 1):
            ticker = item['ticker']
            print(f"   [{idx}/{top_n_for_oi}] {ticker}...", end=' ')

            # Fetch OI from API
            api_response = self.api_fetcher.get_options_chain(ticker)

            if api_response.get('status') == 'OK':
                contracts = api_response.get('results', [])

                # Use centralized OI aggregation utility
                oi_data = aggregate_oi_from_contracts(contracts)

                # Update item with OI data
                item.update(oi_data)

                enriched_count += 1
                print(f"✓ OI={oi_data['total_oi']:,}")
            else:
                print(f"✗")

        print(f"\n✅ Enrichment complete: {enriched_count}/{top_n_for_oi} tickers")
        print(f"{'='*80}\n")

        return data, {'data_source': 'CSV+API', 'csv_date': csv_date}

    def get_strategy_info(self) -> Dict:
        """
        Get information about available strategies

        Returns:
            Dict with strategy information
        """
        has_csv = self.csv_handler.check_flat_files_access()

        return {
            'has_flat_files_access': has_csv,
            'recommended_strategy': 'auto' if has_csv else 'csv',
            'available_strategies': ['auto', 'csv']
        }

    def enrich_with_oi(self, data: List[Dict], top_n: int = 30):
        """
        Enrich top N tickers with Open Interest data from API

        Args:
            data: List of ticker data dicts (must be pre-sorted by volume)
            top_n: Number of top tickers to enrich with OI data

        Returns:
            Tuple of (enriched_data, metadata)
        """
        enriched_count = 0

        for idx, item in enumerate(data[:top_n], 1):
            ticker = item['ticker']

            # Fetch OI from API
            api_response = self.api_fetcher.get_options_chain(ticker)

            if api_response.get('status') == 'OK':
                contracts = api_response.get('results', [])

                # Use centralized OI aggregation utility
                oi_data = aggregate_oi_from_contracts(contracts)

                # Update item with OI data
                item.update(oi_data)

                enriched_count += 1

        return data, {'data_source': 'CSV+API'}
