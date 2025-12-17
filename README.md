# Options Anomaly Detector

## Overview

This project is an automated system for detecting anomalies in the US options market. It ingests daily market data, applies statistical models to identify unusual activity (volume spikes, sentiment shifts, institutional positioning), and generates actionable insights via HTML reports and AI-driven analysis.

For a conceptual understanding of the project's philosophy and "Smart Money" analysis, please refer to [idea.md](idea.md).

## Features

- **Hybrid Data Ingestion**: efficiently combines Polygon.io Flat Files (S3/CSV) for market-wide breadth with Real-time APIs for depth (Open Interest).
- **Anomaly Detection**: Algorithms to spot:
    - Volume Z-Score spikes (>3σ)
    - Extreme Put/Call Ratios (Fear/Greed)
    - High Turnover vs. Accumulation patterns
    - LEAP (Long-Term Equity Anticipation Securities) unusual activity
- **AI Analysis**: Integrates with OpenAI (GPT-4) to generate macro commentary and specific trade ideas based on the data.
- **Reporting**:
    - Interactive HTML Dashboard (deployed to GitHub Pages).
    - Email notifications with summarized insights.
    - Historical JSON archives.

## Installation

### Prerequisites

- Python 3.11+
- Polygon.io API Key (Starter plan or above required for Options data)
- (Optional) OpenAI API Key for AI analysis
- (Optional) Gmail App Password for email notifications

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/onlinefchen/options-anomaly-detector.git
    cd options-anomaly-detector
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment:**
    Copy `.env.example` to `.env` and fill in your credentials:
    ```bash
    cp .env.example .env
    ```

    **Required:**
    - `POLYGON_API_KEY`: Your Polygon.io API Key.

    **Optional (Recommended):**
    - `POLYGON_S3_ACCESS_KEY` & `POLYGON_S3_SECRET_KEY`: For faster Flat File downloads.
    - `OPENAI_API_KEY`: To enable AI analysis.
    - `GMAIL_USER` & `GMAIL_APP_PASSWD`: To enable email reports.

## Usage

### 1. Daily Analysis (Manual)

To run the full daily analysis pipeline (Download -> Analyze -> Report -> Email):

```bash
python run.py daily-analysis
```

### 2. Regenerate Historical Data

To backfill or regenerate reports for past trading days (e.g., last 10 days):

```bash
python run.py daily-analysis --days-back 10
```

*Note: Historical generation skips real-time Open Interest (OI) enrichment to save API calls, relying on the CSV's volume data.*

### 3. Regenerate HTML Reports

If you've modified the report template and want to update existing HTML files without re-downloading data:

```bash
python run.py regenerate-html --days 7
```

## Automation (GitHub Actions)

The system is designed to run automatically via GitHub Actions.

- **Schedule**: Runs hourly from 16:00 to 21:00 Beijing Time (08:00-13:00 UTC) to check for the latest data availability.
- **Workflow**: `daily-analysis.yml` handles the end-to-end process and deploys the report to GitHub Pages.

## Project Structure

- `src/`: Core source code.
    - `hybrid_fetcher.py`: Handles data downloading (S3/API).
    - `anomaly_detector.py`: Statistical logic for anomaly detection.
    - `ai_analyzer.py`: Prompt engineering and OpenAI integration.
    - `report_generator.py`: HTML templating.
- `output/`: Generated JSON data and HTML reports.
- `data/`: Temporary storage for downloaded CSVs (ignored by git).
- `.github/workflows/`: Automation configurations.

## License

MIT
