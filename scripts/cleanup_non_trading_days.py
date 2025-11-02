#!/usr/bin/env python3
"""
Cleanup non-trading day files from gh-pages branch

This script removes JSON and HTML files for dates that are not trading days
(weekends, holidays, etc.). These files are legacy data from before the
API fallback removal.
"""
import sys
import os
import subprocess

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from trading_calendar import is_trading_day


def run_command(cmd, check=True):
    """Run a shell command and return output"""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        check=check
    )
    return result.stdout.strip()


def main():
    print("=" * 80)
    print("Cleanup Non-Trading Day Files from gh-pages")
    print("=" * 80)
    print()

    # Get current branch
    current_branch = run_command("git branch --show-current")
    print(f"📍 Current branch: {current_branch}")

    # Fetch gh-pages
    print("📡 Fetching gh-pages branch...")
    run_command("git fetch origin gh-pages")

    # Get list of files in gh-pages
    print("📋 Checking files in gh-pages branch...")
    files_output = run_command(
        "git ls-tree -r --name-only origin/gh-pages | grep -E '\\.json$'",
        check=False
    )

    if not files_output:
        print("✓ No JSON files found in gh-pages")
        return

    json_files = files_output.split('\n')
    print(f"  Found {len(json_files)} JSON files")
    print()

    # Check each file
    non_trading_files = []

    print("🔍 Checking trading day status...")
    for filename in json_files:
        # Extract date from filename
        date = os.path.basename(filename).replace('.json', '')

        # Check if it matches date pattern
        if not date or len(date) != 10:  # YYYY-MM-DD
            continue

        # Check if it's a trading day
        if not is_trading_day(date):
            print(f"  ⊘ {date} - NOT a trading day")
            non_trading_files.append(date)

    print()

    if not non_trading_files:
        print("✅ No non-trading day files found!")
        return

    print(f"Found {len(non_trading_files)} non-trading day file(s):")
    for date in non_trading_files:
        print(f"  • {date}")
    print()

    # Checkout gh-pages
    print("📂 Switching to gh-pages branch...")
    run_command("git checkout gh-pages")

    try:
        # Remove files
        print("🗑️  Removing non-trading day files...")
        print()

        files_removed = []
        for date in non_trading_files:
            # Remove JSON
            json_file = f"{date}.json"
            if os.path.exists(json_file):
                run_command(f"git rm {json_file}")
                print(f"  ✓ Removed {json_file}")
                files_removed.append(json_file)

            # Remove HTML
            html_file = f"{date}.html"
            if os.path.exists(html_file):
                run_command(f"git rm {html_file}")
                print(f"  ✓ Removed {html_file}")
                files_removed.append(html_file)

        if not files_removed:
            print("  ℹ️  No files to remove")
            run_command(f"git checkout {current_branch}")
            return

        print()
        print("📝 Committing changes...")

        # Commit
        dates_str = ", ".join(non_trading_files)
        commit_msg = f"Clean up non-trading day files ({dates_str})"
        run_command(f"git commit -m '{commit_msg}'")

        print()
        print("🚀 Pushing to gh-pages...")
        run_command("git push origin gh-pages")

        print()
        print("✅ Cleanup complete!")
        print()
        print("Removed files:")
        for f in files_removed:
            print(f"  • {f}")

    finally:
        # Always switch back to original branch
        print()
        print(f"🔄 Switching back to {current_branch}...")
        run_command(f"git checkout {current_branch}")

    print()
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
