"""
Parser tests against saved responses, so they run without network access.

    python -m unittest discover tests
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lottery_common import (  # noqa: E402
    CSV_COLUMNS, ScrapeError, format_amount, parse_count, parse_money, read_csv, write_csv,
)
from megamillions_scraper import MegaMillionsScraper, date_to_ticks  # noqa: E402
from powerball_scraper import PowerBallScraper  # noqa: E402
from validate_data import check_ny, check_schedule, parse_ny_record  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')


def fixture(name, mode='rb'):
    with open(os.path.join(FIXTURES, name), mode) as f:
        return f.read()


class ParsingHelperTests(unittest.TestCase):

    def test_parse_money(self):
        self.assertEqual(parse_money('$1,000,000'), 1_000_000)
        self.assertEqual(parse_money('$2.04 Billion'), 2_040_000_000)
        self.assertEqual(parse_money('997.6 Million'), 997_600_000)
        self.assertEqual(parse_money('$1 Million'), 1_000_000)
        self.assertEqual(parse_money('$4'), 4)
        self.assertIsNone(parse_money('Grand Prize'))
        self.assertIsNone(parse_money('N/A'))
        self.assertIsNone(parse_money(None))

    def test_parse_count(self):
        self.assertEqual(parse_count('1,295,000'), 1_295_000)
        self.assertEqual(parse_count('0'), 0)
        self.assertIsNone(parse_count(''))
        self.assertIsNone(parse_count('N/A'))

    def test_format_amount(self):
        self.assertEqual(format_amount(175_000_000), '175 Million')
        self.assertEqual(format_amount(131_500_000), '131.5 Million')
        self.assertEqual(format_amount(1_600_000_000), '1.6 Billion')
        self.assertEqual(format_amount(2_040_000_000), '2.04 Billion')
        self.assertEqual(format_amount(0), 'N/A')
        self.assertEqual(format_amount(None), 'N/A')

    def test_schema_has_unified_columns(self):
        self.assertEqual(len(CSV_COLUMNS), 45)
        self.assertEqual(len(set(CSV_COLUMNS)), 45)
        self.assertIn('match_5_bonus_winners', CSV_COLUMNS)
        self.assertIn('match_0_bonus_multiplier_prize', CSV_COLUMNS)

    def test_csv_round_trip(self):
        row = dict.fromkeys(CSV_COLUMNS)
        row.update({'lottery': 'powerball', 'date': '2024-01-01', 'match_5_winners': 3})
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'out.csv')
            write_csv([row], path)
            rows = read_csv(path)
        self.assertEqual(list(rows[0]), CSV_COLUMNS)
        self.assertEqual(rows[0]['match_5_winners'], '3')


class PowerBallTests(unittest.TestCase):

    def setUp(self):
        self.scraper = PowerBallScraper()

    def tearDown(self):
        self.scraper.close()

    def test_billion_dollar_jackpot(self):
        row = self.scraper.parse_page(fixture('powerball_2022-11-07.html'), '2022-11-07')
        self.assertEqual(row['jackpot'], '2.04 Billion')
        self.assertEqual(row['jackpot_usd'], 2_040_000_000)
        self.assertEqual(row['cash_value'], '997.6 Million')
        self.assertEqual(row['cash_value_usd'], 997_600_000)

    def test_winning_numbers(self):
        row = self.scraper.parse_page(fixture('powerball_2022-11-07.html'), '2022-11-07')
        self.assertEqual(row['white_balls'], '10 33 41 47 56')
        self.assertEqual(row['bonus_ball'], 10)
        self.assertEqual(row['multiplier'], 2)

    def test_prize_levels(self):
        row = self.scraper.parse_page(fixture('powerball_2022-11-07.html'), '2022-11-07')
        self.assertEqual(row['lottery'], 'powerball')
        self.assertEqual(row['match_5_bonus_winners'], 1)
        self.assertEqual(row['match_5_bonus_prize'], 'Jackpot')
        self.assertEqual(row['match_5_winners'], 22)
        self.assertEqual(row['match_5_prize'], 1_000_000)
        self.assertEqual(row['match_5_multiplier_winners'], 1)
        self.assertEqual(row['match_5_multiplier_prize'], 2_000_000)
        self.assertEqual(row['match_0_bonus_winners'], 5_998_912)
        self.assertEqual(row['match_0_bonus_prize'], 4)
        self.assertEqual(set(row), set(CSV_COLUMNS))

    def test_before_power_play_and_cash_value(self):
        row = self.scraper.parse_page(fixture('powerball_1992-04-22.html'), '1992-04-22')
        self.assertEqual(row['jackpot'], '6 Million')
        self.assertEqual(row['cash_value'], 'N/A')
        self.assertIsNone(row['cash_value_usd'])
        self.assertIsNone(row['white_balls'])  # not shown for early drawings
        self.assertEqual(row['match_5_prize'], 100_000)
        self.assertEqual(row['match_0_bonus_winners'], 47_817)
        self.assertIsNone(row['match_5_multiplier_winners'])

    def test_non_drawing_date_returns_none(self):
        # The site shows the previous drawing (Mon Nov 24) for Tuesday Nov 25
        self.assertIsNone(self.scraper.parse_page(fixture('powerball_2025-11-25.html'), '2025-11-25'))

    def test_drawing_schedule_change(self):
        dates = self.scraper.get_drawing_dates('2021-08-16', '2021-08-28')
        # Wed/Sat before 2021-08-23, Mon/Wed/Sat after
        self.assertEqual(dates, ['2021-08-18', '2021-08-21', '2021-08-23', '2021-08-25', '2021-08-28'])


class MegaMillionsTests(unittest.TestCase):

    def setUp(self):
        self.scraper = MegaMillionsScraper()

    def tearDown(self):
        self.scraper.close()

    def parse(self, date_str):
        payload = json.loads(fixture(f'megamillions_{date_str}.json', 'r'))
        return self.scraper.parse_response(payload, date_str)

    def test_ticks_are_timezone_independent(self):
        self.assertEqual(date_to_ticks(date(2024, 11, 1)), 638660160000000000)
        self.assertEqual(date_to_ticks(date(2025, 11, 25)), 638996256000000000)

    def test_megaplier_era(self):
        row = self.parse('2024-11-01')
        self.assertEqual(row['white_balls'], '11 22 42 46 51')
        self.assertEqual(row['bonus_ball'], 4)
        self.assertEqual(row['multiplier'], 2)
        self.assertEqual(row['jackpot'], '281 Million')
        self.assertEqual(row['jackpot_usd'], 281_000_000)
        self.assertEqual(row['cash_value'], '131.5 Million')
        self.assertEqual(row['match_5_bonus_winners'], 0)
        self.assertEqual(row['match_5_bonus_prize'], 'Jackpot')
        self.assertEqual(row['match_4_bonus_winners'], 18)
        self.assertEqual(row['match_4_bonus_prize'], 10_000)
        self.assertEqual(row['match_5_prize'], 1_000_000)
        # Winners are totals including Megaplier tickets, as the site shows them
        self.assertEqual(row['match_4_winners'], 391)
        self.assertEqual(row['match_4_multiplier_winners'], 84)
        self.assertEqual(row['match_4_multiplier_prize'], 1_000)  # 2x Megaplier drawn
        self.assertEqual(set(row), set(CSV_COLUMNS))

    def test_2010_matrix_tier_order(self):
        # In the 2010-2013 matrix tier 5 is match 2 + MB and tier 6 is match 3
        row = self.parse('2012-03-30')
        self.assertEqual(row['jackpot'], '640 Million')
        self.assertEqual(row['match_5_bonus_winners'], 3)
        self.assertEqual(row['match_3_winners'], 2_086_571)
        self.assertEqual(row['match_3_prize'], 7)
        self.assertEqual(row['match_2_bonus_winners'], 780_589)
        self.assertEqual(row['match_2_bonus_prize'], 10)
        self.assertEqual(row['match_5_multiplier_prize'], 1_000_000)  # capped at $1M

    def test_builtin_multiplier_era(self):
        row = self.parse('2025-11-25')
        self.assertEqual(row['white_balls'], '11 15 31 32 59')
        self.assertEqual(row['bonus_ball'], 18)
        self.assertIsNone(row['multiplier'])  # multipliers are per ticket now
        self.assertEqual(row['jackpot'], '70 Million')
        self.assertEqual(row['match_4_winners'], 102)  # summed over 2x..10x
        self.assertEqual(row['match_4_prize'], 1_000)  # lowest (2x) payout
        self.assertEqual(row['match_0_bonus_prize'], 10)
        self.assertIsNone(row['match_4_multiplier_winners'])
        self.assertIsNone(row['match_4_multiplier_prize'])

    def test_non_drawing_date_returns_none(self):
        self.assertIsNone(self.scraper.parse_response({'d': ''}, '2024-11-02'))

    def test_missing_prize_matrix_uses_cached_matrix(self):
        # The service sometimes omits PrizeMatrix; reuse one seen for the same era
        payload = json.loads(fixture('megamillions_2025-11-25.json', 'r'))
        data = json.loads(payload['d'])
        del data['PrizeMatrix']
        stripped = {'d': json.dumps(data)}

        with self.assertRaises(ScrapeError):
            self.scraper.parse_response(stripped, '2025-11-25')

        self.parse('2025-11-25')  # caches the current matrix
        row = self.scraper.parse_response(stripped, '2025-11-25')
        self.assertEqual(row['match_4_prize'], 1_000)



class ValidationTests(unittest.TestCase):

    def setUp(self):
        self.scraper = PowerBallScraper()

    def tearDown(self):
        self.scraper.close()

    @staticmethod
    def ours(date, whites='01 02 03 04 05', bonus=6, mult=''):
        return {'date': date, 'white_balls': whites, 'bonus_ball': str(bonus), 'multiplier': mult}

    @staticmethod
    def ny(date, whites='01 02 03 04 05', bonus=6, mult=None):
        return {'date': date, 'white_balls': whites, 'bonus_ball': bonus, 'multiplier': mult}

    def test_parse_powerball_record(self):
        record = {'draw_date': '2010-02-03T00:00:00.000',
                  'winning_numbers': '17 22 36 37 52 24', 'multiplier': '2'}
        self.assertEqual(parse_ny_record(record), {
            'date': '2010-02-03', 'white_balls': '17 22 36 37 52', 'bonus_ball': 24, 'multiplier': 2,
        })

    def test_parse_megamillions_record(self):
        record = {'draw_date': '2026-09-22T00:00:00.000', 'winning_numbers': '07 13 26 37 68',
                  'mega_ball': '08'}
        self.assertEqual(parse_ny_record(record), {
            'date': '2026-09-22', 'white_balls': '07 13 26 37 68', 'bonus_ball': 8, 'multiplier': None,
        })

    def test_schedule_check(self):
        # Every PowerBall drawing through 2026-09-21, minus the first and one recent one
        scheduled = self.scraper.get_drawing_dates(PowerBallScraper.FIRST_DRAWING, '2026-09-21')
        ours = [self.ours(d) for d in scheduled if d not in ('1992-04-22', '2026-09-19')]
        ours.append(self.ours('2026-09-15'))  # a Tuesday
        ours.append(self.ours('2026-09-23'))  # after --through: not checked
        issues = {(i['date'], i['issue']) for i in check_schedule(self.scraper, ours, '2026-09-21')}
        self.assertEqual(issues, {
            ('1992-04-22', 'missing'),       # gaps at the start are caught
            ('2026-09-19', 'missing'),       # ...and at the end
            ('2026-09-15', 'unscheduled'),
        })

    def test_schedule_check_fails_on_empty_data(self):
        issues = check_schedule(self.scraper, [], '2026-09-21')
        self.assertEqual([i['issue'] for i in issues], ['no_local_data'])

    def test_ny_check(self):
        ours = [
            self.ours('2026-09-12', mult='2'),                       # matches
            self.ours('2026-09-14', mult='2'),                       # wrong multiplier
            self.ours('2026-09-16', whites='01 02 03 04 07'),        # wrong numbers
            self.ours('2026-09-19'),                                 # not in NY: fine
            self.ours('2026-09-21', whites=''),                      # no numbers
        ]
        ny = {r['date']: r for r in [
            self.ny('2026-09-12', mult=2),
            self.ny('2026-09-14', mult=3),
            self.ny('2026-09-15'),                                   # a Tuesday
            self.ny('2026-09-16'),
            self.ny('2026-09-21'),
            self.ny('2026-09-23'),                                   # after --through
        ]}
        issues = {(i['date'], i['issue']) for i in check_ny(self.scraper, ours, ny, '2026-09-21')}
        self.assertEqual(issues, {
            ('2026-09-14', 'multiplier_mismatch'),
            ('2026-09-15', 'ny_unscheduled'),
            ('2026-09-16', 'numbers_mismatch'),
            ('2026-09-21', 'no_numbers'),
        })

    def test_ny_check_fails_on_empty_ny_data(self):
        issues = check_ny(self.scraper, [self.ours('2026-09-21')], {}, '2026-09-21')
        self.assertEqual([i['issue'] for i in issues], ['no_ny_data'])

    def test_known_ny_errata_are_flagged(self):
        with MegaMillionsScraper() as scraper:
            issues = check_ny(scraper, [self.ours('2011-09-23', whites='21 27 32 40 52', bonus=36)],
                              {'2011-09-23': self.ny('2011-09-23', whites='27 31 32 40 52', bonus=36)},
                              '2011-09-23')
        self.assertEqual([(i['issue'], i['known_ny_error']) for i in issues],
                         [('numbers_mismatch', True)])


if __name__ == '__main__':
    unittest.main()
