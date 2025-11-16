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
import boto3
from botocore.client import Config
from utils import get_market_times
from options_utils import parse_option_ticker


class PolygonCSVHandler:
    """Handle CSV flat files from Polygon.io"""

    def __init__(self, api_key: str, s3_access_key: str = None, s3_secret_key: str = None):
        """
        Initialize CSV handler

        Args:
            api_key: Polygon.io API key
            s3_access_key: S3 Access Key ID (for Flat Files)
            s3_secret_key: S3 Secret Access Key (for Flat Files)
        """
        self.api_key = api_key
        self.base_url = "https://files.polygon.io"
        self.has_flat_files_access = None  # Will be detected

        # S3 credentials for Flat Files
        self.s3_access_key = s3_access_key or os.getenv('POLYGON_S3_ACCESS_KEY')
        self.s3_secret_key = s3_secret_key or os.getenv('POLYGON_S3_SECRET_KEY')
        self.s3_endpoint = "https://files.massive.com"
        self.s3_bucket = "flatfiles"

        # Initialize S3 client if credentials available
        self.s3_client = None
        if self.s3_access_key and self.s3_secret_key:
            try:
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=self.s3_endpoint,
                    aws_access_key_id=self.s3_access_key,
                    aws_secret_access_key=self.s3_secret_key,
                    config=Config(signature_version='s3v4')
                )
            except Exception as e:
                print(f"⚠️  Failed to initialize S3 client: {e}")

    def check_flat_files_access(self) -> bool:
        """
        Check if account has Flat Files access

        Returns:
            True if has access, False otherwise
        """
        if self.has_flat_files_access is not None:
            return self.has_flat_files_access

        # Prioritize S3 access if credentials available
        if self.s3_client:
            try:
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                s3_key = self._get_s3_key(yesterday)
                self.s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)
                self.has_flat_files_access = True
                return True
            except Exception:
                pass

        # Fallback to HTTP access
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

    def _get_s3_key(self, date: str) -> str:
        """
        Get S3 key for a specific date

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            S3 key path
        """
        year, month, _ = date.split('-')
        return f"us_options_opra/day_aggs_v1/{year}/{month}/{date}.csv.gz"

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

    def _get_local_csv_path(self, date: str) -> str:
        """
        Get local file path for CSV file

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Local file path
        """
        # Ensure data directory exists
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(data_dir, exist_ok=True)

        return os.path.join(data_dir, f"{date}_options_day_aggs.csv.gz")

    def _save_csv_to_disk(self, date: str, data: bytes) -> None:
        """
        Save CSV data to local disk

        Args:
            date: Date in YYYY-MM-DD format
            data: Compressed CSV data
        """
        local_file = self._get_local_csv_path(date)

        try:
            with open(local_file, 'wb') as f:
                f.write(data)
            size_mb = len(data) / 1024 / 1024
            print(f"  💾 Saved to disk: {local_file} ({size_mb:.1f} MB)")
        except Exception as e:
            print(f"  ⚠️  Failed to save to disk: {e}")

    def download_csv(self, date: Optional[str] = None, save_to_disk: bool = True) -> Optional[bytes]:
        """
        Download options day aggregates CSV file

        Args:
            date: Date in YYYY-MM-DD format (defaults to yesterday)
            save_to_disk: If True, save the downloaded file to data/ directory

        Returns:
            Compressed CSV data as bytes, or None if failed
        """
        if date is None:
            # Default to yesterday (data available next day ~11 AM ET)
            date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        # Get current market session to determine caching strategy
        time_info = get_market_times()
        market_session = time_info['session']
        is_market_hours = (market_session == 'market-hours')

        # Check if file already exists locally
        if save_to_disk:
            local_file = self._get_local_csv_path(date)
            if os.path.exists(local_file):
                # If in market hours, always re-download to get latest data
                if is_market_hours:
                    print(f"  📊 盘中时段检测到缓存文件，但需要重新下载以获取最新数据")
                    print(f"  🔄 删除旧缓存: {local_file}")
                    try:
                        os.remove(local_file)
                    except Exception as e:
                        print(f"  ⚠️  删除缓存失败: {e}")
                else:
                    # If not in market hours, use cache
                    print(f"  📂 {time_info['session_cn']}时段，使用本地缓存: {local_file}")
                    try:
                        with open(local_file, 'rb') as f:
                            data = f.read()
                        size_mb = len(data) / 1024 / 1024
                        print(f"  ✓ 从缓存加载 {size_mb:.1f} MB (节省下载时间)")
                        return data
                    except Exception as e:
                        print(f"  ⚠️  缓存读取失败: {e}, 重新下载...")

        # Try S3 download first if credentials available
        if self.s3_client:
            s3_key = self._get_s3_key(date)
            print(f"  📥 Downloading via S3 for {date}...")
            print(f"     Bucket: {self.s3_bucket}")
            print(f"     Key: {s3_key}")

            try:
                response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
                data = response['Body'].read()
                size_mb = len(data) / 1024 / 1024
                print(f"  ✓ Downloaded {size_mb:.1f} MB via S3")

                # Save to disk if requested
                if save_to_disk:
                    self._save_csv_to_disk(date, data)

                return data

            except self.s3_client.exceptions.NoSuchKey:
                print(f"  ✗ File not found in S3 - Data may not be ready yet")
                return None
            except Exception as e:
                print(f"  ✗ S3 download failed: {e}")
                print(f"  🔄 Falling back to HTTP download...")

        # Fallback to HTTP download
        url = self._get_csv_url(date)

        print(f"  📥 Downloading via HTTP for {date}...")
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

                # Save to disk if requested
                if save_to_disk:
                    self._save_csv_to_disk(date, data)

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

    def aggregate_by_underlying(self, df: pd.DataFrame, trading_date: Optional[str] = None) -> List[Dict]:
        """
        Aggregate options data by underlying ticker

        Args:
            df: DataFrame with columns [ticker, volume, ...]
            trading_date: Optional trading date in YYYY-MM-DD format for LEAP C/P calculation

        Returns:
            List of aggregated data dicts
        """
        print(f"  🔄 Aggregating data by underlying...")

        if df.empty:
            return []

        # Parse all tickers
        parsed_data = []
        for _, row in df.iterrows():
            parsed = parse_option_ticker(row['ticker'])
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

            # Calculate total transactions and average trade size
            total_transactions = underlying_df['transactions'].sum()
            avg_trade_size = round(total_volume / total_transactions, 1) if total_transactions > 0 else 0

            cp_ratio = round(call_volume / put_volume, 2) if put_volume > 0 else 0

            result = {
                'ticker': underlying,
                'total_volume': int(total_volume),
                'put_volume': int(put_volume),
                'call_volume': int(call_volume),
                'cp_volume_ratio': cp_ratio,
                'total_transactions': int(total_transactions),
                'avg_trade_size': avg_trade_size,
                'contracts_count': len(underlying_df),
                'put_contracts': len(put_df),
                'call_contracts': len(call_df),
                # OI data will be added later via API
                'total_oi': 0,
                'put_oi': 0,
                'call_oi': 0,
                'cp_oi_ratio': 0
            }

            # Calculate LEAP C/P ratio if trading_date is provided
            if trading_date:
                leap_cp = self._calculate_leap_cp_from_contracts(underlying_df, trading_date)
                result['leap_cp_ratio'] = leap_cp

            # Collect Top 3 contracts by volume and Top 3 LEAP by volume
            top_3_volume, top_3_leap_volume = self._get_top_contracts_by_volume(
                underlying_df, trading_date, total_volume
            )
            result['top_3_contracts_volume'] = top_3_volume
            result['top_3_leap_volume'] = top_3_leap_volume

            results.append(result)

        # Sort by volume
        results = sorted(results, key=lambda x: x['total_volume'], reverse=True)

        print(f"  ✓ Aggregated {len(results)} unique tickers")
        return results

    def _calculate_leap_cp_from_contracts(self, contracts_df: pd.DataFrame, trading_date: str) -> float:
        """
        Calculate LEAP C/P ratio from contract DataFrame

        Args:
            contracts_df: DataFrame with parsed contract data (expiry, contract_type, volume)
            trading_date: Trading date in YYYY-MM-DD format

        Returns:
            C/P ratio for LEAP options (0 if no LEAP puts found)
        """
        from datetime import datetime, timedelta

        # Calculate the 3-month threshold date
        date_obj = datetime.strptime(trading_date, '%Y-%m-%d')
        leap_threshold = date_obj + timedelta(days=90)  # ~3 months

        leap_call_volume = 0
        leap_put_volume = 0

        for _, contract in contracts_df.iterrows():
            expiry_str = contract.get('expiry')
            contract_type = contract.get('contract_type')
            volume = contract.get('volume', 0) or 0

            if not expiry_str or not contract_type:
                continue

            try:
                # Parse expiry date (YYMMDD format)
                # Convert to YYYY-MM-DD
                expiry_date = datetime.strptime(f'20{expiry_str}', '%Y%m%d')

                # Check if this is a LEAP (expires 3+ months out)
                if expiry_date >= leap_threshold:
                    if contract_type == 'call':
                        leap_call_volume += volume
                    elif contract_type == 'put':
                        leap_put_volume += volume
            except (ValueError, TypeError):
                continue

        # Calculate C/P ratio
        if leap_put_volume == 0:
            return 0.0

        return round(leap_call_volume / leap_put_volume, 2)

    def _get_top_contracts_by_volume(
        self,
        contracts_df: pd.DataFrame,
        trading_date: str,
        total_volume: int
    ) -> tuple:
        """
        Get Top 3 contracts by volume and Top 3 LEAP contracts by volume

        Args:
            contracts_df: DataFrame with parsed contract data (expiry, contract_type, volume, strike)
            trading_date: Trading date in YYYY-MM-DD format
            total_volume: Total volume for percentage calculation

        Returns:
            Tuple of (top_3_contracts_volume, top_3_leap_volume)
        """
        from datetime import datetime, timedelta

        # Calculate the 3-month threshold date
        date_obj = datetime.strptime(trading_date, '%Y-%m-%d')
        leap_threshold = date_obj + timedelta(days=90)

        # Collect all contracts with volume
        all_contracts = []
        leap_contracts = []

        for _, contract in contracts_df.iterrows():
            volume = contract.get('volume', 0) or 0
            if volume == 0:
                continue

            expiry_str = contract.get('expiry')
            contract_type = contract.get('contract_type')
            strike = contract.get('strike')

            if not expiry_str or not contract_type:
                continue

            # Format contract ticker: YYMMDD + C/P + strike
            # e.g., "251205C480" for Dec 5, 2025, Call at $480
            contract_type_letter = 'C' if contract_type == 'call' else 'P'
            ticker = f"{expiry_str}{contract_type_letter}{int(strike)}"

            contract_info = {
                'ticker': ticker,
                'volume': volume,
                'strike': strike,
                'expiry': expiry_str,
                'type': contract_type,
                'percentage': round(volume / total_volume * 100, 1) if total_volume > 0 else 0
            }

            all_contracts.append(contract_info)

            # Check if this is a LEAP (expires 3+ months out)
            try:
                # Parse expiry date (YYMMDD format)
                expiry_date = datetime.strptime(f'20{expiry_str}', '%Y%m%d')
                if expiry_date >= leap_threshold:
                    leap_contracts.append(contract_info)
            except (ValueError, TypeError):
                pass

        # Get Top 3 by volume
        top_3_contracts = sorted(all_contracts, key=lambda x: x['volume'], reverse=True)[:3]
        top_3_leap = sorted(leap_contracts, key=lambda x: x['volume'], reverse=True)[:3]

        return top_3_contracts, top_3_leap

    def get_latest_trading_day(self) -> str:
        """
        Get the most recent trading day based on US Eastern Time

        Logic:
        - Convert current time to US Eastern Time
        - Go back 1 day to get yesterday's trading day (CSV available next day)
        - Skip weekends to find the latest trading day

        Returns:
            Date string in YYYY-MM-DD format
        """
        import pytz

        # Get current time in US Eastern timezone
        eastern = pytz.timezone('US/Eastern')
        now_eastern = datetime.now(pytz.utc).astimezone(eastern)

        # Go back 1 day (CSV for trading day N is available on day N+1)
        check_date = now_eastern - timedelta(days=1)

        # Skip weekends: if yesterday was Sunday (6), go back to Friday
        # if yesterday was Saturday (5), go back to Friday
        while check_date.weekday() in [5, 6]:  # Saturday=5, Sunday=6
            check_date -= timedelta(days=1)

        result = check_date.strftime('%Y-%m-%d')
        print(f"  🌍 Current US Eastern Time: {now_eastern.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"  📅 Target trading day: {result} ({check_date.strftime('%A')})")

        return result

    def try_download_and_parse(
        self,
        date: Optional[str] = None,
        max_retries: int = 3
    ) -> Tuple[bool, List[Dict], Optional[str]]:
        """
        Try to download and parse CSV data with retries

        Logic:
        - First attempt: Try latest trading day (based on US Eastern Time)
        - If failed: Try previous trading days (up to max_retries times)
        - Automatically skips weekends

        Args:
            date: Date string or None to auto-detect latest trading day
            max_retries: Number of trading days to try (default: 3)

        Returns:
            Tuple of (success, data, date_used)
        """
        if date is None:
            # Auto-detect latest trading day based on US Eastern Time
            used_date = self.get_latest_trading_day()
        else:
            used_date = date
            print(f"  📅 Using specified date: {used_date}")

        for attempt in range(max_retries):
            if attempt > 0:
                print(f"  🔄 Retry attempt {attempt + 1}/{max_retries}")

                # Try previous trading day
                check_date = datetime.strptime(used_date, '%Y-%m-%d')
                check_date -= timedelta(days=1)

                # Skip weekends
                while check_date.weekday() in [5, 6]:
                    check_date -= timedelta(days=1)

                used_date = check_date.strftime('%Y-%m-%d')
                print(f"  💡 Trying previous trading day: {used_date} ({check_date.strftime('%A')})")

            # Download
            csv_data = self.download_csv(used_date)
            if csv_data is None:
                print(f"  ✗ Failed to download CSV for {used_date}")
                continue

            # Parse
            df = self.parse_csv(csv_data)
            if df.empty:
                print(f"  ✗ CSV file is empty for {used_date}")
                continue

            # Aggregate (with LEAP C/P calculation based on CSV data)
            results = self.aggregate_by_underlying(df, trading_date=used_date)
            if results:
                print(f"  ✅ Successfully loaded data for {used_date}")
                return True, results, used_date

        print(f"  ❌ Failed to get CSV data after {max_retries} attempts")
        return False, [], None
