# MacroFactor Workouts program file format

An unofficial spec, validator and exporter for the `.xlsx` files that [MacroFactor Workouts](https://macrofactor.com/workouts/) uses for **Export Program** and **Import From File**. Write a training program as JSON or Python, check it, and import it instead of building it tap by tap.

| | |
|---|---|
| [FORMAT.md](FORMAT.md) | The format, plus every validation rule and its evidence |
| [mfxlsx/](mfxlsx/) | Parser/validator, writer, and command line |
| [examples/](examples/) | Real app exports (gym name replaced) and a JSON program |
| [tests/](tests/) | Automated tests, an import test pack for the real app, and results |

## Tested against

| App | Version | Platform | Package | Checked |
|---|---|---|---|---|
| MacroFactor Workouts | **1.4.5** (version code 160) | Android | `com.sbs.train` | 2026-11-20 |

The version also lives in [`mfxlsx/versions.py`](mfxlsx/versions.py), and `validate` prints it with every report. Results from other versions and from iOS are welcome; see *Contributing*.

## How the rules were derived

This is an independent implementation, not the app's code. Each rule comes from one of:
1. **Real exports:** the parser must read them with zero issues, and the writer must reproduce them cell for cell (enforced by the tests).
2. **Strings in the app:** for example the set-column header pattern, "Reps Max must be higher than Reps Min", and the `.xlsx`-only message.
3. **Import tests in the real app:** the pack in `tests/`, with results in [tests/RESULTS.md](tests/RESULTS.md).

A rule backed by 1 or 2 is an **error**. Anything not yet confirmed by an import is a **warning**.

## Usage

```bash
pip install -r requirements.txt

python -m mfxlsx validate program.xlsx                 # errors and warnings, exit 1 if invalid
python -m mfxlsx validate program.xlsx --strict        # warnings count as errors
python -m mfxlsx validate program.xlsx --known         # also check names against names seen in real exports
python -m mfxlsx validate program.xlsx --names my-exercises.txt   # ...or against your own list
python -m mfxlsx dump program.xlsx > program.json      # program as JSON (per-cycle targets)
python -m mfxlsx build program.json -o program.xlsx    # JSON to importable file (refuses invalid input)
python -m mfxlsx compare sent.xlsx reexport.xlsx      # what the app changed when it imported your file
python -m mfxlsx rules                                 # the rule table
```

JSON input can be the full form `dump` produces, or the short form in [examples/programs/push-pull.json](examples/programs/push-pull.json). In the short form, any set field can be a list with one value per cycle, for example `"rir": [3, 2, 1, 1]`.

From Python:

```python
from mfxlsx import Day, Exercise, Program, Set, read, write

press = Exercise("Low Incline Dumbbell Press", [Set(reps="8 - 12", rir=[3, 2, 1, 1])] * 2, superset=1)
pull = Exercise("Wide Grip Cable Lat Pulldown", [Set(reps="8 - 12", rir=2)] * 2, superset=1, notes="Neutral grip")
write(Program("Example", cycles=4, gym="Home Gym", days=[Day("Monday", [press, pull])] + ["Rest"] * 6), "example.xlsx")

result = read("example.xlsx")
print(result.ok(), [str(i) for i in result.issues])
```

Then in the app: **+ → New Program** (not New Workout) **→ Import From File**.
- Use your own gym profile's name.
- Exercise names must exist in MacroFactor's library or in your custom exercises. Alternative names are mapped to MacroFactor's own.

## Tests

```bash
pip install pytest && python -m pytest tests/
```

The suite covers:
- **Real exports:** both parse with zero issues, the writer reproduces them cell for cell, and they survive a JSON round trip.
- **Valid programs:** 12 varied programs (effort ramps, 5 sets, uneven set counts, 2- and 3-exercise supersets, per-cycle notes, multiple gyms, two blocks, Unicode) that must survive a write-and-read round trip unchanged.
- **The 14-file import test pack:** no errors, and exactly the warnings each test is meant to probe.
- **Broken files:** 49 mutations of real exports, one per rule.
- **Real round trip:** `compare` on a file the app imported and re-exported finds exactly the known changes.
- **Coverage:** a check that every rule is exercised and that FORMAT.md's rule table is in sync.

When the real app contradicts a rule, update [`mfxlsx/versions.py`](mfxlsx/versions.py) or `RULES` in [`mfxlsx/reader.py`](mfxlsx/reader.py), along with the matching test case and `tests/RESULTS.md`.

## Contributing
Run the pack against your app version (`python tests/build_pack.py --gym "<your gym>"`). For each file that imports, re-export it and run `compare`. Add the results to `tests/RESULTS.md` with the app version and platform, and any new names or aliases to `mfxlsx/data/`.

Not affiliated with or endorsed by MacroFactor or Stronger By Science.

## License
MIT
