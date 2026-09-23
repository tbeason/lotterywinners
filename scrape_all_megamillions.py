"""
Scrape ALL MegaMillions historical data from 2010-02-02 to present.

Only drawings missing from megamillions_all_history.csv are fetched, so
re-running this script brings the dataset up to date. Progress is auto-saved
every 50 drawings and an interrupted run resumes where it left off.

    python scrape_all_megamillions.py                     # add new drawings
    python scrape_all_megamillions.py --full              # re-scrape everything
    python scrape_all_megamillions.py --dates 2024-11-01  # re-scrape specific dates
"""

from lottery_common import run_history_scrape
from megamillions_scraper import MegaMillionsScraper


if __name__ == '__main__':
    with MegaMillionsScraper() as scraper:
        run_history_scrape(
            scraper,
            first_drawing=MegaMillionsScraper.FIRST_DRAWING,
            output_file='megamillions_all_history.csv',
            partial_file='megamillions_partial.csv',
            error_file='megamillions_scraping_errors.csv',
        )
