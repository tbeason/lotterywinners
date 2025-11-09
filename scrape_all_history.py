"""
Scrape ALL PowerBall historical data from 1992-04-22 to present.

This script scrapes the complete PowerBall drawing history, with:
- Progress tracking and resume capability
- Error handling for page structure changes
- Rate limiting to respect the server
- Automatic save every 50 drawings
"""

from powerball_scraper import PowerBallScraper
from datetime import datetime
import time
import os
import sys


def scrape_all_powerball_history():
    """Scrape all PowerBall data from first drawing to present."""

    scraper = PowerBallScraper()

    # PowerBall started on April 22, 1992
    start_date = '1992-04-22'

    # Today's date
    end_date = datetime.now().strftime('%Y-%m-%d')

    print(f"PowerBall Historical Data Scraper")
    sys.stdout.flush()
    print(f"=" * 50)
    sys.stdout.flush()
    print(f"Start Date: {start_date}")
    print(f"End Date: {end_date}")
    print()
    sys.stdout.flush()

    # Get all drawing dates
    # Note: Wed/Sat only before 2021-08-23, then Mon/Wed/Sat
    dates = scraper.get_drawing_dates(start_date, end_date)
    print(f"Total drawings to scrape: {len(dates)}")
    sys.stdout.flush()
    print(f"Estimated time: {len(dates) * 0.5 / 3600:.1f} hours (at 0.5 seconds per drawing)")
    print()
    sys.stdout.flush()

    # Check for existing partial data
    partial_file = 'powerball_partial.csv'
    if os.path.exists(partial_file):
        response = input(f"Found existing partial data file. Resume from there? (y/n): ")
        if response.lower() == 'y':
            # Load existing dates to skip
            import csv
            with open(partial_file, 'r') as f:
                reader = csv.DictReader(f)
                completed_dates = {row['date'] for row in reader}
            dates = [d for d in dates if d not in completed_dates]
            print(f"Resuming: {len(dates)} drawings remaining")
            print()

    results = []
    errors = []
    save_interval = 50  # Save every 50 drawings

    print("Starting scrape...")
    print()

    for i, date in enumerate(dates, 1):
        try:
            # Fetch data
            data = scraper.get_drawing_data(date)

            if data:
                results.append(data)

                # Progress update
                if i % 10 == 0:
                    print(f"Progress: {i}/{len(dates)} ({i/len(dates)*100:.1f}%) - Latest: {date}")
                    sys.stdout.flush()

                # Auto-save every N drawings
                if i % save_interval == 0:
                    scraper.save_to_csv(results, partial_file)
                    print(f"  → Auto-saved {len(results)} drawings to {partial_file}")
                    sys.stdout.flush()

            else:
                errors.append({'date': date, 'error': 'No data returned'})

            # Rate limiting - be nice to the server
            time.sleep(0.5)  # 0.5 seconds between requests

        except Exception as e:
            errors.append({'date': date, 'error': str(e)})
            print(f"ERROR on {date}: {e}")

            # Continue despite errors
            continue

    print()
    print("=" * 50)
    print("Scraping Complete!")
    print(f"Successfully scraped: {len(results)} drawings")
    print(f"Errors: {len(errors)}")
    print()

    # Save final results
    final_file = 'powerball_all_history.csv'
    scraper.save_to_csv(results, final_file)
    print(f"Final data saved to: {final_file}")

    # Save error log if there were errors
    if errors:
        error_file = 'scraping_errors.csv'
        import csv
        with open(error_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['date', 'error'])
            writer.writeheader()
            writer.writerows(errors)
        print(f"Error log saved to: {error_file}")

    print()
    print("Done!")


if __name__ == '__main__':
    scrape_all_powerball_history()
