#!/usr/bin/env python3
"""
CSV Handler Module
Downloads and parses Polygon.io Flat Files for options data
"""
import os
import re
import gzip
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import requests


class PolygonCSVHandler:
    """Handle CSV flat files from Polygon.io"""

    def __init__(self, api_key: str):
        """
        Initialize CSV handler

        Args:
            api_key: Polygon.io API key (may also serve as S3 access key)
        """
        self.api_key = api_key
        self.base_url = "https://files.polygon.io"
        self.has_flat_files_access = None  # Will be detected

    def check_flat_files_access(self) -> bool:
        """
        Check if account has Flat Files access

        Returns:
            True if has access, False otherwise
        """
        if self.has_flat_files_access is not None:
            return self.has_flat_files_access

        # Try to access a recent file
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        test_url = self._get_csv_url(yesterday)

        try:
            response = requests.head(
                test_url,
                auth=(self.api_key, ''),
                timeout=10
            )
            self.has_flat_files_access = response.status_code == 200
            return self.has_flat_files_access
        except Exception:
            self.has_flat_files_access = False
            return False

    def _get_csv_url(self, date: str) -> str:
        """
        Get CSV file URL for a specific date

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Full URL to CSV file
        """
        year, month, day = date.split('-')
        return f"{self.base_url}/flatfiles/us_options_opra/day_aggs_v1/{year}/{month}/{date}.csv.gz"

    def download_csv(self, date: Optional[str] = None) -> Optional[bytes]:
        """
        Download options day aggregates CSV file

        Args:
            date: Date in YYYY-MM-DD format (defaults to yesterday)

        Returns:
            Compressed CSV data as bytes, or None if failed
        """
        if date is None:
            # Default to yesterday (data available next day ~11 AM ET)
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        url = self._get_csv_url(date)

        print(f"  📥 Downloading CSV for {date}...")
        print(f"     URL: {url}")

        try:
            response = requests.get(
                url,
                auth=(self.api_key, ''),
                stream=True,
                timeout=30
            )

            if response.status_code == 200:
                data = response.content
                size_mb = len(data) / 1024 / 1024
                print(f"  ✓ Downloaded {size_mb:.1f} MB")
                return data
            elif response.status_code == 403:
                print(f"  ✗ Access denied (403) - Flat Files not available in your plan")
                return None
            elif response.status_code == 404:
                print(f"  ✗ File not found (404) - Data may not be ready yet")
                return None
            else:
                print(f"  ✗ Error {response.status_code}")
                return None

        except Exception as e:
            print(f"  ✗ Download failed: {e}")
            return None

    def parse_option_ticker(self, ticker: str) -> Optional[Dict]:
        """
        Parse option ticker to extract information

        Format: O:SPY251219C00600000

        Args:
            ticker: Option ticker string

        Returns:
            Dict with parsed info or None
        """
        pattern = r'O:([A-Z]+)(\d{6})([CP])(\d+)'
        match = re.match(pattern, ticker)

        if match:
            return {
                'underlying': match.group(1),
                'expiry': match.group(2),
                'contract_type': 'call' if match.group(3) == 'C' else 'put',
                'strike': int(match.group(4)) / 1000
            }
        return None

    def parse_csv(self, csv_data: bytes) -> pd.DataFrame:
        """
        Parse compressed CSV data

        Args:
            csv_data: Compressed CSV data

        Returns:
            Parsed DataFrame
        """
        print(f"  📊 Parsing CSV data...")

        try:
            # Decompress
            decompressed = gzip.decompress(csv_data)

            # Read CSV
            df = pd.read_csv(io.BytesIO(decompressed))

            print(f"  ✓ Parsed {len(df):,} contracts")
            return df

        except Exception as e:
            print(f"  ✗ Parse error: {e}")
            return pd.DataFrame()

    def aggregate_by_underlying(self, df: pd.DataFrame) -> List[Dict]:
        """
        Aggregate options data by underlying ticker

        Args:
            df: DataFrame with columns [ticker, volume, ...]

        Returns:
            List of aggregated data dicts
        """
        print(f"  🔄 Aggregating data by underlying...")

        if df.empty:
            return []

        # Parse all tickers
        parsed_data = []
        for _, row in df.iterrows():
            parsed = self.parse_option_ticker(row['ticker'])
            if parsed:
                parsed['volume'] = row.get('volume', 0) or 0
                parsed['transactions'] = row.get('transactions', 0) or 0
                parsed_data.append(parsed)

        if not parsed_data:
            return []

        parsed_df = pd.DataFrame(parsed_data)

        # Group by underlying
        results = []
        for underlying in parsed_df['underlying'].unique():
            underlying_df = parsed_df[parsed_df['underlying'] == underlying]

            put_df = underlying_df[underlying_df['contract_type'] == 'put']
            call_df = underlying_df[underlying_df['contract_type'] == 'call']

            put_volume = put_df['volume'].sum()
            call_volume = call_df['volume'].sum()
            total_volume = put_volume + call_volume

            # Skip if no volume
            if total_volume == 0:
                continue

            cp_ratio = round(call_volume / put_volume, 2) if put_volume > 0 else 0

            results.append({
                'ticker': underlying,
                'total_volume': int(total_volume),
                'put_volume': int(put_volume),
                'call_volume': int(call_volume),
                'cp_volume_ratio': cp_ratio,
                'contracts_count': len(underlying_df),
                'put_contracts': len(put_df),
                'call_contracts': len(call_df),
                # OI data will be added later via API
                'total_oi': 0,
                'put_oi': 0,
                'call_oi': 0,
                'cp_oi_ratio': 0
            })

        # Sort by volume
        results = sorted(results, key=lambda x: x['total_volume'], reverse=True)

        print(f"  ✓ Aggregated {len(results)} unique tickers")
        return results

    def try_download_and_parse(
        self,
        date: Optional[str] = None,
        max_retries: int = 2
    ) -> Tuple[bool, List[Dict]]:
        """
        Try to download and parse CSV data with retries

        Args:
            date: Date string or None for yesterday
            max_retries: Number of retry attempts

        Returns:
            Tuple of (success, data)
        """
        for attempt in range(max_retries):
            if attempt > 0:
                print(f"  🔄 Retry attempt {attempt + 1}/{max_retries}")

                # If first attempt failed, try day before yesterday
                if date is None:
                    retry_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
                    print(f"  💡 Trying previous day: {retry_date}")
                    date = retry_date

            # Download
            csv_data = self.download_csv(date)
            if csv_data is None:
                continue

            # Parse
            df = self.parse_csv(csv_data)
            if df.empty:
                continue

            # Aggregate
            results = self.aggregate_by_underlying(df)
            if results:
                return True, results

        return False, []
