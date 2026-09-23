"""
Validate the scraped datasets.

Two independent checks:

1. Schedule: every scheduled drawing from the lottery's first drawing through
   --through (default: yesterday) is in the CSV, and no row falls on an
   unscheduled date. Runs offline.

2. data.ny.gov: New York State republishes the official PowerBall and
   MegaMillions winning numbers. For drawings in both datasets, the winning
   numbers, bonus ball and multiplier must match, which confirms each row is
   really the drawing for its date. A NY drawing on a date our schedule doesn't
   expect means the schedule logic is wrong. Drawings missing from NY's data are
   only counted: NY has gaps, and the schedule check covers completeness.

    python validate_data.py                   # both lotteries
    python validate_data.py powerball
    python validate_data.py --through 2026-09-21 --report issues.csv
    python validate_data.py --offline         # schedule check only

Exits with status 1 if any problems are found, other than confirmed errors in
the NY data (KNOWN_NY_ERRATA).
"""

import argparse
import csv
import sys
from datetime import date, timedelta
from typing import Dict, List, Optional

from lottery_common import (
    LotteryScraper, configure_console, format_white_balls, make_session, parse_date, read_csv,
)
from megamillions_scraper import MegaMillionsScraper
from powerball_scraper import PowerBallScraper

SCRAPERS = {
    'powerball': PowerBallScraper,
    'megamillions': MegaMillionsScraper,
}

HISTORY_FILES = {
    'powerball': 'powerball_all_history.csv',
    'megamillions': 'megamillions_all_history.csv',
}

NY_DATASETS = {
    'powerball': 'https://data.ny.gov/resource/d6yy-54nr.json',
    'megamillions': 'https://data.ny.gov/resource/5xaw-6ayf.json',
}

# Mismatches where a third source (the Texas Lottery's published history) agrees
# with our data, i.e. errors in the NY dataset. Reported, but not counted as failures.
KNOWN_NY_ERRATA = {
    ('megamillions', '2011-09-23'): 'NY lists 31 instead of 21',
    ('megamillions', '2022-05-10'): 'NY lists Mega Ball 6 instead of 9',
}


def _issue(lottery: str, date_str: str, kind: str, detail: str) -> Dict:
    return {
        'lottery': lottery, 'date': date_str, 'issue': kind, 'detail': detail,
        'known_ny_error': (lottery, date_str) in KNOWN_NY_ERRATA,
    }


# ---------------------------------------------------------------------------
# Schedule check
# ---------------------------------------------------------------------------

def check_schedule(scraper: LotteryScraper, ours: List[Dict], through: str) -> List[Dict]:
    """Scheduled drawings missing from our data, and rows on unscheduled dates."""
    lottery = scraper.LOTTERY
    if not ours:
        return [_issue(lottery, '', 'no_local_data', 'our dataset is empty or missing')]

    scheduled = set(scraper.get_drawing_dates(scraper.FIRST_DRAWING, through))
    have = {r['date'] for r in ours}
    issues = [_issue(lottery, d, 'missing', 'scheduled drawing not in our data')
              for d in sorted(scheduled - have)]
    issues += [_issue(lottery, d, 'unscheduled', 'row on a date with no scheduled drawing')
               for d in sorted(have - scheduled) if d <= through]
    return issues


# ---------------------------------------------------------------------------
# data.ny.gov check
# ---------------------------------------------------------------------------

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


def check_ny(scraper: LotteryScraper, ours: List[Dict], ny: Dict[str, Dict],
             through: str) -> List[Dict]:
    """Number mismatches with NY, and NY drawings on dates our schedule doesn't expect."""
    lottery = scraper.LOTTERY
    if not ny:
        return [_issue(lottery, '', 'no_ny_data', 'NY returned no records')]

    ours_by_date = {r['date']: r for r in ours}
    in_range = [d for d in sorted(ny) if scraper.FIRST_DRAWING <= d <= through]
    scheduled = set(scraper.get_drawing_dates(in_range[0], through)) if in_range else set()

    issues = []
    for date_str in in_range:
        theirs = ny[date_str]
        if date_str not in scheduled:
            issues.append(_issue(lottery, date_str, 'ny_unscheduled',
                                 'NY has a drawing on a date our schedule does not expect'))
        mine = ours_by_date.get(date_str)
        if mine is None:
            continue  # reported by the schedule check if it was scheduled

        if not mine.get('white_balls'):
            issues.append(_issue(lottery, date_str, 'no_numbers', 'our row has no winning numbers'))
            continue
        if (mine['white_balls'] != theirs['white_balls']
                or _int_or_none(mine['bonus_ball']) != theirs['bonus_ball']):
            issues.append(_issue(lottery, date_str, 'numbers_mismatch',
                                 f"ours {mine['white_balls']} + {mine['bonus_ball']}, "
                                 f"NY {theirs['white_balls']} + {theirs['bonus_ball']}"))

        # Only compare multipliers when both sources have one
        mine_mult = _int_or_none(mine.get('multiplier'))
        if mine_mult is not None and theirs['multiplier'] is not None and mine_mult != theirs['multiplier']:
            issues.append(_issue(lottery, date_str, 'multiplier_mismatch',
                                 f"ours {mine_mult}x, NY {theirs['multiplier']}x"))
    return issues


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_issues(lottery: str, issues: List[Dict]):
    for i in issues:
        if i['known_ny_error']:
            print(f"  known NY error on {i['date']}: {KNOWN_NY_ERRATA[(lottery, i['date'])]}")
    counts = {}
    for i in issues:
        if not i['known_ny_error']:
            counts[i['issue']] = counts.get(i['issue'], 0) + 1
    if not counts:
        print("  OK - no problems found")
    for kind, count in sorted(counts.items()):
        examples = ', '.join(i['date'] or i['detail'] for i in issues
                             if i['issue'] == kind and not i['known_ny_error'])
        if len(examples) > 70:
            examples = examples[:70] + '...'
        print(f"  {kind}: {count} ({examples})")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Validate the scraped lottery datasets.')
    parser.add_argument('lotteries', nargs='*', metavar='LOTTERY',
                        help=f"any of {', '.join(SCRAPERS)} (default: all)")
    parser.add_argument('--through', default=(date.today() - timedelta(days=1)).isoformat(),
                        metavar='YYYY-MM-DD',
                        help='last date that should be scraped (default: yesterday)')
    parser.add_argument('--offline', action='store_true', help='skip the data.ny.gov check')
    parser.add_argument('--report', metavar='FILE', help='write all problems to a CSV file')
    args = parser.parse_args(argv)

    unknown = set(args.lotteries) - set(SCRAPERS)
    if unknown:
        parser.error(f"unknown lottery: {', '.join(sorted(unknown))}")
    parse_date(args.through)  # validate format

    configure_console()
    all_issues = []
    for lottery in args.lotteries or SCRAPERS:
        ours = read_csv(HISTORY_FILES[lottery])
        with SCRAPERS[lottery]() as scraper:
            issues = check_schedule(scraper, ours, args.through)
            print(f"{lottery}: {len(ours)} rows in {HISTORY_FILES[lottery]}, "
                  f"checked through {args.through}")
            if not args.offline:
                ny = fetch_ny(lottery)
                issues += check_ny(scraper, ours, ny, args.through)
                if ny:
                    have = {r['date'] for r in ours}
                    gaps = [d for d in have if min(ny) <= d <= max(ny) and d not in ny]
                    print(f"  NY: {len(ny)} records, {len(have & set(ny))} compared; "
                          f"{len(gaps)} of our drawings are absent from NY's data (not an error)")
        _print_issues(lottery, issues)
        all_issues.extend(issues)

    if args.report:
        with open(args.report, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['lottery', 'date', 'issue', 'detail', 'known_ny_error'])
            writer.writeheader()
            writer.writerows(all_issues)
        print(f"Report saved to {args.report}")

    return 1 if any(not i['known_ny_error'] for i in all_issues) else 0


if __name__ == '__main__':
    sys.exit(main())
