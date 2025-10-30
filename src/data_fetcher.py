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

            # Aggregate volume and OI
            put_volume = 0
            call_volume = 0
            put_oi = 0
            call_oi = 0
            contracts_with_oi = []
            strike_dict = {}

            for contract in contracts:
                details = contract.get('details', {})
                contract_type = details.get('contract_type')
                volume = contract.get('day', {}).get('volume', 0) or 0
                oi = contract.get('open_interest', 0) or 0
                strike = details.get('strike_price')

                if contract_type == 'put':
                    put_volume += volume
                    put_oi += oi
                elif contract_type == 'call':
                    call_volume += volume
                    call_oi += oi

                # 收集合约信息用于 Top 3 分析
                if oi > 0:
                    contracts_with_oi.append({
                        'ticker': details.get('ticker'),
                        'oi': oi,
                        'strike': strike,
                        'expiry': details.get('expiration_date'),
                        'type': contract_type
                    })

                    # 统计行权价分布
                    if strike:
                        strike_dict[strike] = strike_dict.get(strike, 0) + oi

            total_volume = put_volume + call_volume
            total_oi = put_oi + call_oi

            # Calculate ratios (C/P ratio: Call/Put)
            cp_volume_ratio = round(call_volume / put_volume, 2) if put_volume > 0 else 0
            cp_oi_ratio = round(call_oi / put_oi, 2) if put_oi > 0 else 0

            # 获取 Top 3 活跃合约
            top_3 = sorted(contracts_with_oi, key=lambda x: x['oi'], reverse=True)[:3]
            for contract in top_3:
                contract['percentage'] = round(contract['oi'] / total_oi * 100, 1) if total_oi > 0 else 0

            # 分析价格区间
            strike_concentration = self._analyze_strike_concentration(strike_dict, total_oi)

            result = {
                'ticker': ticker,
                'total_volume': total_volume,
                'put_volume': put_volume,
                'call_volume': call_volume,
                'cp_volume_ratio': cp_volume_ratio,
                'total_oi': total_oi,
                'put_oi': put_oi,
                'call_oi': call_oi,
                'cp_oi_ratio': cp_oi_ratio,
                'contracts_count': len(contracts),
                'top_3_contracts': top_3,
                'strike_concentration': strike_concentration
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

    def _analyze_strike_concentration(self, strike_dict: dict, total_oi: int) -> dict:
        """
        分析行权价分布，找到最集中的价格区间

        Args:
            strike_dict: Dict mapping strike price to total OI
            total_oi: Total open interest

        Returns:
            Dict with strike concentration info
        """
        if not strike_dict or total_oi == 0:
            return {
                'range': 'N/A',
                'oi': 0,
                'percentage': 0.0,
                'dominant_strike': None
            }

        # 找到持仓量最大的行权价
        dominant_strike = max(strike_dict.items(), key=lambda x: x[1])[0]

        # 定义价格区间宽度（根据价格水平自适应）
        if dominant_strike < 50:
            range_width = 5
        elif dominant_strike < 200:
            range_width = 10
        elif dominant_strike < 500:
            range_width = 20
        else:
            range_width = 50

        # 计算以dominant_strike为中心的区间
        range_start = int(dominant_strike / range_width) * range_width
        range_end = range_start + range_width

        # 计算该区间的总持仓量
        range_oi = sum(oi for strike, oi in strike_dict.items()
                      if range_start <= strike < range_end)

        return {
            'range': f'{range_start}-{range_end}',
            'oi': range_oi,
            'percentage': round(range_oi / total_oi * 100, 1) if total_oi > 0 else 0,
            'dominant_strike': int(dominant_strike)
        }
