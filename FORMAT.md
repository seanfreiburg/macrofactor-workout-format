# MacroFactor Workouts program file format (.xlsx)

**Status: draft.** This describes the spreadsheet MacroFactor Workouts uses for
**Export Program** and **Import From File**. Every rule is tagged:

- **[confirmed]**: seen in real app exports, or in a file the app imported without errors
- **[tested]**: an import test in [tests/RESULTS.md](tests/RESULTS.md) settled it
- **[candidate]**: a value found in the app's strings but not yet tested

**Tested against:** MacroFactor Workouts **1.4.5** (Android, package `com.sbs.train`, version code 160), checked 2026-11-20. Run `python -m mfxlsx validate FILE.xlsx` to check a file against these rules.

## File

- One `.xlsx` workbook with one sheet named `Training Programs`. **[confirmed]**
- All cells use the General format. Numbers (RIR) are numeric cells; everything else is text. **[confirmed]**
- MacroFactor's import help warns that the format is sensitive to changes. Start from an export, or from the writer in this repo.

## Layout

```
Row 1      Program: <name> | Cycles: <n> | Deload: <when> | Color: <color> | Icon: <icon>
Row 2      Block 1
Row 3      Cycle 1 | Exercise | Skipped | Notes | Set 1 Type | Set 1 Rep Range | Set 1 RIR | Set 1 Rest | Set 2 Type | ...
Row 4..    <Day> @ <Gym> | <exercise> | No | <note> | Standard Set | 8 - 12 | 2 | <rest> | ...
           (blank)       | <exercise> | ...
           Rest
           ...
           Cycle 2 | Exercise | ...   (header row repeats for every cycle)
```

### Row 1: program metadata [confirmed]
Each value goes in its own cell as `Key: value`, starting in column A.

| Cell | Example | Values |
|---|---|---|
| A1 | `Program: Jack Reacher` | Program name (bold in exports) |
| B1 | `Cycles: 6` | Number of cycles. In app terms a cycle is one pass through the days, usually a week. |
| C1 | `Deload: Last Cycle` | `Last Cycle` **[confirmed]**; `First Cycle`, `None` **[candidate]** |
| D1 | `Color: Orange` | `Orange` **[confirmed]**; `Red`, `Yellow`, `Green`, `Teal`, `Blue`, `Purple` **[candidate]** |
| E1 | `Icon: Chess Queen` | `Chess Queen` **[confirmed]**; `Chess King`, `Chess King 2`, `Chess Rook`, `Chess Bishop`, `Chess Bishop 2`, `Chess Knight`, `Chess Pawn` **[candidate]** (the list is longer) |

With `Cycles: 6` and `Deload: Last Cycle`, cycle 6 is the deload. The file lists cycle 6 with normal targets, and the app applies the deload itself. **[confirmed]**

### Blocks
`Block 1` sits alone in column A of row 2. **[confirmed]** Several blocks (`Block 2`, ...) probably work. **[candidate]**

### Cycle header row [confirmed]
Column A holds `Cycle <n>`. Columns B onward hold the headers:
`Exercise`, `Skipped`, `Notes`, then 4 columns per set: `Set <k> Type`, `Set <k> Rep Range`, `Set <k> RIR`, `Set <k> Rest`.
There are as many set groups as the largest set count in the program.

The importer matches set headers with `Set <k> (Type|Rep Range|RIR|Rest|Duration|Distance)`. So `Duration` and `Distance` columns are probably accepted. **[candidate]**

### Days [confirmed]
- A training day starts with `<Day> @ <Gym>` in column A (for example `Monday @ Home Gym`). The cell is merged down over that day's exercise rows and top-aligned.
- `<Gym>` is the name of a gym profile in the app. Whether an unknown gym is accepted is untested.
- A rest day is one row with `Rest` in column A.
- Days appear in order. Exports use weekday names, one row group per day of the week.

### Exercise rows [confirmed]

| Column | Content |
|---|---|
| B Exercise | Exercise name as MacroFactor knows it. Custom exercises use their custom name. See *Exercise names*. |
| C Skipped | `No` (`Yes` untested) |
| D Notes | Free text, or empty |
| Set k Type | `Standard Set` **[confirmed]**; `Drop Set`, `Myo Set`, `Failure Set` **[candidate]** |
| Set k Rep Range | `"<low> - <high>"` with spaces, for example `8 - 12`. A single target like `10` is untested. |
| Set k RIR | Integer |
| Set k Rest | Empty in every export so far. Format untested. |

Unused set columns stay empty. An exercise with fewer sets than the maximum leaves the later groups blank.

### Supersets [confirmed]
Each member of a superset gets ` ∈ SS<n>` appended to its exercise name. That's a space, U+2208 ("element of"), a space, then `SS` and a number:

```
Low Incline Dumbbell Press ∈ SS1
Wide Grip Cable Lat Pulldown ∈ SS1
```

The members are adjacent rows. Exports so far show `SS1` only, so numbering across several supersets is still being tested.

## Exercise names
- Import fails if a name isn't recognized (per MacroFactor's help page). The app's exercise database uses sentence case ("Bent-over cable fly"); exports use Title Case. Matching appears to be case-insensitive.
- **Alternative names are accepted and mapped to the canonical exercise.** An import containing `Reverse Cable Crossover` re-exported as `Bent-Over Cable Fly`. **[confirmed]**
- Custom exercises in the importing account can be used by name. **[confirmed]**

## Other spreadsheet styles
The importer's strings include patterns for `week <n>`, `block <n>`, `sets <a>-<b>: ...`, `topset:` / `back off:`, and `... / week spreadsheet`. So it may also parse coach-style program spreadsheets. **[candidate]**

## Validation rules

`python -m mfxlsx validate FILE.xlsx` runs these checks. An **error** means the app's own exports never do this, the program model can't represent it, or an app string names the rule. A **warning** means not yet confirmed by an import test, or a value outside the known lists. `--strict` treats warnings as errors.

<!-- rules:begin (generated by `python -m mfxlsx rules`) -->
| Code | Severity | Evidence |
|---|---|---|
| `not_xlsx` | error | app string: 'We only support select spreadsheet formats with a .xlsx extension' |
| `sheet_name` | warning | exports use one sheet named 'Training Programs'; other names untested |
| `extra_sheets` | warning | exports have exactly one sheet; extra sheets untested |
| `meta_missing` | error | every export has Program, Cycles, Deload, Color, Icon in row 1 |
| `meta_unknown` | warning | row-1 keys other than the five exported ones are untested |
| `meta_bad_cycles` | error | Cycles must be a positive integer |
| `meta_empty_name` | error | program name is required |
| `value_candidate` | warning | value found in app strings but not yet confirmed by an import |
| `value_unknown` | warning | value not seen in exports or app strings |
| `no_block` | error | exports always start the program with a 'Block 1' row |
| `block_numbering` | warning | blocks are numbered 1, 2, ... in order (multi-block files untested) |
| `no_cycle_header` | error | every cycle starts with a 'Cycle <n>' header row |
| `header_columns` | error | B-D must be Exercise, Skipped, Notes (as exported) |
| `header_set_column` | error | set columns must match the app's header pattern 'Set <k> <Type|Rep Range|RIR|Rest|Duration|Distance>' |
| `header_set_order` | error | set groups are numbered 1..k and each repeats the same columns in the same order |
| `header_set_fields` | warning | exports use Type, Rep Range, RIR, Rest; Duration/Distance are in the app's header pattern but untested |
| `cycle_numbering` | error | a block must list cycles 1..Cycles, in order |
| `cycle_structure` | error | every cycle must repeat the same days and exercises (the app stores one target per cycle for each exercise) |
| `row_unrecognized` | error | row doesn't match any exported row kind |
| `row_blank` | warning | exports contain no blank rows |
| `exercise_outside_day` | error | an exercise row must follow a '<Day> @ <Gym>' cell |
| `day_no_gym` | error | day cells are '<Day> @ <Gym>' |
| `day_not_merged` | warning | exports merge the day cell down over its exercise rows |
| `rest_has_content` | error | rest rows contain only 'Rest' |
| `empty_day` | error | a training day has at least one exercise |
| `exercise_name_empty` | error | exercise name is required |
| `exercise_name_unknown` | warning | name not in the supplied exercise list; the import fails on unknown names |
| `superset_lookalike` | error | superset suffix must be ' ∈ SS<n>' with U+2208 (exports) |
| `superset_single` | warning | a superset normally has 2+ members |
| `superset_split` | error | superset members are adjacent rows (exports) |
| `superset_numbering` | warning | exports number supersets SS1, SS2, ... within a day (only SS1 confirmed) |
| `skipped_value` | error | Skipped is 'No' or 'Yes' |
| `skipped_yes` | warning | 'Yes' untested |
| `no_sets` | warning | exports always have at least one set per exercise |
| `set_gap` | error | set groups are filled from Set 1 with no gaps |
| `set_no_type` | error | a set with values must have a Type |
| `rep_range_format` | warning | exports write ranges as '<low> - <high>' with single spaces |
| `rep_range_invalid` | error | rep range must be '<low> - <high>' or a single number |
| `rep_range_order` | error | app string: 'Reps Max must be higher than Reps Min' |
| `rep_single` | warning | single rep target untested |
| `reps_missing` | warning | exports always give a rep range |
| `rir_invalid` | error | RIR is a whole number >= 0 (numeric cell in exports) |
| `rir_high` | warning | RIR above 10 is unusual |
| `rir_missing` | warning | blank RIR untested |
| `rest_untested` | warning | exports leave Rest empty; value formats untested |
| `duration_distance_untested` | warning | Duration/Distance values untested |
<!-- rules:end -->

## Open questions
Tracked in [tests/RESULTS.md](tests/RESULTS.md).
