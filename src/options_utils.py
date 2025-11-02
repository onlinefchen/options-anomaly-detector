#!/usr/bin/env python3
"""
Options Data Utilities
Shared functions for parsing and analyzing options data
"""
import re
from typing import Dict, Optional, List


def parse_option_ticker(ticker: str) -> Optional[Dict]:
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


def analyze_strike_concentration(strike_dict: dict, total_oi: int) -> dict:
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


def aggregate_oi_from_contracts(contracts: List[dict]) -> dict:
    """
    从合约列表中聚合OI数据

    Centralizes the OI aggregation logic that was duplicated across modules.

    Args:
        contracts: List of contract dicts from Polygon API

    Returns:
        Dict with aggregated OI data and analysis:
        {
            'total_oi': int,
            'put_oi': int,
            'call_oi': int,
            'cp_oi_ratio': float,
            'top_3_contracts': list,
            'strike_concentration': dict
        }
    """
    put_oi = 0
    call_oi = 0
    contracts_with_oi = []
    strike_dict = {}

    for contract in contracts:
        details = contract.get('details', {})
        contract_type = details.get('contract_type')
        oi = contract.get('open_interest', 0) or 0
        strike = details.get('strike_price')

        if contract_type == 'put':
            put_oi += oi
        elif contract_type == 'call':
            call_oi += oi

        # 收集合约信息用于分析
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

    total_oi = put_oi + call_oi
    cp_oi_ratio = round(call_oi / put_oi, 2) if put_oi > 0 else 0

    # 获取 Top 3 活跃合约
    top_3 = sorted(contracts_with_oi, key=lambda x: x['oi'], reverse=True)[:3]
    for contract in top_3:
        contract['percentage'] = round(contract['oi'] / total_oi * 100, 1) if total_oi > 0 else 0

    # 分析价格区间
    strike_concentration = analyze_strike_concentration(strike_dict, total_oi)

    return {
        'total_oi': total_oi,
        'put_oi': put_oi,
        'call_oi': call_oi,
        'cp_oi_ratio': cp_oi_ratio,
        'top_3_contracts': top_3,
        'strike_concentration': strike_concentration
    }
