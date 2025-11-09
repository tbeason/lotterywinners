# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PowerBall Historical Data Scraper - Python scripts to scrape and analyze PowerBall drawing results from powerball.com (1992-present).

## Key Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run example scraper (recent data)
python powerball_scraper.py

# Scrape complete historical data (1992-present, ~2 hours)
python scrape_all_history.py

# Run custom example
python example_usage.py
```

## Architecture

### Core Components

**`PowerBallScraper` class** (`powerball_scraper.py`)
- Main scraping engine with BeautifulSoup HTML parsing
- Key methods:
  - `get_drawing_data(date)` - Fetch single drawing by date (YYYY-MM-DD)
  - `get_drawing_dates(start, end)` - Generate valid drawing dates respecting historical schedule
  - `scrape_historical_data(start, end)` - Batch scrape with progress tracking
  - `save_to_csv(data, filename)` - Export to one-row-per-date CSV format

**Drawing Schedule Logic** (Critical)
- Before 2021-08-23: Wednesday and Saturday only
- From 2021-08-23 onwards: Monday, Wednesday, and Saturday
- The `get_drawing_dates()` method automatically handles this transition
- Total: ~3,722 drawings from April 22, 1992 to present

**HTML Parsing Strategy**
- Target: `<table class="winners-table">`
- Hardcoded match levels map to table row positions (order-dependent):
  ```python
  ['Match 5 + PB', 'Match 5', 'Match 4 + PB', 'Match 4',
   'Match 3 + PB', 'Match 3', 'Match 2 + PB', 'Match 1 + PB', 'Match 0 + PB']
  ```
- Each row has 5 cells: [Match description, PB Winners, PB Prize, PP Winners, PP Prize]
- Only columns 1-2 are used (regular PowerBall data, not Power Play)

### CSV Output Structure

One row per drawing date with 21 columns:
- `date`, `jackpot`, `cash_value`
- For each of 9 match levels: `match_X_pb_winners`, `match_X_pb_prize` (or `match_X_winners`, `match_X_prize`)

### Historical Scraper (`scrape_all_history.py`)

Long-running batch scraper with:
- Auto-save every 50 drawings to `powerball_partial.csv`
- Resume capability (checks for partial file)
- 2-second rate limiting between requests
- Error logging to `scraping_errors.csv`
- Final output: `powerball_all_history.csv`

## Important Implementation Details

### Date Format
All dates must be in `YYYY-MM-DD` format. The scraper constructs URLs like:
```
https://www.powerball.com/draw-result?gc=powerball&date=2025-10-01
```

### Match Level Priority
The data focuses on **match levels** (e.g., "Match 5 + PB") rather than prize amounts, since prize amounts have varied historically but match levels remain consistent.

### Power Play Exclusion
Power Play data is intentionally excluded because it wasn't available for the entire historical period (1992-present).

### Error Handling
- Network errors: Logged but scraping continues
- Missing data: Returns `N/A` for jackpot/cash value
- Page structure changes: Uses regex fallbacks for jackpot extraction

## Data Source

Scrapes from powerball.com's official draw results page. The site uses server-side rendering (not JavaScript), so `requests` + `BeautifulSoup` is sufficient.
