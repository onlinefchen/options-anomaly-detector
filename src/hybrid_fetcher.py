#!/usr/bin/env python3
"""
Hybrid Data Fetcher Module
Combines CSV (volume) and API (open interest) for optimal performance
"""
import os
from typing import List, Dict, Optional
from data_fetcher import PolygonDataFetcher
from csv_handler import PolygonCSVHandler


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

        self.api_fetcher = PolygonDataFetcher(self.api_key)
        self.csv_handler = PolygonCSVHandler(self.api_key)

    def fetch_data(
        self,
        strategy: str = 'auto',
        top_n_for_oi: int = 30
    ) -> List[Dict]:
        """
        Fetch options data using optimal strategy

        Args:
            strategy: 'auto', 'csv', or 'api'
            top_n_for_oi: Number of top tickers to fetch OI for

        Returns:
            List of aggregated data dicts
        """
        print(f"\n{'='*80}")
        print(f"📡 DATA FETCHING STRATEGY")
        print(f"{'='*80}")

        if strategy == 'api':
            print(f"  Strategy: Pure API (forced)\n")
            return self._fetch_via_api()

        if strategy == 'csv':
            print(f"  Strategy: CSV only (forced)\n")
            success, data = self.csv_handler.try_download_and_parse()
            if success:
                return data
            else:
                print(f"\n  ⚠️  CSV fetch failed, falling back to API\n")
                return self._fetch_via_api()

        # Auto strategy: try CSV first
        print(f"  Strategy: AUTO (CSV → API → fallback)\n")
        return self._fetch_auto(top_n_for_oi)

    def _fetch_auto(self, top_n_for_oi: int) -> List[Dict]:
        """
        Auto strategy: intelligently choose best method

        Args:
            top_n_for_oi: Number of top tickers to enrich with OI

        Returns:
            List of aggregated data
        """
        # Step 1: Try CSV for volume data
        print(f"📦 STEP 1: Attempting CSV download for volume data")
        print(f"{'-'*80}")

        success, data = self.csv_handler.try_download_and_parse()

        if not success or not data:
            print(f"\n❌ CSV method failed or no data")
            print(f"📱 Falling back to pure API method...\n")
            return self._fetch_via_api()

        print(f"\n✅ CSV method successful!")
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
            oi_data = self.api_fetcher.get_options_chain(ticker)

            if oi_data.get('status') == 'OK':
                contracts = oi_data.get('results', [])

                put_oi = 0
                call_oi = 0

                for contract in contracts:
                    contract_type = contract.get('details', {}).get('contract_type')
                    oi = contract.get('open_interest', 0) or 0

                    if contract_type == 'put':
                        put_oi += oi
                    elif contract_type == 'call':
                        call_oi += oi

                total_oi = put_oi + call_oi
                pc_oi_ratio = round(put_oi / call_oi, 2) if call_oi > 0 else 0

                # Update item
                item['total_oi'] = total_oi
                item['put_oi'] = put_oi
                item['call_oi'] = call_oi
                item['pc_oi_ratio'] = pc_oi_ratio

                enriched_count += 1
                print(f"✓ OI={total_oi:,}")
            else:
                print(f"✗")

        print(f"\n✅ Enrichment complete: {enriched_count}/{top_n_for_oi} tickers")
        print(f"{'='*80}\n")

        return data

    def _fetch_via_api(self) -> List[Dict]:
        """
        Pure API strategy (fallback)

        Returns:
            List of aggregated data
        """
        print(f"📱 PURE API METHOD")
        print(f"{'-'*80}")
        print(f"   Fetching popular tickers...\n")

        tickers = self.api_fetcher.get_top_active_tickers(limit=48)
        data = self.api_fetcher.aggregate_options_by_underlying(tickers)

        print(f"\n✅ API fetch complete: {len(data)} tickers")
        print(f"{'='*80}\n")

        return data

    def get_strategy_info(self) -> Dict:
        """
        Get information about available strategies

        Returns:
            Dict with strategy information
        """
        has_csv = self.csv_handler.check_flat_files_access()

        return {
            'has_flat_files_access': has_csv,
            'recommended_strategy': 'auto' if has_csv else 'api',
            'available_strategies': ['auto', 'csv', 'api'] if has_csv else ['api']
        }
