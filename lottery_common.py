"""
Shared schema, parsing helpers, and batch runner for the lottery scrapers.

Both scrapers produce rows keyed by CSV_COLUMNS so their output can be
concatenated directly.
"""

import argparse
import csv
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# (column base name, white balls matched, bonus ball matched), in prize order
MATCH_LEVELS = [
    ('match_5_bonus', 5, True),   # Jackpot
    ('match_5', 5, False),
    ('match_4_bonus', 4, True),
    ('match_4', 4, False),
    ('match_3_bonus', 3, True),
    ('match_3', 3, False),
    ('match_2_bonus', 2, True),
    ('match_1_bonus', 1, True),
    ('match_0_bonus', 0, True),
]

LEVEL_FIELDS = ('winners', 'prize', 'multiplier_winners', 'multiplier_prize')

BASE_COLUMNS = [
    'lottery', 'date', 'white_balls', 'bonus_ball', 'multiplier',
    'jackpot', 'cash_value', 'jackpot_usd', 'cash_value_usd',
]

CSV_COLUMNS = BASE_COLUMNS + [
    f'{level}_{field}' for level, _, _ in MATCH_LEVELS for field in LEVEL_FIELDS
]

JACKPOT_PRIZE = 'Jackpot'

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


class ScrapeError(Exception):
    """The response didn't have the structure the scraper expects."""


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_MONEY_RE = re.compile(r'\$?\s*(\d[\d,]*(?:\.\d+)?)\s*(million|billion)?', re.IGNORECASE)
_SCALE = {'million': 1_000_000, 'billion': 1_000_000_000}


def parse_money(text: Optional[str]) -> Optional[int]:
    """Parse '$1,000,000', '$2.04 Billion' or '997.6 Million' into whole dollars."""
    match = _MONEY_RE.search(text or '')
    if not match:
        return None
    value = float(match.group(1).replace(',', ''))
    scale = _SCALE.get((match.group(2) or '').lower(), 1)
    return int(round(value * scale))


def parse_count(text: Optional[str]) -> Optional[int]:
    """Parse a winner count like '1,234'. Returns None for blank/non-numeric text."""
    cleaned = (text or '').replace(',', '').strip()
    return int(cleaned) if cleaned.isdigit() else None


def format_amount(usd: Optional[int]) -> str:
    """Format whole dollars for display, e.g. 175 Million or 2.04 Billion."""
    if not usd:
        return 'N/A'
    if usd >= 1_000_000_000:
        return f'{usd / 1e9:.2f}'.rstrip('0').rstrip('.') + ' Billion'
    return f'{usd / 1e6:.1f}'.removesuffix('.0') + ' Million'


def format_white_balls(numbers: Iterable[int]) -> str:
    """Format white balls as sorted, zero-padded, space-separated: '02 07 09 17 58'."""
    return ' '.join(f'{n:02d}' for n in sorted(numbers))


def parse_date(value: str) -> date:
    """Parse a 'YYYY-MM-DD' string."""
    return datetime.strptime(value, '%Y-%m-%d').date()


def make_session() -> requests.Session:
    """HTTP session that retries transient failures with exponential backoff."""
    retry = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=None,  # also retry POST; every request we make is a read
    )
    session = requests.Session()
    session.mount('https://', HTTPAdapter(max_retries=retry))
    session.headers['User-Agent'] = USER_AGENT
    return session


def configure_console():
    """Keep print() from crashing on non-ASCII text in the Windows console."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)


# ---------------------------------------------------------------------------
# CSV I/O
# ---------------------------------------------------------------------------

def write_csv(rows: Iterable[Dict], filename: str):
    """Write rows in the unified schema, sorted by lottery and date."""
    rows = sorted(rows, key=lambda r: (r['lottery'], r['date']))
    tmp = filename + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, filename)  # atomic, so an interrupted write can't truncate the file


def read_csv(filename: str) -> List[Dict]:
    """Read a CSV written by write_csv. Returns [] if the file doesn't exist."""
    if not os.path.exists(filename):
        return []
    with open(filename, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Base scraper
# ---------------------------------------------------------------------------

class LotteryScraper:
    """
    Common interface for both lotteries.

    Subclasses set LOTTERY and implement drawing_days() and get_drawing_data().
    """

    LOTTERY = ''

    def __init__(self):
        self.session = make_session()

    def drawing_days(self, day: date) -> Iterable[int]:
        """Weekdays (Monday=0) the lottery drew on in the week containing `day`."""
        raise NotImplementedError

    def get_drawing_data(self, date_str: str) -> Optional[Dict]:
        """
        Fetch one drawing as a row keyed by CSV_COLUMNS.

        Returns None if no drawing was held (or has been published) for that date.
        Raises requests.RequestException or ScrapeError if the fetch fails.
        """
        raise NotImplementedError

    def new_row(self, date_str: str, jackpot: str, cash_value: str) -> Dict:
        """Row with base columns filled in and every match column blank."""
        row = dict.fromkeys(CSV_COLUMNS)
        row.update({
            'lottery': self.LOTTERY,
            'date': date_str,
            'jackpot': jackpot,
            'cash_value': cash_value,
            'jackpot_usd': parse_money(jackpot),
            'cash_value_usd': parse_money(cash_value),
        })
        return row

    def get_drawing_dates(self, start_date: str, end_date: str) -> List[str]:
        """Scheduled drawing dates between start_date and end_date inclusive."""
        day, end = parse_date(start_date), parse_date(end_date)
        dates = []
        while day <= end:
            if day.weekday() in self.drawing_days(day):
                dates.append(day.isoformat())
            day += timedelta(days=1)
        return dates

    def scrape_historical_data(self, start_date: str, end_date: str, delay: float = 0.5) -> List[Dict]:
        """Scrape every drawing in a date range, skipping dates that fail."""
        dates = self.get_drawing_dates(start_date, end_date)
        results = []
        print(f"Scraping {len(dates)} drawings from {start_date} to {end_date}...")
        for i, date_str in enumerate(dates, 1):
            print(f"Fetching {i}/{len(dates)}: {date_str}", end='\r')
            try:
                row = self.get_drawing_data(date_str)
            except (requests.RequestException, ScrapeError) as e:
                print(f"\nError fetching {date_str}: {e}")
                row = None
            if row:
                results.append(row)
            time.sleep(delay)
        print(f"\nCompleted! Retrieved {len(results)} drawings.")
        return results

    def save_to_csv(self, data: List[Dict], filename: str):
        """Save rows to a CSV file in the unified schema."""
        if not data:
            print("No data to save.")
            return
        write_csv(data, filename)
        print(f"Data saved to {filename}")

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def run_history_scrape(scraper: LotteryScraper, first_drawing: str, output_file: str,
                       partial_file: str, error_file: str, argv=None):
    """
    Bring output_file up to date with every drawing since first_drawing.

    By default only drawings missing from output_file are fetched, so re-running
    just picks up new drawings. Progress is saved to partial_file every 50
    drawings (and on Ctrl+C); the next run resumes from it.
    """
    parser = argparse.ArgumentParser(description=f'Scrape {scraper.LOTTERY} drawing history.')
    parser.add_argument('--full', action='store_true',
                        help='re-scrape every drawing instead of only missing ones')
    parser.add_argument('--dates', nargs='+', default=[], metavar='YYYY-MM-DD',
                        help='also re-scrape these specific dates')
    parser.add_argument('--start', default=first_drawing, help='first date to consider')
    parser.add_argument('--end', default=date.today().isoformat(), help='last date to consider')
    parser.add_argument('--delay', type=float, default=0.5, help='seconds between requests')
    args = parser.parse_args(argv)

    configure_console()
    print(f"{scraper.LOTTERY} historical data scraper")
    print("=" * 50)

    rows = {r['date']: r for r in read_csv(output_file)}
    print(f"Existing drawings in {output_file}: {len(rows)}")

    fresh = set()  # dates scraped by this or the interrupted run; never re-fetched
    for row in read_csv(partial_file):
        rows[row['date']] = row
        fresh.add(row['date'])
    if fresh:
        print(f"Resuming: {len(fresh)} drawings loaded from {partial_file}")

    scheduled = scraper.get_drawing_dates(args.start, args.end)
    if args.full:
        todo = scheduled
    else:
        todo = [d for d in scheduled if d not in rows]
    for d in args.dates:
        parse_date(d)  # validate format
        if d not in todo:
            todo.append(d)
    todo = sorted(d for d in todo if d not in fresh)

    print(f"Drawings to scrape: {len(todo)}")
    print()

    def fetch(date_str):
        # The sites occasionally serve an incomplete page with status 200; retry those
        attempts = 5
        for attempt in range(1, attempts + 1):
            try:
                return scraper.get_drawing_data(date_str)
            except ScrapeError:
                if attempt == attempts:
                    raise
                time.sleep(5)

    errors = []
    scraped = 0
    save_interval = 50
    try:
        for i, date_str in enumerate(todo, 1):
            try:
                row = fetch(date_str)
            except (requests.RequestException, ScrapeError) as e:
                errors.append({'date': date_str, 'error': f'{type(e).__name__}: {e}'})
                print(f"ERROR on {date_str}: {e}")
            else:
                if row is None:
                    errors.append({'date': date_str, 'error': 'No drawing published for this date'})
                    print(f"No drawing found for {date_str}")
                else:
                    rows[date_str] = row
                    fresh.add(date_str)
                    scraped += 1
                    if scraped % save_interval == 0:
                        write_csv([rows[d] for d in fresh], partial_file)
                        print(f"  >> Auto-saved progress to {partial_file}")

            if i % 10 == 0 or i == len(todo):
                print(f"Progress: {i}/{len(todo)} ({i / len(todo) * 100:.1f}%) - Latest: {date_str}")
            time.sleep(args.delay)
    except KeyboardInterrupt:
        write_csv([rows[d] for d in fresh], partial_file)
        print(f"\nInterrupted. Progress saved to {partial_file}; re-run to resume.")
        raise

    write_csv(rows.values(), output_file)
    if os.path.exists(partial_file):
        os.remove(partial_file)

    print()
    print("=" * 50)
    print(f"Scraped: {scraped}  Errors: {len(errors)}  Total drawings: {len(rows)}")
    print(f"Data saved to: {output_file}")

    if errors:
        with open(error_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['date', 'error'])
            writer.writeheader()
            writer.writerows(errors)
        print(f"Error log saved to: {error_file}")
    elif os.path.exists(error_file):
        os.remove(error_file)  # don't leave a stale log from an earlier run
