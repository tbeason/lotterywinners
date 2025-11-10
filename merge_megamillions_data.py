"""
Merge missing MegaMillions data (2010-2014) with existing data (2014-present).

Creates a complete historical dataset sorted by date.
"""

import csv
from datetime import datetime

def merge_data():
    """Merge the missing data with existing data."""

    print("Merging MegaMillions Historical Data")
    print("=" * 50)

    # Read both CSV files
    missing_file = 'megamillions_missing_2010_2014.csv'
    existing_file = 'megamillions_all_history.csv'
    output_file = 'megamillions_complete_history.csv'

    all_rows = []

    # Read missing data (2010-2014)
    print(f"Reading {missing_file}...")
    try:
        with open(missing_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            missing_rows = list(reader)
            print(f"  Found {len(missing_rows)} rows (2010-2014)")
            all_rows.extend(missing_rows)
    except FileNotFoundError:
        print(f"  ERROR: {missing_file} not found!")
        return

    # Read existing data (2014-present)
    print(f"Reading {existing_file}...")
    with open(existing_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        existing_rows = list(reader)
        print(f"  Found {len(existing_rows)} rows (2014-present)")
        all_rows.extend(existing_rows)

    # Sort by date
    print("Sorting by date...")
    all_rows.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d'))

    # Write merged data
    print(f"Writing {len(all_rows)} total rows to {output_file}...")

    if all_rows:
        fieldnames = all_rows[0].keys()
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)

    print()
    print("=" * 50)
    print(f"Complete! {len(all_rows)} total drawings")
    print(f"Date range: {all_rows[0]['date']} to {all_rows[-1]['date']}")
    print(f"Output: {output_file}")

if __name__ == '__main__':
    merge_data()
