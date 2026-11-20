"""Build the import test pack: one small program per format question.

Each file is the baseline (T00) with one thing changed. Import each in MacroFactor
(+ > New Program > Import From File) and record pass/fail and what the app shows in
tests/RESULTS.md. Delete the test programs afterwards.

Run: python tests/build_pack.py --gym "<your gym profile name>" --out <dir>
Use your real gym name: T13 is the only test meant to use an unknown gym.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mfxlsx import Block, Day, Exercise, Program, Set, write  # noqa: E402

# Names confirmed by real MacroFactor exports.
PRESS = "Low Incline Dumbbell Press"
PULL = "Wide Grip Cable Lat Pulldown"
CURL = "Standing Dumbbell Biceps Curl"
PUSHDOWN = "Cable V-Bar Triceps Pushdown"
LATERAL = "Standing Dumbbell Lateral Raise"
REST6 = ["Rest"] * 6


def std(n=2, reps="8 - 12", rir=2, **kw):
    return [Set(reps=reps, rir=rir, **kw) for _ in range(n)]


def baseline_day(**kw):
    return Day("Monday", [Exercise(PRESS, std()), Exercise(PULL, std())], **kw)


def tests(gym):
    def prog(code, title, days=None, **kw):
        return code, title, Program(f"{code} {title}", cycles=2, days=days or [baseline_day()] + REST6, gym=gym, **kw)

    yield prog("T00", "Baseline")
    yield prog("T01", "Set types", days=[Day("Monday", [
        Exercise(PRESS, [Set("Standard Set", "8 - 12", 2), Set("Drop Set", "8 - 12", 0)]),
        Exercise(PULL, [Set("Myo Set", "8 - 12", 1), Set("Failure Set", "8 - 12", 0)]),
        Exercise(CURL, [Set("Warm-Up Set", "10 - 15", 4), Set("Standard Set", "10 - 15", 1)]),
    ])] + REST6)
    yield prog("T02", "Rest as seconds", days=[Day("Monday", [
        Exercise(PRESS, std(rest=90)), Exercise(PULL, std(rest=150))])] + REST6)
    yield prog("T03", "Rest as m-ss", days=[Day("Monday", [
        Exercise(PRESS, std(rest="1:30")), Exercise(PULL, std(rest="2:30"))])] + REST6)
    yield prog("T04", "Duration and Distance columns", days=[Day("Monday", [
        Exercise(PRESS, std(duration=60, distance=100)), Exercise(PULL, std())])] + REST6,
        set_fields=["Type", "Rep Range", "RIR", "Rest", "Duration", "Distance"])
    yield prog("T05", "Deload First Cycle", deload="First Cycle")
    yield prog("T06", "Deload None", deload="None")
    yield prog("T07", "Color Teal Icon Knight", color="Teal", icon="Chess Knight")
    b2 = Day("Monday", [Exercise(CURL, std(reps="10 - 15")), Exercise(PUSHDOWN, std(reps="10 - 15"))], gym=None)
    yield "T08", "Two blocks", Program("T08 Two blocks", cycles=2, gym=gym,
                                       blocks=[Block([baseline_day()] + REST6), Block([b2] + REST6)])
    yield prog("T09", "Supersets", days=[
        Day("Monday", [Exercise(PRESS, std(), superset=1), Exercise(PULL, std(), superset=1),
                       Exercise(CURL, std(), superset=2), Exercise(PUSHDOWN, std(), superset=2),
                       Exercise(LATERAL, std(reps="12 - 20"))]),
        Day("Tuesday", [Exercise(CURL, std(), superset=1), Exercise(PUSHDOWN, std(), superset=1),
                        Exercise(LATERAL, std(reps="12 - 20"), superset=1)]),
    ] + ["Rest"] * 5)
    yield prog("T10", "Four sets and single rep target", days=[Day("Monday", [
        Exercise(PRESS, std(n=4)), Exercise(PULL, std(n=3, reps="10"))])] + REST6)
    yield prog("T11", "Skipped and blank RIR", days=[Day("Monday", [
        Exercise(PRESS, std(rir=None)), Exercise(PULL, std(), skipped=True)])] + REST6)
    yield prog("T12", "Unknown exercise name", days=[Day("Monday", [
        Exercise(PRESS, std()), Exercise("Zzz Not A Real Exercise", std())])] + REST6)
    yield prog("T13", "Unknown gym", days=[baseline_day(gym="Nonexistent Test Gym")] + REST6)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gym", default="Home Gym")
    ap.add_argument("--out", default=str(pathlib.Path(__file__).with_name("pack")))
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for code, title, p in tests(a.gym):
        f = out / f"{code}-{title.lower().replace(' ', '-')}.xlsx"
        write(p, f)
        print(f.name)
