# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Lottery Historical Data Scrapers - Python scripts to scrape PowerBall and MegaMillions drawing results from their official websites, with a unified CSV schema for easy data combination and analysis.

## Key Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests (offline; parse saved fixtures in tests/fixtures/)
python -m unittest discover tests

# Try scrapers on recent data
python powerball_scraper.py
python megamillions_scraper.py

# Update the historical datasets (only fetches drawings missing from the CSV)
python scrape_all_history.py         # PowerBall: 1992-present
python scrape_all_megamillions.py    # MegaMillions: 2010-present

# Re-scrape everything, specific dates, or the last N days
python scrape_all_history.py --full
python scrape_all_history.py --dates 2022-11-07 2016-01-13
python scrape_all_history.py --recent 7

# Check completeness against the drawing schedule and numbers against data.ny.gov
python validate_data.py              # through yesterday; exit 1 on problems
python validate_data.py --offline    # schedule check only

# Run custom examples
python example_usage.py
```

## Architecture

### Shared module (`lottery_common.py`)

- `MATCH_LEVELS` / `CSV_COLUMNS`: the unified 45-column schema, defined once
- `parse_money` / `parse_count` / `format_amount`: handle `$1,000,000`, `$2.04 Billion`, `997.6 Million`
- `make_session()`: `requests` session with urllib3 `Retry` (backoff on connection errors, 429 and 5xx)
- `LotteryScraper`: base class with `get_drawing_dates`, `scrape_historical_data`, `save_to_csv`, context manager
- `run_history_scrape()`: batch runner used by both `scrape_all_*.py` scripts
- `ScrapeError`: raised when a response doesn't have the expected structure

### Scrapers

Both subclass `LotteryScraper` and implement `drawing_days(day)` and `get_drawing_data(date_str)`.
`get_drawing_data` returns a row dict keyed by `CSV_COLUMNS`, returns `None` if there was no
drawing on that date, and raises `requests.RequestException` / `ScrapeError` on failure.
The parsing step is split out (`PowerBallScraper.parse_page`, `MegaMillionsScraper.parse_response`)
so tests can run it on saved fixtures.

**PowerBall** (`powerball_scraper.py`)
- `requests` + `BeautifulSoup` on `https://www.powerball.com/draw-result?gc=powerball&date=YYYY-MM-DD`
- For a date without a drawing the site shows the nearest earlier drawing, so the page's
  `.title-date` is compared with the requested date
- Numbers from `.number-group-powerball` (`.white-balls`, `.powerball`) and `.multiplier`; absent for early drawings
- Jackpot/cash from `.estimated-jackpot` / `.cash-value`; prize levels from `table.winners-table`
- Each table row's level comes from the `.game-balls` element's class (`m5-pb`, `m4`, ...), not row position
- Schedule: Wed/Sat before 2021-08-23, Mon/Wed/Sat after

**MegaMillions** (`megamillions_scraper.py`)
- POSTs to the JSON service `cmspages/utilservice.asmx/GetDrawDataByTickWithMatrix`
  (the endpoint megamillions.com's Previous Drawing page calls); no browser needed
- Body: `{"PlayDateTicks": "<ticks>"}`, dates as .NET DateTime ticks, computed from calendar
  days by `date_to_ticks` (don't use `datetime.timestamp()`, which depends on the local timezone)
- Response `{"d": "<JSON string>"}`; `d` is empty for dates without a drawing
- Numbers from `Drawing` (`N1`-`N5`, `MBall`, `Megaplier`; `-1` means none)
- Tier numbers map to match levels through `PrizeMatrix.PrizeTiers` (`TierWhiteBall`, `TierMegaBall`),
  because tier order differs between prize matrices
- Two multiplier eras (optional Megaplier until 2025-04-04, built-in multiplier since),
  see `SCHEMA_DESIGN.md`
- Schedule: Tuesday and Friday

### Unified CSV Schema (45 columns)

- Base (9): `lottery`, `date`, `white_balls`, `bonus_ball`, `multiplier`, `jackpot`, `cash_value`, `jackpot_usd`, `cash_value_usd`
- Match levels (36): 9 levels x (`_winners`, `_prize`, `_multiplier_winners`, `_multiplier_prize`)
- Level names: `match_5_bonus`, `match_5`, `match_4_bonus`, `match_4`, `match_3_bonus`,
  `match_3`, `match_2_bonus`, `match_1_bonus`, `match_0_bonus`

See `SCHEMA_DESIGN.md` for column semantics per lottery and era.

### Daily update workflow (`.github/workflows/update-data.yml`)

- Runs daily at 14:00 UTC (and on `workflow_dispatch`): tests, then both scrape scripts with
  `--end <yesterday> --recent 7`, then `validate_data.py --through <yesterday>`, then commits changed CSVs to `main`
- Any failing step stops the run before the commit
- On pull requests touching the code it runs the same steps against the live sites but doesn't commit

### Validation (`validate_data.py`)

- **Completeness comes from the schedule**, not from NY: `check_schedule` reports `missing`
  (scheduled date through `--through` not in the CSV) and `unscheduled` rows; `no_local_data` if empty
- **Numbers come from data.ny.gov** (PowerBall `d6yy-54nr`, MegaMillions `5xaw-6ayf`): `check_ny`
  reports `numbers_mismatch` / `multiplier_mismatch` / `no_numbers`, plus `ny_unscheduled` if NY
  has a drawing our schedule logic doesn't expect; drawings absent from NY are not errors
- Confirmed NY errors (cross-checked with the Texas Lottery) live in `KNOWN_NY_ERRATA`
- Run it after any re-scrape

### Historical batch runner (`run_history_scrape`)

- Loads the existing `*_all_history.csv` and fetches only missing drawings (unless `--full` / `--dates`)
- Saves progress to `*_partial.csv` every 50 drawings and on Ctrl+C; the next run resumes from it
- Writes the merged, sorted dataset back to `*_all_history.csv` atomically, then deletes the partial file
- Failed dates (with the exception message) go to `*_scraping_errors.csv`
- 0.5 seconds between requests (`--delay`)

## Testing and Development

When modifying scrapers:
1. Run `python -m unittest discover tests`
2. If a site's markup or JSON changes, save a new response into `tests/fixtures/` and add a test
3. Try a recent date range live (e.g. `python scrape_all_history.py --start 2025-10-01 --end 2025-10-31`
   writes to the real dataset; use `scrape_historical_data` + `save_to_csv` for a scratch file)
4. Run `python validate_data.py` and spot-check for blank winner columns or `N/A` jackpots

## Common Pitfalls

1. **Row order**: don't map prize levels by position; both sites vary the order across eras
2. **Non-drawing dates**: PowerBall silently returns a different drawing; always check the date
3. **Money strings**: jackpots can be in billions; use `parse_money`, not ad-hoc regexes
4. **Schema consistency**: add columns only in `lottery_common.CSV_COLUMNS`
5. **Drawing schedule**: must respect historical schedule changes (PowerBall 2021-08-23)
