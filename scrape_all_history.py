"""
Scrape ALL PowerBall historical data from 1992-04-22 to present.

Only drawings missing from powerball_all_history.csv are fetched, so re-running
this script brings the dataset up to date. Progress is auto-saved every 50
drawings and an interrupted run resumes where it left off.

    python scrape_all_history.py                     # add new drawings
    python scrape_all_history.py --full              # re-scrape everything
    python scrape_all_history.py --dates 2022-11-07  # re-scrape specific dates
"""

from lottery_common import run_history_scrape
from powerball_scraper import PowerBallScraper


if __name__ == '__main__':
    with PowerBallScraper() as scraper:
        run_history_scrape(
            scraper,
            first_drawing=PowerBallScraper.FIRST_DRAWING,
            output_file='powerball_all_history.csv',
            partial_file='powerball_partial.csv',
            error_file='powerball_scraping_errors.csv',
        )
