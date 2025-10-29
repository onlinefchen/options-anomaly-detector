# Options Anomaly Detector

🔍 Daily options market anomaly detection and analysis system

## Features

- ⚡ **Hybrid CSV + API Strategy**: Optimal performance with smart fallback
- 📊 **Volume Analysis**: Detect unusual trading volume spikes
- 📈 **Put/Call Ratio Anomalies**: Identify extreme sentiment shifts
- 🎯 **Open Interest Tracking**: Monitor position building and unwinding
- 🚨 **Real-time Alerts**: Automated anomaly detection
- 📱 **Interactive Dashboard**: Beautiful HTML reports with charts
- 🤖 **GitHub Actions**: Automated daily analysis and reports

## Data Strategy

The system uses an intelligent **hybrid data fetching strategy**:

### Strategy 1: CSV + API (Optimal - if Flat Files available)
1. 📦 Download daily options aggregates CSV (~50-100MB)
2. ⚡ Parse and aggregate volume data for all tickers (~10 sec)
3. 🎯 Fetch Open Interest via API for top 30 tickers only (~30 API calls)
4. ✅ **Total time: ~30 seconds** with complete market coverage

### Strategy 2: Pure API (Fallback - always works)
1. 📱 Fetch data for ~50 popular tickers via API (~50 calls)
2. ✅ **Total time: ~15-20 seconds** with targeted coverage

The system **automatically detects** your subscription level and chooses the optimal strategy!

## Quick Start

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/onlinefchen/options-anomaly-detector.git
cd options-anomaly-detector
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your POLYGON_API_KEY
```

4. Run analysis:
```bash
python main.py
```

5. View the report:
```bash
open output/anomaly_report.html
```

### GitHub Actions (Automated)

The system runs automatically every day at 11:30 AM ET via GitHub Actions.

Reports are published to: **https://onlinefchen.github.io/options-anomaly-detector/**

## Configuration

### Required Secrets

Configure in GitHub repository settings → Secrets and variables → Actions:

- `POLYGON_API_KEY`: Your Polygon.io API key

### Data Sources

- **Trading Volume**: Options Chain Snapshot API
- **Open Interest**: Options Contract Snapshot API
- **Price Data**: Options Aggregates API

## Architecture

```
options-anomaly-detector/
├── src/
│   ├── data_fetcher.py      # Data acquisition
│   ├── anomaly_detector.py  # Anomaly detection logic
│   ├── report_generator.py  # HTML report generation
│   └── utils.py             # Utility functions
├── .github/
│   └── workflows/
│       └── daily-analysis.yml
├── output/
│   └── anomaly_report.html
├── main.py
└── requirements.txt
```

## Anomaly Detection Methods

### 1. Volume Anomalies
- Z-score > 3 (3 standard deviations)
- Day-over-day growth > 200%
- Ranking jumps

### 2. Put/Call Ratio Anomalies
- Extreme fear: Put/Call > 1.8
- Extreme greed: Put/Call < 0.4

### 3. Open Interest Anomalies
- Large OI increases (new positions)
- OI decreases (position unwinding)
- Volume/OI divergence

### 4. Structural Anomalies
- Deep OTM activity
- Strike price concentration
- Expiration clustering

## Output

### Terminal Output
- Top 30 volume rankings
- Detected anomalies summary
- Key metrics and alerts

### HTML Report
- Interactive charts (Chart.js)
- Volume rankings table
- Anomaly details
- Historical trends

## License

MIT

## Author

Created with ❤️ by onlinefchen
