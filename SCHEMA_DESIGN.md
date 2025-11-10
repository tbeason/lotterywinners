# Unified CSV Schema Design

## Current Schemas

### PowerBall
- Columns: `date`, `jackpot`, `cash_value`
- Match levels with powerball: `match_5_pb`, `match_4_pb`, `match_3_pb`, `match_2_pb`, `match_1_pb`, `match_0_pb`
- Match levels without powerball: `match_5`, `match_4`, `match_3`
- Multiplier suffix: `_pp` (Power Play)
- Example: `match_5_pb_winners`, `match_5_pb_prize`, `match_5_pb_pp_winners`, `match_5_pb_pp_prize`

### MegaMillions
- Columns: `date`, `jackpot`, `cash_value`
- Match levels with megaball: `match_5_mb`, `match_4_mb`, `match_3_mb`, `match_2_mb`, `match_1_mb`, `match_0_mb`
- Match levels without megaball: `match_5`, `match_4`, `match_3`
- Multiplier suffix: `_megaplier`
- Example: `match_5_mb_winners`, `match_5_mb_prize`, `match_5_mb_megaplier_winners`, `match_5_mb_megaplier_prize`

## Unified Schema

### Key Changes
1. **Add lottery identifier column**: `lottery` (values: "powerball" or "megamillions")
2. **Standardize bonus ball naming**: `_bonus` instead of `_pb` or `_mb`
3. **Standardize multiplier naming**: `_multiplier` instead of `_pp` or `_megaplier`

### New Column Structure
```
lottery,date,jackpot,cash_value,
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

### Benefits
1. **Single schema for both lotteries**: Easier to combine and analyze data
2. **Clear lottery identification**: `lottery` column makes it obvious which game
3. **Consistent naming**: Same column names work for both games
4. **Future-proof**: Easy to add more lotteries with same schema

### Match Level Mapping

#### PowerBall → Unified
- `match_5_pb_*` → `match_5_bonus_*`
- `match_5_pp_*` → `match_5_multiplier_*`
- `match_4_pb_*` → `match_4_bonus_*`
- etc.

#### MegaMillions → Unified
- `match_5_mb_*` → `match_5_bonus_*`
- `match_5_megaplier_*` → `match_5_multiplier_*`
- `match_4_mb_*` → `match_4_bonus_*`
- etc.

## Total Columns
- **Old**: 39 columns (3 base + 36 match level columns)
- **New**: 40 columns (4 base [+lottery] + 36 match level columns)
