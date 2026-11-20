# Static string scan: MacroFactor Workouts (com.sbs.train) 1.4.5, arm64 (2026-11-20)

Source: an XAPK of the Play Store build (signature not verified).
Method: `strings` on the Flutter AOT snapshot `lib/arm64-v8a/libapp.so`. Nothing was executed.
These are CANDIDATES. A value counts as confirmed only after a test import or export in the app.

## Confirmed by real exports (2 files, 2026-11-20)
- Sheet "Training Programs". Row 1: `Program: <name>`, `Cycles: <n>`, `Deload: Last Cycle`, `Color: <c>`, `Icon: <i>`.
- `Block 1`, then per cycle a header row: `Cycle <n>` | Exercise | Skipped | Notes | Set k Type | Set k Rep Range | Set k RIR | Set k Rest ...
- Day label `<Weekday> @ <Gym>` in column A, merged down the day's exercise rows; `Rest` rows for rest days.
- Rep range written as `"8 - 12"`, RIR as an integer, Skipped `No`, set type `Standard Set`.
- Superset: name suffix ` ∈ SS<n>` (U+2208) on every member.
- Import maps alternate exercise names to the canonical one (Reverse Cable Crossover -> Bent-Over Cable Fly); export uses Title Case.

## From the binary (unconfirmed)
- Set-column header regex: `^Set\s+(\d+)\s+(Type|Rep Range|RIR|Rest|Duration|Distance)$` -> per-set columns may also include Duration and Distance.
- Set types seen: Standard Set, Drop Set, Myo Set, Failure Set (also "Warm-Up"/"Warm Up" strings, unclear if a set type).
- Deload values seen: Last Cycle, First Cycle, None (useDeload flag exists).
- Colors seen: Red, Orange, Yellow, Green, Teal, Blue, Purple (list may be incomplete).
- Icons seen: Chess King, Chess King 2, Chess Queen, Chess Rook, Chess Bishop, Chess Bishop 2, Chess Knight, Chess Pawn (more likely).
- `Block ` prefix -> multiple blocks probably supported (`Block 2`...).
- The importer also has regexes for other spreadsheet styles: `^\s*week\s*(\d+)`, `^block\s+\d+`, `^sets? \d+(?:-\d+)?:\s*(.+)$`, `^(topset|back off)\s*:\s*`, `\s*/\s*week spreadsheet$` -> may parse third-party program sheets (e.g. coach spreadsheets), not just its own export format.
- `SS0` string exists -> superset numbering may be 0-based internally; exports show SS1.

## Next: test imports to confirm
1. Set types: one exercise each with Drop Set / Myo Set / Failure Set.
2. Rest column values: `90`, `1:30`, `90s`, `2 min`.
3. Duration / Distance columns.
4. Deload: First Cycle, None.
5. Colors and icons from the lists above.
6. Two blocks.
7. Supersets: SS1+SS2 on one day, a 3-exercise superset, numbering restarting per day.
8. Unknown exercise name (expect failure), 3+ sets, single rep target ("10").
