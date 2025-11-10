"""
Scrape missing MegaMillions data from 2010-02-02 to 2014-05-26.

This fills in the gap in the historical data.
"""

from megamillions_scraper import MegaMillionsScraper
import csv
import sys

# Configure stdout encoding for Windows console compatibility
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

def scrape_missing_data():
    """Scrape the missing early MegaMillions data."""

    scraper = MegaMillionsScraper(headless=True)

    # Missing date range
    start_date = '2010-02-02'
    end_date = '2014-05-26'  # Day before current data starts

    print(f"Scraping missing MegaMillions data")
    print(f"=" * 50)
    print(f"Start Date: {start_date}")
    print(f"End Date: {end_date}")
    print()

    # Get all drawing dates for the missing period
    dates = scraper.get_drawing_dates(start_date, end_date)
    print(f"Total drawings to scrape: {len(dates)}")
    print()

    results = []
    errors = []

    print("Starting scrape...")
    print()

    for i, date in enumerate(dates, 1):
        try:
            print(f"Fetching {i}/{len(dates)}: {date}", end='\r')
            data = scraper.get_drawing_data(date)

            if data:
                results.append(data)
            else:
                errors.append({'date': date, 'error': 'No data returned'})

        except Exception as e:
            errors.append({'date': date, 'error': str(e)})
            print(f"\nERROR on {date}: {e}")

    print(f"\n\nCompleted! Successfully scraped: {len(results)} drawings")
    print(f"Errors: {len(errors)}")
    print()

    # Save to temporary file
    output_file = 'megamillions_missing_2010_2014.csv'
    scraper.save_to_csv(results, output_file)
    print(f"Missing data saved to: {output_file}")

    if errors:
        error_file = 'megamillions_missing_errors.csv'
        with open(error_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['date', 'error'])
            writer.writeheader()
            writer.writerows(errors)
        print(f"Error log saved to: {error_file}")

    scraper.close()
    print("\nDone!")

if __name__ == '__main__':
    scrape_missing_data()
