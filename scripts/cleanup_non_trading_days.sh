#!/bin/bash
# Cleanup non-trading day files from gh-pages branch
#
# This script removes JSON and HTML files for dates that are not trading days
# (weekends, holidays, etc.). These files are legacy data from before the
# API fallback removal.

set -e

echo "============================================================"
echo "Cleanup Non-Trading Day Files"
echo "============================================================"
echo ""

# Switch to project root
cd "$(dirname "$0")/.."

# Checkout gh-pages branch
echo "📂 Checking out gh-pages branch..."
git fetch origin gh-pages
git checkout gh-pages

# Get list of all JSON files
echo ""
echo "📋 Checking files for trading day validation..."
echo ""

NON_TRADING_FILES=()

# Check each JSON file
for json_file in *.json; do
    if [ -f "$json_file" ]; then
        # Extract date from filename (YYYY-MM-DD.json)
        date="${json_file%.json}"

        # Skip if not a date pattern
        if [[ ! "$date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
            continue
        fi

        # Check if it's a trading day using Python
        IS_TRADING=$(python3 -c "
import sys
sys.path.insert(0, '../src')
from trading_calendar import is_trading_day
print('true' if is_trading_day('$date') else 'false')
        ")

        if [ "$IS_TRADING" != "true" ]; then
            echo "  ⊘ $date - NOT a trading day"
            NON_TRADING_FILES+=("$date")
        fi
    fi
done

echo ""

if [ ${#NON_TRADING_FILES[@]} -eq 0 ]; then
    echo "✅ No non-trading day files found!"
    echo ""
    git checkout main
    exit 0
fi

echo "Found ${#NON_TRADING_FILES[@]} non-trading day file(s):"
for date in "${NON_TRADING_FILES[@]}"; do
    echo "  • $date"
done
echo ""

# Ask for confirmation
read -p "Delete these files? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled"
    git checkout main
    exit 0
fi

echo ""
echo "🗑️  Removing non-trading day files..."
echo ""

for date in "${NON_TRADING_FILES[@]}"; do
    # Remove JSON and HTML files
    if [ -f "${date}.json" ]; then
        git rm "${date}.json"
        echo "  ✓ Removed ${date}.json"
    fi

    if [ -f "${date}.html" ]; then
        git rm "${date}.html"
        echo "  ✓ Removed ${date}.html"
    fi
done

echo ""
echo "📝 Committing changes..."
git commit -m "Clean up non-trading day files (${NON_TRADING_FILES[*]})"

echo ""
echo "🚀 Pushing to gh-pages..."
git push origin gh-pages

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Cleaned up dates:"
for date in "${NON_TRADING_FILES[@]}"; do
    echo "  • $date"
done
echo ""

# Switch back to main branch
git checkout main

echo "============================================================"
