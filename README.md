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
- Includes Megaplier multiplier data
- Uses Selenium to handle JavaScript-rendered pages

### Both Scrapers Include
- Estimated jackpot amounts and cash values
- Number of winners at each prize level (9 levels total)
- Multiplier winner data (Power Play / Megaplier)
- **Unified CSV schema** - both lotteries use identical column names
- Export to CSV format (one row per date)
- Automatic date range scraping
- Resume capability for long-running scrapes

## Installation

1. Install required dependencies:

```bash
pip install -r requirements.txt
```

For MegaMillions scraping, you'll also need Chrome browser installed (Selenium will manage the ChromeDriver automatically).

## Usage

### Quick Start - PowerBall

Run the example script:

```bash
python powerball_scraper.py
```

This will fetch a recent drawing and scrape historical data from October 1 to November 5, 2024.

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

with MegaMillionsScraper(headless=True) as scraper:
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
# PowerBall (1992-present, ~3,722 drawings)
python scrape_all_history.py

# MegaMillions (2010-present, ~1,646 drawings)
python scrape_all_megamillions.py
```

## Unified CSV Schema

Both scrapers now use an identical, unified schema for easy data combination and analysis.

### Basic Columns
- `lottery`: Lottery identifier ("powerball" or "megamillions")
- `date`: Drawing date (YYYY-MM-DD)
- `jackpot`: Estimated jackpot amount (e.g., "175 Million")
- `cash_value`: Cash alternative value (e.g., "81.2 Million")

### Match Level Columns (9 prize levels)

Each match level has 4 columns:
- `match_X_winners`: Number of regular winners
- `match_X_prize`: Prize amount for regular winners
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

### Total: 40 columns
- 4 base columns (lottery, date, jackpot, cash_value)
- 36 match level columns (9 levels × 4 columns each)

### Example CSV Row
```csv
lottery,date,jackpot,cash_value,match_5_bonus_winners,match_5_bonus_prize,...
powerball,2024-10-01,175 Million,81.2 Million,0,Jackpot,0,,1,1000000,0,2000000,...
megamillions,2024-10-01,93 Million,46.4 Million,0,Jackpot,,,1,1,0,2,...
```

## Data Sources

- **PowerBall**: Scrapes from powerball.com using BeautifulSoup (server-side rendered)
- **MegaMillions**: Scrapes from megamillions.com using Selenium (JavaScript-rendered)

## Drawing Schedules

### PowerBall
- **Before August 23, 2021**: Wednesday and Saturday only
- **From August 23, 2021 onwards**: Monday, Wednesday, and Saturday
- **First drawing**: April 22, 1992
- **Total historical drawings**: ~3,722

### MegaMillions
- **Schedule**: Tuesday and Friday (consistent since 2010)
- **First available data**: February 2, 2010
- **Total historical drawings**: ~1,646

## Key Differences Between Lotteries

| Feature | PowerBall | MegaMillions |
|---------|-----------|--------------|
| **Scraping method** | BeautifulSoup (simple HTTP) | Selenium (JavaScript rendering) |
| **Historical start** | April 22, 1992 | February 2, 2010 |
| **Drawing days** | Mon/Wed/Sat (Wed/Sat before 2021) | Tue/Fri |
| **Bonus ball name** | PowerBall | MegaBall |
| **Multiplier name** | Power Play | Megaplier |
| **CSV schema** | **Unified** (same as MegaMillions) | **Unified** (same as PowerBall) |

## Schema Benefits

The unified schema provides several advantages:

1. **Easy data combination**: Merge PowerBall and MegaMillions data into a single dataset
2. **Consistent analysis**: Same column names work for both lotteries
3. **Clear identification**: `lottery` column distinguishes the games
4. **Future-proof**: Easy to add more lotteries with the same schema

## Notes

- Prize amounts may vary over time, but match levels remain consistent
- Power Play/Megaplier data is included when available
- The scrapers respect servers with appropriate rate limiting (0.5s between requests)
- Both scrapers include auto-save functionality (every 50 drawings)
- Resume capability allows interrupted scrapes to continue from where they left off
- MegaMillions scraper requires Chrome browser (ChromeDriver managed automatically)

## Files

- `powerball_scraper.py` - PowerBall scraper class
- `megamillions_scraper.py` - MegaMillions scraper class (with Selenium)
- `scrape_all_history.py` - Full PowerBall historical scraper
- `scrape_all_megamillions.py` - Full MegaMillions historical scraper
- `requirements.txt` - Python dependencies
- `SCHEMA_DESIGN.md` - Detailed schema design documentation

## Complete Historical Datasets

The repository includes complete historical datasets:
- `powerball_all_history.csv` - 3,722 drawings (1992-04-22 to present)
- `megamillions_all_history.csv` - 1,646 drawings (2010-02-02 to present)

Both use the unified schema format.
