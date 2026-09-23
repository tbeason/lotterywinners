# Lottery Historical Data Scrapers

Python scripts to scrape PowerBall and MegaMillions drawing results from their official websites.

## Features

### PowerBall Scraper
- Fetch PowerBall drawing results from powerball.com
- Historical data from April 22, 1992 to present
- Drawing schedule: Wed/Sat (before Aug 23, 2021), Mon/Wed/Sat (after)
- Includes Power Play multiplier data

### MegaMillions Scraper
- Fetch MegaMillions drawing results from megamillions.com
- Historical data from February 2, 2010 to present
- Drawing schedule: Tuesday and Friday
- Includes Megaplier multiplier data (through April 2025)
- Reads the JSON service behind megamillions.com (no browser needed)

### Both Scrapers Include
- Winning numbers, bonus ball, and drawn multiplier
- Estimated jackpot amounts and cash values
- Number of winners at each prize level (9 levels total)
- Multiplier winner data (Power Play / Megaplier)
- **Unified CSV schema** - both lotteries use identical column names
- Export to CSV format (one row per date)
- Automatic date range scraping
- Incremental updates and resume capability for long-running scrapes
- Automatic retries with backoff for transient network errors

## Installation

1. Install required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Quick Start - PowerBall

Run the example script:

```bash
python powerball_scraper.py
```

This will fetch a recent drawing and scrape historical data from October 1 to November 5, 2025.

### Quick Start - MegaMillions

Run the example script:

```bash
python megamillions_scraper.py
```

This will fetch a recent drawing and scrape historical data from October 1 to November 8, 2024.

### Custom Date Range - PowerBall

```python
from powerball_scraper import PowerBallScraper

scraper = PowerBallScraper()

# Scrape data from January 1 to December 31, 2024
data = scraper.scrape_historical_data('2024-01-01', '2024-12-31')

# Save to CSV
scraper.save_to_csv(data, 'powerball_2024.csv')
```

### Custom Date Range - MegaMillions

```python
from megamillions_scraper import MegaMillionsScraper

with MegaMillionsScraper() as scraper:
    # Scrape data from January 1 to December 31, 2024
    data = scraper.scrape_historical_data('2024-01-01', '2024-12-31')

    # Save to CSV
    scraper.save_to_csv(data, 'megamillions_2024.csv')
```

### Single Drawing

```python
from powerball_scraper import PowerBallScraper
from megamillions_scraper import MegaMillionsScraper

# PowerBall
pb_scraper = PowerBallScraper()
result = pb_scraper.get_drawing_data('2024-10-01')
print(f"PowerBall Jackpot: {result['jackpot']}")

# MegaMillions
with MegaMillionsScraper() as mm_scraper:
    result = mm_scraper.get_drawing_data('2024-10-01')
    print(f"MegaMillions Jackpot: {result['jackpot']}")
```

### Full Historical Scrape

```bash
# PowerBall (1992-present)
python scrape_all_history.py

# MegaMillions (2010-present)
python scrape_all_megamillions.py
```

Each script only fetches drawings missing from its `*_all_history.csv`, so re-running it
brings the dataset up to date. Options:

```bash
python scrape_all_history.py --full                          # re-scrape every drawing
python scrape_all_history.py --dates 2022-11-07 2016-01-13   # re-scrape specific dates
python scrape_all_history.py --start 2024-01-01 --end 2024-12-31
```

Progress is saved to `*_partial.csv` every 50 drawings (and on Ctrl+C); the next run resumes
from it. Dates that fail are listed in `*_scraping_errors.csv`.

### Validation Against NY Open Data

```bash
python validate_against_ny.py                 # both lotteries
python validate_against_ny.py --report issues.csv
```

Compares the datasets with the official winning numbers republished at
[data.ny.gov](https://data.ny.gov) (PowerBall from 2010-02-03, MegaMillions from 2002).
Over the overlapping date range it reports drawings missing from either source and any
mismatched numbers or multipliers, and exits with status 1 if there are discrepancies.

### Tests

```bash
python -m unittest discover tests
```

The tests parse saved pages in `tests/fixtures/`, so they don't need network access.

## Unified CSV Schema

Both scrapers now use an identical, unified schema for easy data combination and analysis.

### Basic Columns
- `lottery`: Lottery identifier ("powerball" or "megamillions")
- `date`: Drawing date (YYYY-MM-DD)
- `white_balls`: The five white balls, sorted and zero-padded (e.g., "02 07 09 17 58"); blank for early PowerBall drawings the site doesn't show
- `bonus_ball`: Powerball / Mega Ball number
- `multiplier`: Power Play / Megaplier drawn (blank when none was drawn)
- `jackpot`: Estimated jackpot amount (e.g., "175 Million", "2.04 Billion")
- `cash_value`: Cash alternative value (e.g., "81.2 Million"; "N/A" before 1997 for PowerBall)
- `jackpot_usd`, `cash_value_usd`: The same amounts as whole dollars (blank when unknown)

### Match Level Columns (9 prize levels)

Each match level has 4 columns:
- `match_X_winners`: Number of winners (see SCHEMA_DESIGN.md for how multiplier tickets are counted)
- `match_X_prize`: Prize amount in dollars (`Jackpot` for the top level)
- `match_X_multiplier_winners`: Number of multiplier winners (Power Play / Megaplier)
- `match_X_multiplier_prize`: Prize amount for multiplier winners

**Match Levels:**
1. `match_5_bonus`: Match 5 + bonus ball (PowerBall/MegaBall) - **Jackpot**
2. `match_5`: Match 5 white balls only - **$1 Million**
3. `match_4_bonus`: Match 4 + bonus ball
4. `match_4`: Match 4 white balls
5. `match_3_bonus`: Match 3 + bonus ball
6. `match_3`: Match 3 white balls
7. `match_2_bonus`: Match 2 + bonus ball
8. `match_1_bonus`: Match 1 + bonus ball
9. `match_0_bonus`: Match 0 + bonus ball only

### Total: 45 columns
- 9 base columns (lottery, date, white_balls, bonus_ball, multiplier, jackpot, cash_value, jackpot_usd, cash_value_usd)
- 36 match level columns (9 levels × 4 columns each)

### Example CSV Row
```csv
lottery,date,white_balls,bonus_ball,multiplier,jackpot,cash_value,jackpot_usd,cash_value_usd,match_5_bonus_winners,match_5_bonus_prize,...
powerball,2022-11-07,10 33 41 47 56,10,2,2.04 Billion,997.6 Million,2040000000,997600000,1,Jackpot,...
megamillions,2024-11-01,11 22 42 46 51,4,2,281 Million,131.5 Million,281000000,131500000,0,Jackpot,...
```

## Data Sources

- **PowerBall**: Scrapes from powerball.com using BeautifulSoup (server-side rendered)
- **MegaMillions**: Reads the JSON service (`GetDrawDataByTickWithMatrix`) that megamillions.com's Previous Drawing page uses

## Drawing Schedules

### PowerBall
- **Before August 23, 2021**: Wednesday and Saturday only
- **From August 23, 2021 onwards**: Monday, Wednesday, and Saturday
- **First drawing**: April 22, 1992

### MegaMillions
- **Schedule**: Tuesday and Friday (consistent since 2010)
- **First available data**: February 2, 2010

## Key Differences Between Lotteries

| Feature | PowerBall | MegaMillions |
|---------|-----------|--------------|
| **Scraping method** | BeautifulSoup (HTML page) | JSON service |
| **Historical start** | April 22, 1992 | February 2, 2010 |
| **Drawing days** | Mon/Wed/Sat (Wed/Sat before 2021) | Tue/Fri |
| **Bonus ball name** | PowerBall | MegaBall |
| **Multiplier name** | Power Play | Megaplier (built into every ticket since April 2025) |
| **CSV schema** | **Unified** (same as MegaMillions) | **Unified** (same as PowerBall) |

## Schema Benefits

The unified schema provides several advantages:

1. **Easy data combination**: Merge PowerBall and MegaMillions data into a single dataset
2. **Consistent analysis**: Same column names work for both lotteries
3. **Clear identification**: `lottery` column distinguishes the games
4. **Future-proof**: Easy to add more lotteries with the same schema

## Notes

- Prize amounts may vary over time, but match levels remain consistent
- Power Play/Megaplier data is included when available (Power Play started in 2001; the
  optional Megaplier ended in April 2025 when MegaMillions built a multiplier into every ticket)
- The scrapers respect servers with appropriate rate limiting (0.5s between requests)
- Both scrapers include auto-save functionality (every 50 drawings)
- Resume capability allows interrupted scrapes to continue from where they left off
- Each drawing's date is checked against the date requested; the sites return the nearest
  earlier drawing (PowerBall) or nothing (MegaMillions) for dates without a drawing

## Files

- `lottery_common.py` - Shared schema, parsing helpers, base scraper class, and batch runner
- `powerball_scraper.py` - PowerBall scraper class
- `megamillions_scraper.py` - MegaMillions scraper class
- `example_usage.py` - Examples, including combining both lotteries into one CSV
- `validate_against_ny.py` - Cross-checks winning numbers and drawing dates against data.ny.gov
- `scrape_all_history.py` - Full PowerBall historical scraper
- `scrape_all_megamillions.py` - Full MegaMillions historical scraper
- `requirements.txt` - Python dependencies
- `SCHEMA_DESIGN.md` - Detailed schema design documentation
- `tests/` - Parser tests with saved page fixtures

## Complete Historical Datasets

The repository includes complete historical datasets:
- `powerball_all_history.csv` - PowerBall drawings (1992-04-22 to present)
- `megamillions_all_history.csv` - MegaMillions drawings (2010-02-02 to present)

Both use the unified schema format.
