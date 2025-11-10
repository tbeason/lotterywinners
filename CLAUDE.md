# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Lottery Historical Data Scrapers - Python scripts to scrape PowerBall and MegaMillions drawing results from their official websites, with a unified CSV schema for easy data combination and analysis.

## Key Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Test scrapers on recent data
python powerball_scraper.py
python megamillions_scraper.py

# Scrape complete historical data
python scrape_all_history.py         # PowerBall: 1992-present (~2 hours, 3,722 drawings)
python scrape_all_megamillions.py    # MegaMillions: 2010-present (~1 hour, 1,646 drawings)

# Run custom examples
python example_usage.py
```

## Architecture

### Dual Scraper Design

The codebase implements two separate scrapers with **identical CSV output schemas** but different scraping technologies:

**PowerBall** (`powerball_scraper.py`)
- Uses `requests` + `BeautifulSoup` for simple HTTP scraping
- Scrapes from powerball.com (server-side rendered HTML)
- Historical data: April 22, 1992 to present
- Drawing schedule: Wed/Sat (before Aug 23, 2021), Mon/Wed/Sat (after)

**MegaMillions** (`megamillions_scraper.py`)
- Uses `Selenium` + `ChromeDriver` for JavaScript-rendered pages
- Scrapes from megamillions.com (client-side rendered)
- Historical data: February 2, 2010 to present
- Drawing schedule: Tuesday and Friday only
- Date encoding: .NET DateTime ticks (100-nanosecond intervals since 0001-01-01)

### Core Scraper Classes

Both classes implement the same interface:

```python
class LotteryScraper:
    def get_drawing_data(date: str) -> Optional[Dict]
    def get_drawing_dates(start_date: str, end_date: str) -> List[str]
    def scrape_historical_data(start_date: str, end_date: str) -> List[Dict]
    def save_to_csv(data: List[Dict], filename: str)
```

### Critical: Drawing Schedule Logic

**PowerBall Schedule Change (2021-08-23)**
- Before: Wednesday and Saturday only
- After: Monday, Wednesday, and Saturday
- The `get_drawing_dates()` method automatically handles this transition
- Hardcoded in `DRAWING_DAYS` constant and schedule logic

**MegaMillions Consistency**
- Tuesday and Friday throughout entire history
- No schedule changes since 2010

### Unified CSV Schema (40 columns)

**Design Rationale**: Both scrapers output identical column names to enable easy data combination.

**Base Columns (4)**:
- `lottery`: Identifier ("powerball" or "megamillions")
- `date`: Drawing date (YYYY-MM-DD)
- `jackpot`: Estimated jackpot (e.g., "175 Million")
- `cash_value`: Cash alternative (e.g., "81.2 Million")

**Match Level Columns (36)**: 9 levels × 4 columns each
- `match_X_bonus_*`: Match with bonus ball (PowerBall/MegaBall)
- `match_X_*`: Match without bonus ball
- `*_winners` / `*_prize`: Regular winner count and prize amount
- `*_multiplier_winners` / `*_multiplier_prize`: Multiplier (Power Play/Megaplier) data

**Critical Schema Transformation**:
- PowerBall: `match_5_pb_*` → `match_5_bonus_*`, `_pp_*` → `_multiplier_*`
- MegaMillions: `match_5_mb_*` → `match_5_bonus_*`, `_megaplier_*` → `_multiplier_*`

See `SCHEMA_DESIGN.md` for complete mapping details.

### HTML/DOM Parsing Strategies

**PowerBall (BeautifulSoup)**:
- Target: `<table class="winners-table">`
- Hardcoded match levels map to table row positions (order-dependent!)
- Row structure: [Match description, PB Winners, PB Prize, PP Winners, PP Prize]
- Uses regex fallbacks for jackpot extraction

**MegaMillions (Selenium)**:
- Waits for JavaScript to populate data: `WebDriverWait` on `js_pastJackpot` class
- Target: `<table class="tableJackpotWinningNumbersNew">`
- Same row structure as PowerBall
- Requires ChromeDriver (managed automatically by webdriver-manager)

### Historical Batch Scrapers

Both `scrape_all_history.py` and `scrape_all_megamillions.py` implement:
- Auto-save every 50 drawings to `*_partial.csv`
- Resume capability (checks for partial file, prompts to continue)
- Rate limiting: 0.5 seconds between requests
- Error logging to `*_scraping_errors.csv`
- Progress tracking with percentage completion
- Final output: `*_all_history.csv`

**Important**: Auto-save uses ASCII characters (>>) not Unicode (→) to avoid encoding errors on Windows console.

## Important Implementation Details

### Date Handling

**PowerBall**: Simple date parameter in URL
```
https://www.powerball.com/draw-result?gc=powerball&date=2024-10-01
```

**MegaMillions**: .NET DateTime ticks encoding
```python
def datetime_to_ticks(dt):
    epoch_offset = 621355968000000000
    unix_timestamp = dt.timestamp()
    return int(unix_timestamp * 10000000 + epoch_offset)

url = f"{BASE_URL}?date={ticks}"
# https://www.megamillions.com/...?date=638659440000000000
```

### Match Levels (Consistent Across Both Lotteries)

Order matters! Hardcoded to match table row order:
1. Match 5 + Bonus (Jackpot)
2. Match 5 ($1 Million)
3. Match 4 + Bonus
4. Match 4
5. Match 3 + Bonus
6. Match 3
7. Match 2 + Bonus
8. Match 1 + Bonus
9. Match 0 + Bonus (Bonus ball only)

### Multiplier Data Handling

Both scrapers extract multiplier (Power Play/Megaplier) data when available:
- Stored in separate columns: `*_multiplier_winners`, `*_multiplier_prize`
- May be `None` if multiplier wasn't available historically
- CSV writer uses `extrasaction='ignore'` to handle missing columns

### Error Handling Strategy

**Network Errors**: Logged but scraping continues
- Allows partial dataset completion even with intermittent failures
- Error details saved to `*_scraping_errors.csv`

**Missing Data**: Returns "N/A" for jackpot/cash value
- Ensures CSV rows are always complete
- Missing prize data handled gracefully

**Encoding Errors**: Unicode characters avoided in console output
- Windows console (cp1252) cannot handle Unicode arrow (→)
- Use ASCII alternatives (>>) in print statements

## Data Sources and Scraping Methods

**PowerBall**: powerball.com - server-side rendered (simple HTTP)
- URL pattern: `/draw-result?gc=powerball&date=YYYY-MM-DD`
- BeautifulSoup parses static HTML
- Fast and reliable

**MegaMillions**: megamillions.com - client-side rendered (JavaScript)
- URL pattern: `/Previous-Drawing-Page.aspx?date={ticks}`
- Selenium renders JavaScript before extraction
- Slower but handles dynamic content
- Requires Chrome browser installed

## Testing and Development

When modifying scrapers:
1. Test with recent dates first (e.g., last month)
2. Verify CSV output has exactly 40 columns
3. Check `lottery` column populates correctly
4. Confirm match level columns use unified naming (bonus/multiplier)
5. Test auto-save functionality triggers at 50-drawing intervals
6. Verify encoding issues don't occur (no Unicode in print statements)

## Common Pitfalls

1. **Match level order**: Hardcoded to table row positions - changing order breaks parsing
2. **Drawing schedule**: Must respect historical schedule changes (PowerBall 2021-08-23)
3. **Date format**: Must be YYYY-MM-DD for PowerBall, converted to ticks for MegaMillions
4. **Selenium cleanup**: Always use context manager (`with`) or call `.close()` explicitly
5. **Schema consistency**: Both scrapers must output identical column names
6. **Unicode in console**: Avoid non-ASCII characters in print statements (Windows encoding issues)
