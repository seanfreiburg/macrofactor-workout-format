# MacroFactor Workouts program file format

An unofficial spec and Python writer for the `.xlsx` files that [MacroFactor Workouts](https://macrofactor.com/workouts/) uses for **Export Program** and **Import From File**. Write a training program in code or by hand, and import it instead of building it tap by tap.

- [FORMAT.md](FORMAT.md): the format (draft; every rule is marked confirmed, tested or candidate)
- [mfxlsx/](mfxlsx/): a small writer (`pip install openpyxl`)
- [examples/](examples/): real app exports with the gym name replaced
- [tests/](tests/): an import test pack and its results

Not affiliated with or endorsed by MacroFactor or Stronger By Science. The format was worked out from the app's own exports, import tests, and strings in the app.

## Quick start

```python
from mfxlsx import Day, Exercise, Program, Set, write

press = Exercise("Low Incline Dumbbell Press", [Set(reps="8 - 12", rir=2)] * 2, superset=1)
pull = Exercise("Wide Grip Cable Lat Pulldown", [Set(reps="8 - 12", rir=2)] * 2, superset=1, notes="Neutral grip")
monday = Day("Monday", [press, pull])
write(Program("Example", cycles=4, gym="Home Gym", days=[monday] + ["Rest"] * 6), "example.xlsx")
```

Then in the app: **+ → New Program** (not New Workout) **→ Import From File**. Use your own gym profile's name. Exercise names must exist in MacroFactor's library or in your custom exercises.

## Contributing
Results from other app versions, iOS, or new tests are welcome. Add a row to `tests/RESULTS.md` with the app version and what you saw.

## License
MIT
