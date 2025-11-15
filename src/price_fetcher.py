#!/usr/bin/env python3
"""
Price Fetcher Module
Fetches current stock prices from Polygon.io API
"""
import os
import time
import requests
from typing import Dict, List, Optional


class PriceFetcher:
    """Fetch current stock prices from Polygon.io API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize price fetcher

        Args:
            api_key: Polygon.io API key (defaults to environment variable)
        """
        self.api_key = api_key or os.getenv('POLYGON_API_KEY')
        self.base_url = "https://api.polygon.io"
        self.session = requests.Session()

    def is_available(self) -> bool:
        """Check if Polygon API is configured"""
        if not self.api_key:
            return False
        if len(self.api_key) == 0:
            return False
        if self.api_key == 'YOUR_API_KEY_HERE':
            return False
        return True

    def get_quote(self, symbol: str) -> Optional[float]:
        """
        Get current price for a single symbol using Polygon snapshot API

        Args:
            symbol: Stock ticker symbol

        Returns:
            Current price or None if failed
        """
        if not self.is_available():
            return None

        try:
            # Use Polygon snapshot API for real-time quote
            url = f"{self.base_url}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol}"
            params = {'apiKey': self.api_key}
            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                ticker_data = data.get('ticker', {})
                # Get last trade price
                last_trade = ticker_data.get('lastTrade', {})
                price = last_trade.get('p')

                # Fallback to previous close if no last trade
                if price is None:
                    prev_day = ticker_data.get('prevDay', {})
                    price = prev_day.get('c')

                return price
            else:
                return None

        except Exception as e:
            print(f"  ⚠️  Failed to fetch price for {symbol}: {e}")
            return None

    def get_batch_quotes(self, symbols: List[str], delay: float = 0.1) -> Dict[str, float]:
        """
        Get current prices for multiple symbols

        Args:
            symbols: List of stock ticker symbols
            delay: Delay between API calls in seconds (rate limiting)

        Returns:
            Dict mapping symbol to current price
        """
        if not self.is_available():
            print("  ⚠️  Polygon API key not configured, skipping price fetch")
            return {}

        prices = {}
        total = len(symbols)

        print(f"  📊 Fetching current prices for {total} tickers...")

        for idx, symbol in enumerate(symbols, 1):
            price = self.get_quote(symbol)
            if price is not None:
                prices[symbol] = price
                if idx % 10 == 0 or idx == total:
                    print(f"  ✓ Progress: {idx}/{total} prices fetched")

            # Rate limiting
            if idx < total:
                time.sleep(delay)

        success_count = len(prices)
        print(f"  ✓ Successfully fetched {success_count}/{total} prices")

        return prices

    def enrich_data_with_prices(self, data: List[Dict]) -> List[Dict]:
        """
        Add current prices to ticker data

        Args:
            data: List of ticker data dicts

        Returns:
            Data enriched with current_price field
        """
        if not self.is_available():
            print("  ⚠️  Polygon API not configured, skipping price enrichment")
            for item in data:
                item['current_price'] = None
            return data

        # Extract unique tickers
        tickers = [item['ticker'] for item in data]

        # Fetch prices
        prices = self.get_batch_quotes(tickers)

        # Add prices to data
        for item in data:
            ticker = item['ticker']
            item['current_price'] = prices.get(ticker)

        return data
