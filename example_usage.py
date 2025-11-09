"""
Example usage of the PowerBall scraper.

This script shows how to scrape PowerBall historical data
and save it to a CSV file.
"""

from powerball_scraper import PowerBallScraper


def main():
    # Create scraper instance
    scraper = PowerBallScraper()

    # Example 1: Get a single drawing
    print("=== Example 1: Single Drawing ===")
    result = scraper.get_drawing_data('2025-10-01')
    if result:
        print(f"Date: {result['date']}")
        print(f"Jackpot: {result['jackpot']}")
        print(f"Cash Value: {result['cash_value']}")
        print(f"Number of prize levels: {len(result['prize_levels'])}")
        print()

    # Example 2: Get historical data for a date range
    print("=== Example 2: Historical Data ===")
    print("Scraping drawings from October 1 to October 31, 2025...")

    # Note: PowerBall drawings are on Monday, Wednesday, and Saturday
    historical_data = scraper.scrape_historical_data('2025-10-01', '2025-10-31')

    # Save to CSV
    scraper.save_to_csv(historical_data, 'october_2025_powerball.csv')
    print(f"Saved {len(historical_data)} drawings to october_2025_powerball.csv")
    print()

    # Example 3: Get specific drawing dates
    print("=== Example 3: Drawing Dates ===")
    dates = scraper.get_drawing_dates('2025-10-01', '2025-10-15')
    print(f"PowerBall drawing dates from Oct 1-15, 2025:")
    for date in dates:
        print(f"  - {date}")


if __name__ == '__main__':
    main()
