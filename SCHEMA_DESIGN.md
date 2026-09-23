# Unified CSV Schema Design

Both scrapers write rows with the same 45 columns, defined once as `CSV_COLUMNS` in
`lottery_common.py`, so PowerBall and MegaMillions data can be concatenated directly.

## Columns

```
lottery,date,white_balls,bonus_ball,multiplier,jackpot,cash_value,jackpot_usd,cash_value_usd,
match_5_bonus_winners,match_5_bonus_prize,match_5_bonus_multiplier_winners,match_5_bonus_multiplier_prize,
match_5_winners,match_5_prize,match_5_multiplier_winners,match_5_multiplier_prize,
match_4_bonus_winners,match_4_bonus_prize,match_4_bonus_multiplier_winners,match_4_bonus_multiplier_prize,
match_4_winners,match_4_prize,match_4_multiplier_winners,match_4_multiplier_prize,
match_3_bonus_winners,match_3_bonus_prize,match_3_bonus_multiplier_winners,match_3_bonus_multiplier_prize,
match_3_winners,match_3_prize,match_3_multiplier_winners,match_3_multiplier_prize,
match_2_bonus_winners,match_2_bonus_prize,match_2_bonus_multiplier_winners,match_2_bonus_multiplier_prize,
match_1_bonus_winners,match_1_bonus_prize,match_1_bonus_multiplier_winners,match_1_bonus_multiplier_prize,
match_0_bonus_winners,match_0_bonus_prize,match_0_bonus_multiplier_winners,match_0_bonus_multiplier_prize
```

### Base columns

| Column | Meaning |
|--------|---------|
| `lottery` | `powerball` or `megamillions` |
| `date` | Drawing date, `YYYY-MM-DD` |
| `white_balls` | The five white balls, sorted, zero-padded, space-separated: `02 07 09 17 58` (blank where the source doesn't publish them: PowerBall's early drawings) |
| `bonus_ball` | Powerball / Mega Ball |
| `multiplier` | Power Play / Megaplier value drawn, e.g. `2` (blank when none was drawn, including MegaMillions since April 2025, where each ticket gets its own multiplier) |
| `jackpot` | Advertised jackpot for display, e.g. `175 Million`, `2.04 Billion` (`N/A` if unknown) |
| `cash_value` | Cash option for display, e.g. `81.2 Million` (`N/A` if unknown, e.g. PowerBall before 1997) |
| `jackpot_usd` | `jackpot` in whole dollars (blank if unknown) |
| `cash_value_usd` | `cash_value` in whole dollars (blank if unknown) |

### Match level columns

Each of the nine match levels has four columns. `match_X` means X white balls matched and
`_bonus` means the Powerball / Mega Ball also matched.

| Suffix | Meaning |
|--------|---------|
| `_winners` | Number of winning plays at this level |
| `_prize` | Prize in whole dollars; `Jackpot` for `match_5_bonus` |
| `_multiplier_winners` | Plays that also won with Power Play / Megaplier (blank when not offered) |
| `_multiplier_prize` | Prize for those plays, given the multiplier drawn (blank when not offered) |

Levels are identified from the source data itself (PowerBall row CSS classes, MegaMillions
tier ball counts), not from row position, because the sites don't list them in a fixed order.
MegaMillions' 2010-2013 prize matrix, for instance, lists match 2 + Mega Ball ($10) before
match 3 ($7).

## Lottery-specific notes

### PowerBall

- Values are as shown in powerball.com's winners table: `_winners` is the "Powerball Winners"
  column and `_multiplier_winners` is the "Power Play Winners" column.
- Power Play columns are blank before Power Play was introduced (2001).
- `match_5_multiplier_prize` is the fixed $2 million Power Play prize for match 5.

### MegaMillions

Two eras, both normalized into the same columns:

| Period | Multiplier | How it's recorded |
|--------|------------|-------------------|
| 2010 - 2025-04-04 | Optional Megaplier add-on | `_winners` is the total including Megaplier plays (as megamillions.com displays it); `_multiplier_winners` is the Megaplier subset; `_multiplier_prize` is the prize for the Megaplier drawn |
| 2025-04-08 onward | Multiplier (2x-10x) built into every ticket | `_winners` is summed across all multipliers; `_prize` is the lowest (2x) payout, since no ticket wins less; multiplier columns are blank |

## History

- Originally each scraper used lottery-specific names (`match_5_pb_*`, `_pp_*`,
  `match_5_mb_*`, `_megaplier_*`). The unified schema added the `lottery` column and uses
  `_bonus` / `_multiplier` for both games.
- `white_balls`, `bonus_ball` and `multiplier` were added, which also makes it possible to
  validate the data against an independent source (`validate_against_ny.py`).
- `jackpot_usd` and `cash_value_usd` were added so amounts can be analyzed numerically
  without parsing the display strings (40 -> 45 columns in total).
