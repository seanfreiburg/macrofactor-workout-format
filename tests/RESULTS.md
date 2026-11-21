# Import test results

Build the pack: `python tests/build_pack.py --gym "<your gym name>" --out pack/`.
Import each file in MacroFactor Workouts (+ > New Program > Import From File) and record what happens. If it imports, export it again (Program Settings > Export Program) and run `python -m mfxlsx compare <sent>.xlsx <re-export>.xlsx` to see what the app changed. Then delete the test program.

App version: MacroFactor Workouts 1.4.5 (Android, com.sbs.train, version code 160)

| Test | Question | Result | What the app showed |
|---|---|---|---|
| T00 Baseline | Control: 2 cycles, one training day, six rest days | **Pass** (2026-11-20) | Imported. Cycles shown as "Week 1" and "Week 2"; day tabs Monday + Rest ×6; sets "8–12 reps" with RIR badge 2. Cycle counts other than 6 are accepted. Target Muscles showed 1.7 sets/exercise (probably a weekly average including the deload cycle). |
| T01 Set types | Are Drop Set, Myo Set, Failure Set, Warm-Up Set accepted? | | |
| T02 Rest as seconds | Is Rest an integer number of seconds (90, 150)? | | |
| T03 Rest as m:ss | Is Rest accepted as text `1:30`? | | |
| T04 Duration/Distance | Are `Set k Duration` / `Set k Distance` columns accepted? | | |
| T05 Deload First Cycle | Is `Deload: First Cycle` valid? | | |
| T06 Deload None | Is `Deload: None` valid? | | |
| T07 Color/Icon | Are `Color: Teal`, `Icon: Chess Knight` valid? | | |
| T08 Two blocks | Is a second `Block 2` section accepted, and how does it appear? | | |
| T09 Supersets | SS1 and SS2 on one day, a 3-exercise superset, numbering restarting per day | | |
| T10 Sets/reps | 4 sets in one exercise; single rep target `10` | | |
| T11 Skipped/RIR | `Skipped: Yes`; RIR left blank | | |
| T12 Unknown exercise | What error does an unknown name give? (expected to fail) | | |
| T13 Unknown gym | What happens with a gym name that doesn't exist? | | |

## Confirmed round trips

Files we generated, imported in the app, and exported again. `compare` output is kept in `examples/roundtrip/`.

| Date | App | File | Imported | What the app changed (from `compare`) |
|---|---|---|---|---|
| 2026-11-20 | 1.4.5 Android | `examples/roundtrip/full-body-sent.xlsx` (5 days, 6 cycles, 2 sets, notes, 36 exercises) | Yes | Renamed `Reverse Cable Crossover` to `Bent-Over Cable Fly` (alias). Everything else kept. The program-name change and the SS1 superset were edits made in the app before exporting. |
