"""
Example usage of the PowerBall and MegaMillions scrapers.

Shows how to fetch single drawings, scrape a date range, and combine both
lotteries into one CSV file.
"""

from lottery_common import write_csv
from megamillions_scraper import MegaMillionsScraper
from powerball_scraper import PowerBallScraper


def main():
    powerball = PowerBallScraper()
    megamillions = MegaMillionsScraper()

    # Example 1: Get a single drawing
    print("=== Example 1: Single Drawing ===")
    result = powerball.get_drawing_data('2025-10-01')
    if result:
        print(f"Date: {result['date']}")
        print(f"Jackpot: {result['jackpot']} (${result['jackpot_usd']:,})")
        print(f"Cash Value: {result['cash_value']}")
        print(f"Jackpot winners: {result['match_5_bonus_winners']}")
        print()

    # Example 2: Get historical data for a date range
    print("=== Example 2: Historical Data ===")
    powerball_data = powerball.scrape_historical_data('2025-10-01', '2025-10-31')
    megamillions_data = megamillions.scrape_historical_data('2025-10-01', '2025-10-31')

    # Both scrapers use the same columns, so their rows can be combined directly
    write_csv(powerball_data + megamillions_data, 'october_2025_lotteries.csv')
    print(f"Saved {len(powerball_data) + len(megamillions_data)} drawings to october_2025_lotteries.csv")
    print()

    # Example 3: Get specific drawing dates
    print("=== Example 3: Drawing Dates ===")
    print("PowerBall drawing dates from Oct 1-15, 2025:")
    for date in powerball.get_drawing_dates('2025-10-01', '2025-10-15'):
        print(f"  - {date}")


if __name__ == '__main__':
    main()
