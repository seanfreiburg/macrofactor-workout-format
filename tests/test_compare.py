"""Tests for compare (sent file vs app re-export) and the bundled exercise names."""
import pathlib
import sys

import openpyxl

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mfxlsx import read, read_workbook  # noqa: E402
from mfxlsx.compare import aliases, compare_files  # noqa: E402
from mfxlsx.names import DATA, known_names, load_aliases, load_names  # noqa: E402

RT = ROOT / "examples" / "roundtrip"
EXPORTS = sorted((ROOT / "examples").glob("export-*.xlsx"))


def test_real_round_trip_differences():
    """The full-body file was imported in the app (1.4.5), lightly edited there, and re-exported.
    Expected: the user's rename and added superset, plus one alias the app applied itself."""
    changes = compare_files(RT / "full-body-sent.xlsx", RT / "full-body-reexport.xlsx")
    summary = sorted((c.field, str(c.sent), str(c.exported)) for c in changes)
    assert summary == sorted([
        ("name", "Full Body 5-Day", "Full Body 5-Day V2"),
        ("superset", "None", "1"),
        ("superset", "None", "1"),
        ("exercise name", "Reverse Cable Crossover", "Bent-Over Cable Fly"),
        ("exercise name", "Reverse Cable Crossover", "Bent-Over Cable Fly"),
        ("exercise name", "Reverse Cable Crossover", "Bent-Over Cable Fly"),
    ])
    assert aliases(changes) == {"Reverse Cable Crossover": "Bent-Over Cable Fly"}


def test_compare_identical():
    for p in EXPORTS:
        assert compare_files(p, p) == []


def test_compare_reports_value_change_with_cycles(tmp_path):
    wb = openpyxl.load_workbook(EXPORTS[0])
    ws = wb.active
    for row in ws.iter_rows():
        if row[1].value == "Low Incline Dumbbell Press":
            row[6].value = 3  # Set 1 RIR, every cycle
    out = tmp_path / "changed.xlsx"
    wb.save(out)
    changes = compare_files(EXPORTS[0], out)
    assert len(changes) == 1 and changes[0].field == "set 1 rir" and changes[0].cycles == [1, 2, 3, 4, 5, 6]


def test_alias_file_matches_round_trip():
    changes = compare_files(RT / "full-body-sent.xlsx", RT / "full-body-reexport.xlsx")
    assert aliases(changes).items() <= load_aliases().items()


def test_bundled_names_cover_every_export():
    names = {n.lower() for n in load_names(DATA / "exercise-names.txt")}
    for p in EXPORTS + [RT / "full-body-reexport.xlsx"]:
        for r in openpyxl.load_workbook(p).active.iter_rows(min_row=3, values_only=True):
            if r[1] and r[1] != "Exercise":
                assert r[1].split(" ∈")[0].lower() in names, r[1]


def test_known_names_accept_real_files_and_flag_others():
    known = known_names()
    for p in EXPORTS + [RT / "full-body-sent.xlsx"]:
        assert read(p, exercise_names=known).issues == []
    wb = openpyxl.load_workbook(EXPORTS[0])
    wb.active["B4"] = "Zzz Not A Real Exercise"
    res = read_workbook(wb, exercise_names=known)
    assert {i.code for i in res.issues} >= {"exercise_name_unknown"}


def test_names_file_ignores_comments():
    names = load_names(DATA / "exercise-names.txt")
    assert all("#" not in n and n == n.strip() and not n.startswith("Cycles:") for n in names)
    assert "Neutral Grip Cable Row" in names
