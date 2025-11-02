#!/usr/bin/env python3
"""
Data Fetcher Module
Fetches options data from Polygon.io API
"""
import os
import requests
import time
from typing import Dict, List, Optional
from options_utils import parse_option_ticker, aggregate_oi_from_contracts


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

    def get_options_chain(self, ticker: str) -> Dict:
        """
        Get options chain snapshot for a ticker with pagination

        Args:
            ticker: Stock ticker (e.g., 'SPY')

        Returns:
            Dict containing options chain data
        """
        url = f"{self.base_url}/v3/snapshot/options/{ticker}"
        params = {
            'apiKey': self.api_key,
            'limit': 250  # Maximum allowed
        }

        all_results = []

        try:
            # First request
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('status') != 'OK':
                return data

            all_results.extend(data.get('results', []))

            # Handle pagination
            next_url = data.get('next_url')
            max_pages = 10  # Limit to prevent infinite loops
            page_count = 1

            while next_url and page_count < max_pages:
                # Add API key to next_url
                next_params = {'apiKey': self.api_key}
                response = self.session.get(next_url, params=next_params, timeout=10)
                response.raise_for_status()
                data = response.json()

                if data.get('status') != 'OK':
                    break

                all_results.extend(data.get('results', []))
                next_url = data.get('next_url')
                page_count += 1

            return {
                'status': 'OK',
                'results': all_results,
                'count': len(all_results)
            }

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

            # Aggregate volume
            put_volume = 0
            call_volume = 0

            for contract in contracts:
                details = contract.get('details', {})
                contract_type = details.get('contract_type')
                volume = contract.get('day', {}).get('volume', 0) or 0

                if contract_type == 'put':
                    put_volume += volume
                elif contract_type == 'call':
                    call_volume += volume

            total_volume = put_volume + call_volume

            # Calculate C/P volume ratio
            cp_volume_ratio = round(call_volume / put_volume, 2) if put_volume > 0 else 0

            # Use centralized OI aggregation utility
            oi_data = aggregate_oi_from_contracts(contracts)

            result = {
                'ticker': ticker,
                'total_volume': total_volume,
                'put_volume': put_volume,
                'call_volume': call_volume,
                'cp_volume_ratio': cp_volume_ratio,
                'contracts_count': len(contracts),
                # OI data from centralized utility
                **oi_data
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
