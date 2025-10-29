#!/usr/bin/env python3
"""
Data Fetcher Module
Fetches options data from Polygon.io API
"""
import os
import requests
import time
from typing import Dict, List, Optional
import re


class PolygonDataFetcher:
    """Fetch options data from Polygon.io"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the data fetcher

        Args:
            api_key: Polygon.io API key (defaults to env variable)
        """
        self.api_key = api_key or os.getenv('POLYGON_API_KEY')
        if not self.api_key or self.api_key == 'YOUR_API_KEY_HERE':
            raise ValueError("POLYGON_API_KEY not set")

        self.base_url = "https://api.polygon.io"
        self.session = requests.Session()

    def parse_option_ticker(self, ticker: str) -> Optional[Dict]:
        """
        Parse option ticker to extract underlying, expiry, type, strike

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

    def get_options_chain(self, ticker: str) -> Dict:
        """
        Get options chain snapshot for a ticker

        Args:
            ticker: Stock ticker (e.g., 'SPY')

        Returns:
            Dict containing options chain data
        """
        url = f"{self.base_url}/v3/snapshot/options/{ticker}"
        params = {'apiKey': self.api_key}

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching options chain for {ticker}: {e}")
            return {'status': 'ERROR', 'results': []}

    def aggregate_options_by_underlying(self, tickers: List[str]) -> List[Dict]:
        """
        Aggregate options data for multiple tickers

        Args:
            tickers: List of stock tickers

        Returns:
            List of aggregated data dictionaries
        """
        results = []
        total = len(tickers)

        for idx, ticker in enumerate(tickers, 1):
            print(f"  [{idx}/{total}] Fetching {ticker}...", end=' ')

            data = self.get_options_chain(ticker)

            if data.get('status') != 'OK':
                print(f"✗ Failed")
                continue

            contracts = data.get('results', [])

            # Aggregate volume and OI
            put_volume = 0
            call_volume = 0
            put_oi = 0
            call_oi = 0

            for contract in contracts:
                contract_type = contract.get('details', {}).get('contract_type')
                volume = contract.get('day', {}).get('volume', 0) or 0
                oi = contract.get('open_interest', 0) or 0

                if contract_type == 'put':
                    put_volume += volume
                    put_oi += oi
                elif contract_type == 'call':
                    call_volume += volume
                    call_oi += oi

            total_volume = put_volume + call_volume
            total_oi = put_oi + call_oi

            # Calculate ratios
            pc_volume_ratio = round(put_volume / call_volume, 2) if call_volume > 0 else 0
            pc_oi_ratio = round(put_oi / call_oi, 2) if call_oi > 0 else 0

            result = {
                'ticker': ticker,
                'total_volume': total_volume,
                'put_volume': put_volume,
                'call_volume': call_volume,
                'pc_volume_ratio': pc_volume_ratio,
                'total_oi': total_oi,
                'put_oi': put_oi,
                'call_oi': call_oi,
                'pc_oi_ratio': pc_oi_ratio,
                'contracts_count': len(contracts)
            }

            results.append(result)
            print(f"✓ Vol={total_volume:,}")

            # Rate limiting
            time.sleep(0.1)

        return results

    def get_top_active_tickers(self, limit: int = 50) -> List[str]:
        """
        Get list of most actively traded option tickers

        For now, returns a predefined list of popular tickers.
        Can be enhanced to fetch dynamically.

        Args:
            limit: Number of tickers to return

        Returns:
            List of ticker symbols
        """
        # Popular options tickers by volume
        popular_tickers = [
            # Major indices
            'SPY', 'QQQ', 'IWM', 'DIA',
            # Tech giants
            'NVDA', 'TSLA', 'AAPL', 'MSFT', 'GOOGL', 'META', 'AMZN',
            # Popular stocks
            'AMD', 'INTC', 'NFLX', 'BABA', 'NIO', 'PLTR', 'SOFI',
            # Finance
            'BAC', 'JPM', 'GS', 'WFC', 'C',
            # Energy
            'XLE', 'USO', 'XOM', 'CVX',
            # Volatility
            'VIX', 'UVXY', 'VIXY',
            # ETFs
            'GLD', 'SLV', 'TLT', 'HYG', 'EEM',
            # Healthcare
            'PFE', 'JNJ', 'UNH', 'ABBV',
            # Consumer
            'WMT', 'HD', 'MCD', 'DIS',
            # Industrials
            'BA', 'CAT', 'GE',
            # Communication
            'T', 'VZ',
        ]

        return popular_tickers[:limit]
