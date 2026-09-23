"""
MegaMillions Historical Data Scraper

Fetches MegaMillions drawing results from the JSON service behind
megamillions.com's Previous Drawing page, including:
- Date of drawing
- Estimated jackpot amount and cash option value
- Number of winners and prize at each prize level, with Megaplier breakdown
"""

import json
from collections import defaultdict
from datetime import date
from typing import Dict, Iterable, Optional

from lottery_common import (
    JACKPOT_PRIZE, MATCH_LEVELS, LotteryScraper, ScrapeError,
    format_amount, format_white_balls, parse_date,
)


def date_to_ticks(day: date) -> int:
    """
    Convert a date to .NET DateTime ticks (100-nanosecond intervals since 0001-01-01).

    Computed from calendar days so the result doesn't depend on the local timezone.
    """
    return (day - date(1, 1, 1)).days * 864_000_000_000


class MegaMillionsScraper(LotteryScraper):
    """Scraper for MegaMillions drawing results."""

    LOTTERY = 'megamillions'
    API_URL = "https://www.megamillions.com/cmspages/utilservice.asmx/GetDrawDataByTickWithMatrix"
    FIRST_DRAWING = '2010-02-02'  # earliest drawing the site has data for

    # MegaMillions drawing days: Tuesday=1, Friday=4
    DRAWING_DAYS = (1, 4)

    _LEVEL_BY_BALLS = {(white, bonus): name for name, white, bonus in MATCH_LEVELS}

    def __init__(self):
        super().__init__()
        self._matrices = {}  # MatrixID -> prize matrix, reused when a response omits it

    def drawing_days(self, day: date) -> Iterable[int]:
        return self.DRAWING_DAYS

    def get_drawing_data(self, date_str: str) -> Optional[Dict]:
        """
        Fetch drawing data for a specific date.

        Args:
            date_str: Date string in format 'YYYY-MM-DD'

        Returns:
            Row keyed by CSV_COLUMNS, or None if there was no drawing that day
        """
        ticks = date_to_ticks(parse_date(date_str))
        response = self.session.post(self.API_URL, json={'PlayDateTicks': str(ticks)}, timeout=30)
        response.raise_for_status()
        return self.parse_response(response.json(), date_str)

    def parse_response(self, payload: Dict, date_str: str) -> Optional[Dict]:
        """Parse the service's response ({"d": "<JSON string>"}) into a row."""
        body = payload.get('d')
        if not body:
            return None  # no drawing on this date
        try:
            data = json.loads(body)
            if not data['Drawing']['PlayDate'].startswith(date_str):
                return None
            jackpot = data.get('Jackpot') or {}
            row = self.new_row(
                date_str,
                jackpot=format_amount(jackpot.get('CurrentPrizePool')),
                cash_value=format_amount(jackpot.get('CurrentCashValue')),
            )
            self._fill_numbers(data['Drawing'], row)
            self._fill_prize_levels(data, self._prize_matrix(data, date_str), row)
        except (KeyError, TypeError, ValueError) as e:
            raise ScrapeError(f'unexpected response format: {e!r}') from e
        return row

    @staticmethod
    def _fill_numbers(drawing: Dict, row: Dict):
        row['white_balls'] = format_white_balls(drawing[f'N{i}'] for i in range(1, 6))
        row['bonus_ball'] = drawing['MBall']
        # Megaplier drawn with the numbers; -1 once multipliers moved onto tickets (April 2025)
        megaplier = drawing.get('Megaplier')
        row['multiplier'] = megaplier if megaplier and megaplier > 0 else None

    def _prize_matrix(self, data: Dict, date_str: str) -> Dict:
        """
        The drawing's prize matrix. The service intermittently leaves it out, so
        matrices are cached and matched to drawings by their date range.
        """
        matrix = data.get('PrizeMatrix')
        if matrix:
            self._matrices[matrix['MatrixID']] = matrix
            return matrix
        for cached in self._matrices.values():
            end = cached['MatrixEnd'][:10]
            if cached['MatrixStart'][:10] <= date_str and (end == '0001-01-01' or date_str <= end):
                return cached
        raise ScrapeError('response is missing the prize matrix')

    def _fill_prize_levels(self, data: Dict, matrix: Dict, row: Dict):
        # Winner counts are reported per prize tier number. Before April 2025 the
        # Megaplier was an optional add-on, reported as separate IsMegaplier
        # entries. Since then every ticket carries a multiplier and each tier is
        # split by multiplier (2x, 3x, ...); those are summed into one count.
        winners = defaultdict(int)
        megaplier_winners = defaultdict(int)
        for entry in data['PrizeTiers']:
            winners[entry['Tier']] += entry['Winners']
            if entry['IsMegaplier']:
                megaplier_winners[entry['Tier']] += entry['Winners']

        # With the built-in multiplier the lowest payout is the 2x amount; the
        # matrix's base PrizeAmount is never paid out, so record the 2x amount.
        builtin_multiplier = any(entry.get('Multiplier') for entry in data['PrizeTiers'])
        prize_field = 'Mega2' if builtin_multiplier else 'PrizeAmount'

        megaplier = data['Drawing'].get('Megaplier')
        tiers = matrix['PrizeTiers']
        for tier in tiers:
            number = tier['PrizeTier']
            level = self._LEVEL_BY_BALLS[(tier['TierWhiteBall'], tier['TierMegaBall'])]

            row[f'{level}_winners'] = winners.get(number)
            row[f'{level}_prize'] = JACKPOT_PRIZE if tier['IsJackpot'] else int(tier[prize_field])

            if number in megaplier_winners:
                row[f'{level}_multiplier_winners'] = megaplier_winners[number]
                # Matrix columns Mega2..Mega10 hold the prize for each Megaplier value
                prize = tier.get(f'Mega{megaplier}')
                row[f'{level}_multiplier_prize'] = int(prize) if prize else None

        if len(tiers) != len(MATCH_LEVELS):
            raise ScrapeError(f'expected {len(MATCH_LEVELS)} prize tiers, found {len(tiers)}')


def main():
    """Example usage."""
    with MegaMillionsScraper() as scraper:
        print("Fetching single drawing (2024-11-01)...")
        single_result = scraper.get_drawing_data('2024-11-01')
        if single_result:
            print(f"Jackpot: {single_result['jackpot']}")
            print(f"Cash Value: {single_result['cash_value']}")
            print(f"Match 5 winners: {single_result['match_5_winners']}")

        print("\nFetching historical data...")
        historical_data = scraper.scrape_historical_data('2024-10-01', '2024-11-08')
        scraper.save_to_csv(historical_data, 'megamillions_historical.csv')


if __name__ == '__main__':
    main()
