"""
PowerBall Historical Data Scraper

Scrapes PowerBall drawing results from powerball.com including:
- Date of drawing
- Estimated jackpot amount
- Number of winners at each prize level
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import csv
import re
from typing import Dict, List, Optional


class PowerBallScraper:
    """Scraper for PowerBall drawing results."""

    BASE_URL = "https://www.powerball.com/draw-result"
    DRAWING_DAYS = [0, 2, 5]  # Monday=0, Wednesday=2, Saturday=5

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_drawing_data(self, date: str) -> Optional[Dict]:
        """
        Fetch drawing data for a specific date.

        Args:
            date: Date string in format 'YYYY-MM-DD'

        Returns:
            Dictionary containing drawing data or None if request fails
        """
        url = f"{self.BASE_URL}?gc=powerball&date={date}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract data
            data = {
                'date': date,
                'jackpot': self._extract_jackpot(soup),
                'cash_value': self._extract_cash_value(soup),
                'prize_levels': self._extract_prize_levels(soup)
            }

            return data

        except requests.RequestException as e:
            print(f"Error fetching data for {date}: {e}")
            return None

    def _extract_jackpot(self, soup: BeautifulSoup) -> str:
        """Extract estimated jackpot amount."""
        # Look for jackpot text patterns
        jackpot_patterns = [
            re.compile(r'Estimated Jackpot:\s*\$?([\d,.]+ Million)', re.IGNORECASE),
            re.compile(r'\$?([\d,.]+ Million)', re.IGNORECASE)
        ]

        text = soup.get_text()
        for pattern in jackpot_patterns:
            match = pattern.search(text)
            if match:
                return match.group(1).strip()

        return "N/A"

    def _extract_cash_value(self, soup: BeautifulSoup) -> str:
        """Extract cash alternative value."""
        cash_patterns = [
            re.compile(r'Cash[^:]*:\s*\$?([\d,.]+ Million)', re.IGNORECASE),
            re.compile(r'cash alternative[^:]*:\s*\$?([\d,.]+ Million)', re.IGNORECASE)
        ]

        text = soup.get_text()
        for pattern in cash_patterns:
            match = pattern.search(text)
            if match:
                return match.group(1).strip()

        return "N/A"

    def _extract_prize_levels(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract number of winners at each prize level."""
        prize_data = []

        # PowerBall match levels in order (as they appear in the table)
        match_levels = [
            'Match 5 + PB',     # Row 0: Grand Prize / Jackpot
            'Match 5',          # Row 1: $1 Million
            'Match 4 + PB',     # Row 2: $50,000
            'Match 4',          # Row 3: $100
            'Match 3 + PB',     # Row 4: $100
            'Match 3',          # Row 5: $7
            'Match 2 + PB',     # Row 6: $7
            'Match 1 + PB',     # Row 7: $4
            'Match 0 + PB',     # Row 8: $4 (Powerball only)
        ]

        # Look for the winners table (class contains 'winners-table')
        table = soup.find('table', class_=re.compile(r'winners-table', re.IGNORECASE))

        if table:
            rows = table.find_all('tr')

            # Skip header row (first row)
            data_rows = rows[1:]

            for idx, row in enumerate(data_rows):
                cells = row.find_all(['td', 'th'])

                if len(cells) >= 2 and idx < len(match_levels):
                    # Table structure:
                    # [0] Match level (often empty), [1] Powerball Winners, [2] Powerball Prize,
                    # [3] Power Play Winners (ignore), [4] Power Play Prize (ignore)

                    match_level = match_levels[idx]
                    pb_winners = cells[1].get_text(strip=True)
                    pb_prize = cells[2].get_text(strip=True) if len(cells) > 2 else ""

                    # Extract regular Powerball data (ignore Power Play)
                    if pb_winners and pb_winners.replace(',', '').isdigit():
                        pb_winners_num = pb_winners.replace(',', '')

                        # Extract prize amount
                        pb_prize_amount = "Jackpot"
                        if '$' in pb_prize:
                            prize_match = re.search(r'\$?([\d,]+)', pb_prize)
                            if prize_match:
                                pb_prize_amount = prize_match.group(1).replace(',', '')
                        elif 'grand' in pb_prize.lower() or 'jackpot' in pb_prize.lower():
                            pb_prize_amount = "Jackpot"

                        prize_data.append({
                            'match_level': match_level,
                            'winners': pb_winners_num,
                            'prize_amount': pb_prize_amount
                        })

        return prize_data

    def get_drawing_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        Generate list of PowerBall drawing dates between start and end dates.

        Schedule history:
        - Before 2021-08-23: Wednesday and Saturday only
        - From 2021-08-23 onwards: Monday, Wednesday, and Saturday

        Args:
            start_date: Start date in format 'YYYY-MM-DD'
            end_date: End date in format 'YYYY-MM-DD'

        Returns:
            List of date strings in format 'YYYY-MM-DD'
        """
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        # Date when Monday drawings started
        monday_start = datetime.strptime('2021-08-23', '%Y-%m-%d')

        dates = []
        current = start

        while current <= end:
            # Determine which days are drawing days based on the date
            if current < monday_start:
                # Before 2021-08-23: Wednesday (2) and Saturday (5) only
                drawing_days = [2, 5]
            else:
                # From 2021-08-23 onwards: Monday (0), Wednesday (2), Saturday (5)
                drawing_days = [0, 2, 5]

            if current.weekday() in drawing_days:
                dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)

        return dates

    def scrape_historical_data(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Scrape PowerBall data for a date range.

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

        print(f"\nCompleted! Retrieved {len(results)} drawings.")
        return results

    def save_to_csv(self, data: List[Dict], filename: str = 'powerball_data.csv'):
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
                'date': drawing['date'],
                'jackpot': drawing['jackpot'],
                'cash_value': drawing['cash_value']
            }

            # Add each match level's winner count as a separate column
            for prize in drawing.get('prize_levels', []):
                # Convert match level to column name (e.g., "Match 5 + PB" -> "match_5_pb_winners")
                col_name = prize['match_level'].lower().replace(' ', '_').replace('+', '').replace('_pb_', '_pb_')
                col_name = col_name.replace('__', '_') + '_winners'

                # Also add prize amount column
                prize_col_name = col_name.replace('_winners', '_prize')

                row[col_name] = prize['winners']
                row[prize_col_name] = prize['prize_amount']

            rows.append(row)

        # Write to CSV
        if rows:
            # Create fieldnames with all possible columns
            fieldnames = ['date', 'jackpot', 'cash_value']

            # Add match level columns in order
            match_columns = [
                'match_5_pb_winners', 'match_5_pb_prize',
                'match_5_winners', 'match_5_prize',
                'match_4_pb_winners', 'match_4_pb_prize',
                'match_4_winners', 'match_4_prize',
                'match_3_pb_winners', 'match_3_pb_prize',
                'match_3_winners', 'match_3_prize',
                'match_2_pb_winners', 'match_2_pb_prize',
                'match_1_pb_winners', 'match_1_pb_prize',
                'match_0_pb_winners', 'match_0_pb_prize'
            ]

            fieldnames.extend(match_columns)

            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(rows)

            print(f"Data saved to {filename}")


def main():
    """Example usage."""
    scraper = PowerBallScraper()

    # Example: Get single drawing
    print("Fetching single drawing (2025-11-05)...")
    single_result = scraper.get_drawing_data('2025-11-05')
    if single_result:
        print(f"Jackpot: {single_result['jackpot']}")
        print(f"Cash Value: {single_result['cash_value']}")
        print(f"Prize Levels: {len(single_result['prize_levels'])}")

    # Example: Get historical data
    print("\nFetching historical data...")
    historical_data = scraper.scrape_historical_data('2025-10-01', '2025-11-05')

    # Save to CSV
    scraper.save_to_csv(historical_data, 'powerball_historical.csv')


if __name__ == '__main__':
    main()
