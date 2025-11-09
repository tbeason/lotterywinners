# PowerBall Historical Data Scraper

Python scripts to scrape PowerBall drawing results from powerball.com.

## Features

- Fetch PowerBall drawing results by date
- Extract estimated jackpot amounts and cash values
- Get number of winners at each prize level (Match 5 + PB, Match 5, Match 4 + PB, etc.)
- Export data to CSV format (one row per date)
- Scrape historical data across date ranges
- Automatically identifies drawing dates (Monday, Wednesday, Saturday)

## Installation

1. Install required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Quick Start

Run the example script:

```bash
python powerball_scraper.py
```

This will fetch the most recent drawing and scrape historical data from October 1 to November 5, 2025.

### Custom Date Range

```python
from powerball_scraper import PowerBallScraper

scraper = PowerBallScraper()

# Scrape data from January 1 to December 31, 2024
data = scraper.scrape_historical_data('2024-01-01', '2024-12-31')

# Save to CSV
scraper.save_to_csv(data, 'powerball_2024.csv')
```

### Single Drawing

```python
from powerball_scraper import PowerBallScraper

scraper = PowerBallScraper()

# Get specific drawing
result = scraper.get_drawing_data('2025-10-01')

print(f"Jackpot: {result['jackpot']}")
print(f"Cash Value: {result['cash_value']}")
print(f"Number of prize levels: {len(result['prize_levels'])}")
```

### See More Examples

Check out `example_usage.py` for more detailed examples.

## Output Format

The CSV file contains one row per drawing date with the following columns:

### Basic Information
- `date`: Drawing date (YYYY-MM-DD)
- `jackpot`: Estimated jackpot amount (e.g., "175 Million")
- `cash_value`: Cash alternative value (e.g., "81.2 Million")

### Match Level Winners (9 prize levels)
For each match level, there are two columns:
- `match_X_winners`: Number of winners at this level
- `match_X_prize`: Prize amount for this level

Match levels:
- `match_5_pb`: Match 5 + Powerball (Grand Prize)
- `match_5`: Match 5 white balls ($1 Million)
- `match_4_pb`: Match 4 + Powerball ($50,000)
- `match_4`: Match 4 white balls ($100)
- `match_3_pb`: Match 3 + Powerball ($100)
- `match_3`: Match 3 white balls ($7)
- `match_2_pb`: Match 2 + Powerball ($7)
- `match_1_pb`: Match 1 + Powerball ($4)
- `match_0_pb`: Powerball only ($4)

### Example CSV Row
```
date,jackpot,cash_value,match_5_pb_winners,match_5_pb_prize,match_5_winners,match_5_prize,...
2025-10-01,175 Million,81.2 Million,0,Jackpot,1,1000000,15,50000,256,100,...
```

## Notes

- **PowerBall Drawing Schedule:**
  - Before August 23, 2021: Wednesday and Saturday only
  - From August 23, 2021 onwards: Monday, Wednesday, and Saturday
- The scraper automatically filters to only scrape on drawing dates based on the correct historical schedule
- Prize amounts may vary over time, but match levels remain consistent
- First PowerBall drawing: April 22, 1992
- Historical data availability depends on powerball.com's archive
- The script respects the server and includes appropriate user-agent headers
