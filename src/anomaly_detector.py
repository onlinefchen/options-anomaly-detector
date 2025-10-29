#!/usr/bin/env python3
"""
Anomaly Detector Module
Detects anomalies in options trading data
"""
import numpy as np
from typing import List, Dict, Tuple


class OptionsAnomalyDetector:
    """Detect anomalies in options data"""

    def __init__(self):
        """Initialize the anomaly detector"""
        self.anomalies = []

    def detect_all_anomalies(self, data: List[Dict]) -> List[Dict]:
        """
        Run all anomaly detection methods

        Args:
            data: List of aggregated options data

        Returns:
            List of detected anomalies
        """
        self.anomalies = []

        # Sort by volume for ranking analysis
        sorted_data = sorted(data, key=lambda x: x['total_volume'], reverse=True)

        # Run detection methods
        self.detect_volume_anomalies(sorted_data)
        self.detect_pc_ratio_anomalies(sorted_data)
        self.detect_oi_anomalies(sorted_data)

        return self.anomalies

    def detect_volume_anomalies(self, data: List[Dict]):
        """
        Detect volume anomalies

        - Extremely high volume
        - Very low volume for typically active tickers
        """
        if not data:
            return

        volumes = [d['total_volume'] for d in data if d['total_volume'] > 0]

        if not volumes:
            return

        # Calculate statistics
        mean_vol = np.mean(volumes)
        std_vol = np.std(volumes)
        median_vol = np.median(volumes)

        for item in data:
            ticker = item['ticker']
            volume = item['total_volume']

            # Skip if no volume
            if volume == 0:
                continue

            # Calculate z-score
            if std_vol > 0:
                z_score = (volume - mean_vol) / std_vol
            else:
                z_score = 0

            # Anomaly: Extremely high volume (z-score > 2)
            if z_score > 2:
                self.anomalies.append({
                    'ticker': ticker,
                    'type': 'HIGH_VOLUME',
                    'severity': 'HIGH' if z_score > 3 else 'MEDIUM',
                    'description': f'Extremely high trading volume (Z-score: {z_score:.2f})',
                    'value': volume,
                    'metric': 'volume',
                    'z_score': z_score
                })

            # Anomaly: Volume much higher than median
            if volume > median_vol * 5:
                self.anomalies.append({
                    'ticker': ticker,
                    'type': 'VOLUME_SPIKE',
                    'severity': 'HIGH',
                    'description': f'Volume {volume/median_vol:.1f}x above median',
                    'value': volume,
                    'metric': 'volume'
                })

    def detect_pc_ratio_anomalies(self, data: List[Dict]):
        """
        Detect Put/Call ratio anomalies

        - Extreme fear: PC ratio > 1.8
        - Extreme greed: PC ratio < 0.4
        """
        for item in data:
            ticker = item['ticker']
            pc_volume_ratio = item['pc_volume_ratio']
            pc_oi_ratio = item['pc_oi_ratio']

            # Skip if no data
            if pc_volume_ratio == 0 and pc_oi_ratio == 0:
                continue

            # Volume PC ratio anomalies
            if pc_volume_ratio > 1.8:
                self.anomalies.append({
                    'ticker': ticker,
                    'type': 'EXTREME_FEAR',
                    'severity': 'HIGH',
                    'description': f'Extreme bearish sentiment (Put/Call volume: {pc_volume_ratio:.2f})',
                    'value': pc_volume_ratio,
                    'metric': 'pc_volume_ratio'
                })
            elif pc_volume_ratio < 0.4 and pc_volume_ratio > 0:
                self.anomalies.append({
                    'ticker': ticker,
                    'type': 'EXTREME_GREED',
                    'severity': 'HIGH',
                    'description': f'Extreme bullish sentiment (Put/Call volume: {pc_volume_ratio:.2f})',
                    'value': pc_volume_ratio,
                    'metric': 'pc_volume_ratio'
                })

            # OI PC ratio anomalies
            if pc_oi_ratio > 2.0:
                self.anomalies.append({
                    'ticker': ticker,
                    'type': 'DEFENSIVE_POSITIONING',
                    'severity': 'MEDIUM',
                    'description': f'Heavy defensive positioning (Put/Call OI: {pc_oi_ratio:.2f})',
                    'value': pc_oi_ratio,
                    'metric': 'pc_oi_ratio'
                })
            elif pc_oi_ratio < 0.3 and pc_oi_ratio > 0:
                self.anomalies.append({
                    'ticker': ticker,
                    'type': 'AGGRESSIVE_POSITIONING',
                    'severity': 'MEDIUM',
                    'description': f'Heavy aggressive positioning (Put/Call OI: {pc_oi_ratio:.2f})',
                    'value': pc_oi_ratio,
                    'metric': 'pc_oi_ratio'
                })

    def detect_oi_anomalies(self, data: List[Dict]):
        """
        Detect Open Interest anomalies

        - Very high OI relative to volume
        - Very low OI relative to volume
        """
        for item in data:
            ticker = item['ticker']
            volume = item['total_volume']
            oi = item['total_oi']

            # Skip if no data
            if volume == 0 or oi == 0:
                continue

            # Calculate volume/OI ratio
            vol_oi_ratio = volume / oi if oi > 0 else 0

            # Anomaly: Very high volume relative to OI (day trading / churning)
            if vol_oi_ratio > 2.0:
                self.anomalies.append({
                    'ticker': ticker,
                    'type': 'HIGH_TURNOVER',
                    'severity': 'MEDIUM',
                    'description': f'High turnover (Volume/OI: {vol_oi_ratio:.2f}), possible day trading',
                    'value': vol_oi_ratio,
                    'metric': 'vol_oi_ratio'
                })

            # Anomaly: Very low volume relative to OI (position holding)
            if vol_oi_ratio < 0.1 and volume > 1000:
                self.anomalies.append({
                    'ticker': ticker,
                    'type': 'LOW_TURNOVER',
                    'severity': 'LOW',
                    'description': f'Low turnover (Volume/OI: {vol_oi_ratio:.2f}), strong position holding',
                    'value': vol_oi_ratio,
                    'metric': 'vol_oi_ratio'
                })

    def get_summary(self) -> Dict:
        """
        Get summary of detected anomalies

        Returns:
            Dict with anomaly statistics
        """
        if not self.anomalies:
            return {
                'total': 0,
                'by_severity': {},
                'by_type': {}
            }

        # Count by severity
        by_severity = {}
        for anomaly in self.anomalies:
            severity = anomaly['severity']
            by_severity[severity] = by_severity.get(severity, 0) + 1

        # Count by type
        by_type = {}
        for anomaly in self.anomalies:
            atype = anomaly['type']
            by_type[atype] = by_type.get(atype, 0) + 1

        return {
            'total': len(self.anomalies),
            'by_severity': by_severity,
            'by_type': by_type
        }

    def get_top_anomalies(self, limit: int = 10) -> List[Dict]:
        """
        Get top anomalies by severity

        Args:
            limit: Number of anomalies to return

        Returns:
            List of top anomalies
        """
        # Sort by severity (HIGH > MEDIUM > LOW)
        severity_order = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}

        sorted_anomalies = sorted(
            self.anomalies,
            key=lambda x: severity_order.get(x['severity'], 0),
            reverse=True
        )

        return sorted_anomalies[:limit]
