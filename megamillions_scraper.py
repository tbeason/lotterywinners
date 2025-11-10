"""
MegaMillions Historical Data Scraper

Scrapes MegaMillions drawing results from megamillions.com including:
- Date of drawing
- Estimated jackpot amount
- Cash option value
- Number of winners at each prize level
- Megaplier winner counts
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta
import csv
import re
import time
from typing import Dict, List, Optional


class MegaMillionsScraper:
    """Scraper for MegaMillions drawing results using Selenium."""

    BASE_URL = "https://www.megamillions.com/Winning-Numbers/Previous-Drawings/Previous-Drawing-Page.aspx"

    # MegaMillions drawing days: Tuesday=1, Friday=4
    DRAWING_DAYS = [1, 4]

    def __init__(self, headless: bool = True):
        """
        Initialize the scraper.

        Args:
            headless: Run Chrome in headless mode (no visible browser window)
        """
        self.headless = headless
        self.driver = None

    def _init_driver(self):
        """Initialize the Chrome WebDriver."""
        if self.driver is None:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            # Use webdriver-manager to automatically handle ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def _datetime_to_ticks(self, dt: datetime) -> int:
        """
        Convert Python datetime to .NET DateTime ticks.
        .NET ticks are 100-nanosecond intervals since January 1, 0001.
        """
        epoch_offset = 621355968000000000
        unix_timestamp = dt.timestamp()
        return int(unix_timestamp * 10000000 + epoch_offset)

    def get_drawing_data(self, date: str) -> Optional[Dict]:
        """
        Fetch drawing data for a specific date using Selenium.

        Args:
            date: Date string in format 'YYYY-MM-DD'

        Returns:
            Dictionary containing drawing data or None if request fails
        """
        self._init_driver()

        # Convert date to .NET ticks
        dt = datetime.strptime(date, '%Y-%m-%d')
        ticks = self._datetime_to_ticks(dt)
        url = f"{self.BASE_URL}?date={ticks}"

        try:
            self.driver.get(url)

            # Wait for JavaScript to load the data
            # Wait for jackpot element to be populated with text
            WebDriverWait(self.driver, 15).until(
                lambda driver: driver.find_element(By.CLASS_NAME, "js_pastJackpot").text.strip() != ""
            )

            # Small additional wait to ensure all elements are loaded
            time.sleep(1)

            # Extract data
            data = {
                'date': date,
                'jackpot': self._extract_jackpot(),
                'cash_value': self._extract_cash_value(),
                'prize_levels': self._extract_prize_levels()
            }

            return data

        except Exception as e:
            print(f"Error fetching data for {date}: {e}")
            return None

    def _extract_jackpot(self) -> str:
        """Extract estimated jackpot amount."""
        try:
            jackpot_elem = self.driver.find_element(By.CLASS_NAME, "js_pastJackpot")
            return jackpot_elem.text.strip() or "N/A"
        except Exception:
            return "N/A"

    def _extract_cash_value(self) -> str:
        """Extract cash option value."""
        try:
            cash_elem = self.driver.find_element(By.CLASS_NAME, "js_pastCashOpt")
            return cash_elem.text.strip() or "N/A"
        except Exception:
            return "N/A"

    def _extract_prize_levels(self) -> List[Dict]:
        """Extract number of winners at each prize level."""
        prize_data = []

        # MegaMillions match levels in order (as they appear in the table)
        match_levels = [
            'Match 5 + MB',      # Row 0: Jackpot
            'Match 5',           # Row 1: $1 Million
            'Match 4 + MB',      # Row 2: $10,000
            'Match 4',           # Row 3: $500
            'Match 3 + MB',      # Row 4: $200
            'Match 3',           # Row 5: $10
            'Match 2 + MB',      # Row 6: $10
            'Match 1 + MB',      # Row 7: $4
            'Match 0 + MB',      # Row 8: $2 (Megaball only)
        ]

        try:
            # Find the "All Winners" table
            table = self.driver.find_element(By.CLASS_NAME, "tableJackpotWinningNumbersNew")
            rows = table.find_elements(By.TAG_NAME, "tr")

            # Skip header row (first row)
            data_rows = rows[1:]

            for idx, row in enumerate(data_rows):
                if idx >= len(match_levels):
                    break

                cells = row.find_elements(By.TAG_NAME, "td")

                if len(cells) >= 5:
                    # Table structure:
                    # [0] Match level (visual, not text)
                    # [1] Total Winners
                    # [2] Prize
                    # [3] Megaplier Winners
                    # [4] Megaplier Prize

                    match_level = match_levels[idx]

                    # Get text content
                    total_winners = cells[1].text.strip()
                    prize = cells[2].text.strip()
                    megaplier_winners = cells[3].text.strip()
                    megaplier_prize = cells[4].text.strip()

                    # Extract regular MegaMillions data
                    if total_winners and total_winners.replace(',', '').isdigit():
                        total_winners_num = total_winners.replace(',', '')

                        # Extract prize amount
                        prize_amount = "Jackpot"
                        if '$' in prize:
                            prize_match = re.search(r'\$?([\d,]+)', prize)
                            if prize_match:
                                prize_amount = prize_match.group(1).replace(',', '')
                        elif 'jackpot' in prize.lower():
                            prize_amount = "Jackpot"

                        # Extract Megaplier data if available
                        megaplier_winners_num = None
                        megaplier_prize_amount = None
                        if megaplier_winners and megaplier_winners.replace(',', '').isdigit():
                            megaplier_winners_num = megaplier_winners.replace(',', '')

                            if '$' in megaplier_prize:
                                prize_match = re.search(r'\$?([\d,]+)', megaplier_prize)
                                if prize_match:
                                    megaplier_prize_amount = prize_match.group(1).replace(',', '')

                        prize_data.append({
                            'match_level': match_level,
                            'winners': total_winners_num,
                            'prize_amount': prize_amount,
                            'megaplier_winners': megaplier_winners_num,
                            'megaplier_prize': megaplier_prize_amount
                        })

        except Exception as e:
            print(f"Error extracting prize levels: {e}")

        return prize_data

    def get_drawing_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        Generate list of MegaMillions drawing dates between start and end dates.

        MegaMillions draws on Tuesday and Friday.

        Args:
            start_date: Start date in format 'YYYY-MM-DD'
            end_date: End date in format 'YYYY-MM-DD'

        Returns:
            List of date strings in format 'YYYY-MM-DD'
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        dates = []
        current = start

        while current <= end:
            # Tuesday (1) and Friday (4)
            if current.weekday() in self.DRAWING_DAYS:
                dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)

        return dates

    def scrape_historical_data(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Scrape MegaMillions data for a date range.

        Args:
            start_date: Start date in format 'YYYY-MM-DD'
            end_date: End date in format 'YYYY-MM-DD'

        Returns:
            List of drawing data dictionaries
        """
        dates = self.get_drawing_dates(start_date, end_date)
        results = []

        print(f"Scraping {len(dates)} drawings from {start_date} to {end_date}...")

        for i, date in enumerate(dates, 1):
            print(f"Fetching {i}/{len(dates)}: {date}", end='\r')
            data = self.get_drawing_data(date)
            if data:
                results.append(data)

            # Small delay between requests
            time.sleep(0.5)

        print(f"\nCompleted! Retrieved {len(results)} drawings.")
        return results

    def save_to_csv(self, data: List[Dict], filename: str = 'megamillions_data.csv'):
        """
        Save scraped data to CSV file with one row per date.

        Args:
            data: List of drawing data dictionaries
            filename: Output CSV filename
        """
        if not data:
            print("No data to save.")
            return

        # Prepare rows for CSV - one row per date
        rows = []
        for drawing in data:
            row = {
                'lottery': 'megamillions',
                'date': drawing['date'],
                'jackpot': drawing['jackpot'],
                'cash_value': drawing['cash_value']
            }

            # Add each match level's winner count as a separate column
            for prize in drawing.get('prize_levels', []):
                # Convert match level to column name (e.g., "Match 5 + MB" -> "match_5_bonus")
                # Unified schema: use "bonus" instead of "pb" or "mb"
                base_col = prize['match_level'].lower().replace(' ', '_').replace('+', '').replace('_mb_', '_bonus_')
                base_col = base_col.replace('__', '_')

                # Regular columns
                row[base_col + '_winners'] = prize['winners']
                row[base_col + '_prize'] = prize['prize_amount']

                # Multiplier columns (if available) - unified schema uses "multiplier" instead of "megaplier"
                if prize.get('megaplier_winners') is not None:
                    row[base_col + '_multiplier_winners'] = prize['megaplier_winners']
                if prize.get('megaplier_prize') is not None:
                    row[base_col + '_multiplier_prize'] = prize['megaplier_prize']

            rows.append(row)

        # Write to CSV
        if rows:
            # Create fieldnames with all possible columns (unified schema)
            fieldnames = ['lottery', 'date', 'jackpot', 'cash_value']

            # Add match level columns in order (regular + multiplier)
            # Unified schema uses "bonus" and "multiplier" instead of lottery-specific names
            match_columns = [
                'match_5_bonus_winners', 'match_5_bonus_prize', 'match_5_bonus_multiplier_winners', 'match_5_bonus_multiplier_prize',
                'match_5_winners', 'match_5_prize', 'match_5_multiplier_winners', 'match_5_multiplier_prize',
                'match_4_bonus_winners', 'match_4_bonus_prize', 'match_4_bonus_multiplier_winners', 'match_4_bonus_multiplier_prize',
                'match_4_winners', 'match_4_prize', 'match_4_multiplier_winners', 'match_4_multiplier_prize',
                'match_3_bonus_winners', 'match_3_bonus_prize', 'match_3_bonus_multiplier_winners', 'match_3_bonus_multiplier_prize',
                'match_3_winners', 'match_3_prize', 'match_3_multiplier_winners', 'match_3_multiplier_prize',
                'match_2_bonus_winners', 'match_2_bonus_prize', 'match_2_bonus_multiplier_winners', 'match_2_bonus_multiplier_prize',
                'match_1_bonus_winners', 'match_1_bonus_prize', 'match_1_bonus_multiplier_winners', 'match_1_bonus_multiplier_prize',
                'match_0_bonus_winners', 'match_0_bonus_prize', 'match_0_bonus_multiplier_winners', 'match_0_bonus_multiplier_prize'
            ]

            fieldnames.extend(match_columns)

            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(rows)

            print(f"Data saved to {filename}")

    def close(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def main():
    """Example usage."""
    with MegaMillionsScraper(headless=True) as scraper:
        # Example: Get single drawing
        print("Fetching single drawing (2024-11-01)...")
        single_result = scraper.get_drawing_data('2024-11-01')
        if single_result:
            print(f"Jackpot: {single_result['jackpot']}")
            print(f"Cash Value: {single_result['cash_value']}")
            print(f"Prize Levels: {len(single_result['prize_levels'])}")

        # Example: Get historical data
        print("\nFetching historical data...")
        historical_data = scraper.scrape_historical_data('2024-10-01', '2024-11-08')

        # Save to CSV
        scraper.save_to_csv(historical_data, 'megamillions_historical.csv')


if __name__ == '__main__':
    main()
