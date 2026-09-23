"""
Validate the scraped datasets against New York State's open data.

data.ny.gov republishes the official PowerBall and MegaMillions winning numbers.
For the date range both sources cover, this checks that:
- every drawing NY lists is in our CSV, and vice versa (validates the drawing
  schedule logic and catches skipped or extra dates)
- the winning numbers, bonus ball and multiplier match (validates that each
  row is really the drawing for its date)

    python validate_against_ny.py                  # both lotteries
    python validate_against_ny.py powerball
    python validate_against_ny.py --report issues.csv

Exits with status 1 if any discrepancies are found, other than confirmed errors in
the NY data (KNOWN_NY_ERRATA).
"""

import argparse
import csv
import sys
from typing import Dict, List, Optional

from lottery_common import configure_console, format_white_balls, make_session, read_csv

NY_DATASETS = {
    'powerball': 'https://data.ny.gov/resource/d6yy-54nr.json',
    'megamillions': 'https://data.ny.gov/resource/5xaw-6ayf.json',
}

# Discrepancies where a third source (the Texas Lottery's published history) agrees
# with our data, i.e. errors in the NY dataset. Reported, but not counted as failures.
KNOWN_NY_ERRATA = {
    ('megamillions', '2011-09-23'): 'NY lists 31 instead of 21',
    ('megamillions', '2013-10-18'): 'drawing missing from NY data',
    ('megamillions', '2022-05-10'): 'NY lists Mega Ball 6 instead of 9',
    ('powerball', '2014-06-28'): 'drawing missing from NY data',
    ('powerball', '2017-06-10'): 'drawing missing from NY data',
    ('powerball', '2021-04-28'): 'drawing missing from NY data',
    ('powerball', '2022-03-12'): 'drawing missing from NY data',
    ('powerball', '2022-04-09'): 'drawing missing from NY data',
    ('powerball', '2022-11-07'): 'drawing missing from NY data',
}

HISTORY_FILES = {
    'powerball': 'powerball_all_history.csv',
    'megamillions': 'megamillions_all_history.csv',
}


def parse_ny_record(record: Dict) -> Optional[Dict]:
    """
    Normalize one NY row to {date, white_balls, bonus_ball, multiplier}.

    PowerBall rows put the Powerball as the 6th number in `winning_numbers`;
    MegaMillions rows have a separate `mega_ball` field.
    """
    try:
        numbers = [int(n) for n in record['winning_numbers'].split()]
        if 'mega_ball' in record:
            whites, bonus = numbers, int(record['mega_ball'])
        else:
            whites, bonus = numbers[:5], numbers[5]
    except (KeyError, ValueError, IndexError):
        return None
    if len(whites) != 5:
        return None
    multiplier = (record.get('multiplier') or '').strip().rstrip('xX')
    return {
        'date': record['draw_date'][:10],
        'white_balls': format_white_balls(whites),
        'bonus_ball': bonus,
        'multiplier': int(multiplier) if multiplier.isdigit() else None,
    }


def fetch_ny(lottery: str) -> Dict[str, Dict]:
    """All NY records for a lottery, keyed by date."""
    with make_session() as session:
        response = session.get(
            NY_DATASETS[lottery],
            params={'$limit': 50000, '$order': 'draw_date'},
            timeout=60,
        )
        response.raise_for_status()
    records = (parse_ny_record(r) for r in response.json())
    return {r['date']: r for r in records if r}


def _int_or_none(value) -> Optional[int]:
    return int(value) if value not in (None, '') else None


def compare(lottery: str, ours: List[Dict], ny: Dict[str, Dict]) -> List[Dict]:
    """Discrepancies between our rows and NY's, over the date range both cover."""
    ours_by_date = {r['date']: r for r in ours}
    if not ours_by_date or not ny:
        return []
    start = max(min(ours_by_date), min(ny))
    end = min(max(ours_by_date), max(ny))

    issues = []

    def issue(date, kind, detail):
        known = (lottery, date) in KNOWN_NY_ERRATA
        issues.append({'lottery': lottery, 'date': date, 'issue': kind, 'detail': detail,
                       'known_ny_error': known})

    for date in sorted(set(ours_by_date) | set(ny)):
        if not start <= date <= end:
            continue
        mine, theirs = ours_by_date.get(date), ny.get(date)
        if theirs is None:
            issue(date, 'not_in_ny', 'drawing in our data but not in NY data')
            continue
        if mine is None:
            issue(date, 'missing', f"NY has {theirs['white_balls']} + {theirs['bonus_ball']}")
            continue

        if not mine.get('white_balls'):
            issue(date, 'no_numbers', 'our row has no winning numbers')
            continue
        if (mine['white_balls'] != theirs['white_balls']
                or _int_or_none(mine['bonus_ball']) != theirs['bonus_ball']):
            issue(date, 'numbers_mismatch',
                  f"ours {mine['white_balls']} + {mine['bonus_ball']}, "
                  f"NY {theirs['white_balls']} + {theirs['bonus_ball']}")

        # Only compare multipliers when both sources have one
        mine_mult = _int_or_none(mine.get('multiplier'))
        if mine_mult is not None and theirs['multiplier'] is not None and mine_mult != theirs['multiplier']:
            issue(date, 'multiplier_mismatch', f"ours {mine_mult}x, NY {theirs['multiplier']}x")

    return issues


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Validate scraped data against data.ny.gov.')
    parser.add_argument('lotteries', nargs='*', metavar='LOTTERY',
                        help=f"any of {', '.join(NY_DATASETS)} (default: all)")
    parser.add_argument('--report', metavar='FILE', help='write all discrepancies to a CSV file')
    args = parser.parse_args(argv)

    unknown = set(args.lotteries) - set(NY_DATASETS)
    if unknown:
        parser.error(f"unknown lottery: {', '.join(sorted(unknown))}")

    configure_console()
    all_issues = []
    for lottery in args.lotteries or NY_DATASETS:
        ours = read_csv(HISTORY_FILES[lottery])
        ny = fetch_ny(lottery)
        issues = compare(lottery, ours, ny)
        all_issues.extend(issues)

        print(f"{lottery}: {len(ours)} rows in {HISTORY_FILES[lottery]}, "
              f"{len(ny)} NY records ({min(ny)} to {max(ny)})")
        for i in issues:
            if i['known_ny_error']:
                print(f"  known NY error on {i['date']}: {KNOWN_NY_ERRATA[(lottery, i['date'])]}")
        counts = {}
        for i in issues:
            if not i['known_ny_error']:
                counts[i['issue']] = counts.get(i['issue'], 0) + 1
        if not counts:
            print("  OK - no unexplained discrepancies")
        for kind, count in sorted(counts.items()):
            examples = ', '.join(i['date'] for i in issues
                                 if i['issue'] == kind and not i['known_ny_error'])
            if len(examples) > 70:
                examples = examples[:70] + '...'
            print(f"  {kind}: {count} ({examples})")

    if args.report:
        with open(args.report, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['lottery', 'date', 'issue', 'detail', 'known_ny_error'])
            writer.writeheader()
            writer.writerows(all_issues)
        print(f"Report saved to {args.report}")

    return 1 if any(not i['known_ny_error'] for i in all_issues) else 0


if __name__ == '__main__':
    sys.exit(main())
