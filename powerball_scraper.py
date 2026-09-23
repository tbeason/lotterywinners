"""
PowerBall Historical Data Scraper

Scrapes PowerBall drawing results from powerball.com including:
- Date of drawing
- Estimated jackpot amount and cash value
- Number of winners and prize at each prize level, with and without Power Play
"""

import re
from datetime import date, datetime
from typing import Dict, Iterable, Optional

from bs4 import BeautifulSoup

from lottery_common import (
    JACKPOT_PRIZE, MATCH_LEVELS, LotteryScraper, ScrapeError,
    format_white_balls, parse_count, parse_date, parse_money,
)


class PowerBallScraper(LotteryScraper):
    """Scraper for PowerBall drawing results."""

    LOTTERY = 'powerball'
    BASE_URL = "https://www.powerball.com/draw-result"
    FIRST_DRAWING = '1992-04-22'
    MONDAY_DRAWINGS_START = date(2021, 8, 23)

    # Row classes like "m5-pb" (match 5 + Powerball) or "m4" (match 4)
    _LEVEL_CLASS_RE = re.compile(r'^m(\d)(-pb)?$')
    _LEVEL_BY_BALLS = {(white, bonus): name for name, white, bonus in MATCH_LEVELS}

    def drawing_days(self, day: date) -> Iterable[int]:
        # Wednesday/Saturday, plus Monday from 2021-08-23
        return (0, 2, 5) if day >= self.MONDAY_DRAWINGS_START else (2, 5)

    def get_drawing_data(self, date_str: str) -> Optional[Dict]:
        """
        Fetch drawing data for a specific date.

        Args:
            date_str: Date string in format 'YYYY-MM-DD'

        Returns:
            Row keyed by CSV_COLUMNS, or None if there was no drawing that day
        """
        response = self.session.get(
            self.BASE_URL, params={'gc': 'powerball', 'date': date_str}, timeout=30
        )
        response.raise_for_status()
        return self.parse_page(response.content, date_str)

    def parse_page(self, html: bytes, date_str: str) -> Optional[Dict]:
        """Parse a draw-result page into a row."""
        soup = BeautifulSoup(html, 'html.parser')

        # For a date with no drawing the site shows the nearest earlier drawing instead
        title = soup.find(class_='title-date')
        if title is None:
            raise ScrapeError('draw date not found on page')
        shown = datetime.strptime(title.get_text(strip=True), '%a, %b %d, %Y').date()
        if shown != parse_date(date_str):
            return None

        row = self.new_row(
            date_str,
            jackpot=self._labeled_amount(soup, 'estimated-jackpot'),
            cash_value=self._labeled_amount(soup, 'cash-value'),
        )
        self._fill_numbers(soup, row)
        self._fill_prize_levels(soup, row)
        return row

    @staticmethod
    def _fill_numbers(soup: BeautifulSoup, row: Dict):
        """Winning numbers and Power Play (the site doesn't show numbers for early drawings)."""
        group = soup.find(class_='number-group-powerball')
        whites = [parse_count(b.get_text()) for b in group.find_all(class_='white-balls')] if group else []
        bonus = group.find(class_='powerball') if group else None
        if not whites:
            return
        if len(whites) != 5 or None in whites or bonus is None:
            raise ScrapeError(f'unexpected winning numbers: {whites}')
        row['white_balls'] = format_white_balls(whites)
        row['bonus_ball'] = parse_count(bonus.get_text())
        multiplier = soup.find(class_='multiplier')
        if multiplier is not None:
            row['multiplier'] = parse_count(multiplier.get_text(strip=True).rstrip('xX'))

    @staticmethod
    def _labeled_amount(soup: BeautifulSoup, css_class: str) -> str:
        """Text of e.g. <div class="estimated-jackpot"><span>Label:</span><span>$2.04 Billion</span>."""
        container = soup.find(class_=css_class)
        if container is None:
            return 'N/A'  # cash value wasn't published before 1997
        for span in container.find_all('span'):
            if 'prize-label' not in (span.get('class') or []):
                return span.get_text(strip=True).lstrip('$') or 'N/A'
        return 'N/A'

    def _fill_prize_levels(self, soup: BeautifulSoup, row: Dict):
        table = soup.find('table', class_='winners-table')
        if table is None:
            raise ScrapeError('winners table not found')

        # Columns: match level, Powerball winners, prize, Power Play winners, prize
        # (the Power Play columns are absent before it was introduced in 2001)
        found = set()
        for tr in table.find_all('tr'):
            cells = tr.find_all('td')
            if not cells:
                continue  # header row
            level = self._row_level(cells[0])
            texts = [c.get_text(strip=True) for c in cells] + [''] * 5

            row[f'{level}_winners'] = parse_count(texts[1])
            if level == 'match_5_bonus':
                row[f'{level}_prize'] = JACKPOT_PRIZE
            else:
                row[f'{level}_prize'] = parse_money(texts[2])

            multiplier_winners = parse_count(texts[3])
            if multiplier_winners is not None:
                row[f'{level}_multiplier_winners'] = multiplier_winners
                row[f'{level}_multiplier_prize'] = parse_money(texts[4])
            found.add(level)

        if len(found) != len(MATCH_LEVELS):
            raise ScrapeError(f'expected {len(MATCH_LEVELS)} prize levels, found {len(found)}')

    def _row_level(self, match_cell) -> str:
        """Map a row's match-level cell to a MATCH_LEVELS name via its ball-group CSS class."""
        balls = match_cell.find(class_='game-balls')
        for css_class in (balls.get('class') if balls else None) or []:
            m = self._LEVEL_CLASS_RE.match(css_class)
            if m:
                return self._LEVEL_BY_BALLS[(int(m.group(1)), bool(m.group(2)))]
        raise ScrapeError('unrecognized prize level row')


def main():
    """Example usage."""
    scraper = PowerBallScraper()

    print("Fetching single drawing (2025-11-24)...")
    single_result = scraper.get_drawing_data('2025-11-24')
    if single_result:
        print(f"Jackpot: {single_result['jackpot']}")
        print(f"Cash Value: {single_result['cash_value']}")
        print(f"Match 5 winners: {single_result['match_5_winners']}")

    print("\nFetching historical data...")
    historical_data = scraper.scrape_historical_data('2025-10-01', '2025-11-05')
    scraper.save_to_csv(historical_data, 'powerball_historical.csv')


if __name__ == '__main__':
    main()
