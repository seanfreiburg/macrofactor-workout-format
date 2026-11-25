"""Tests for the reader/validator and writer.

Ground truth, strongest first:
1. Real app exports (examples/): must parse with zero issues, and the writer must
   reproduce them cell for cell.
2. Rules from the app's strings (rep range order, .xlsx only, set header pattern).
3. Import test results (tests/RESULTS.md). When a result comes in, move the value or rule
   in mfxlsx/versions.py / RULES and update the matching case below.

Run: python -m pytest tests/
"""
import copy
import json
import pathlib
import sys

import openpyxl
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from mfxlsx import (APP, RULES, Block, Day, Exercise, ExerciseCycle, Program, Set, from_dict,  # noqa: E402
                    read, read_workbook, to_workbook, write)
from mfxlsx.reader import FORMAT_RULES_BEGIN, FORMAT_RULES_END, rules_markdown  # noqa: E402
import build_pack  # noqa: E402

EXPORTS = sorted((ROOT / "examples").glob("export-*.xlsx"))
FIVE_DAY = ROOT / "examples" / "export-5day-program.xlsx"
SUPERSET = ROOT / "examples" / "export-with-superset.xlsx"


def codes(res, level=None):
    return {i.code for i in res.issues if level is None or i.level == level}


# 1. Real exports ---------------------------------------------------------------------

@pytest.mark.parametrize("path", EXPORTS, ids=lambda p: p.name)
def test_real_export_is_clean(path):
    res = read(path)
    assert res.issues == [], [str(i) for i in res.issues]
    assert res.program is not None


@pytest.mark.parametrize("path", EXPORTS, ids=lambda p: p.name)
def test_writer_reproduces_export_cell_for_cell(path):
    original = openpyxl.load_workbook(path).active
    rebuilt = to_workbook(read(path).program).active
    assert [list(r) for r in rebuilt.iter_rows(values_only=True)] == [list(r) for r in original.iter_rows(values_only=True)]
    assert sorted(map(str, rebuilt.merged_cells.ranges)) == sorted(map(str, original.merged_cells.ranges))
    assert rebuilt.title == original.title
    assert rebuilt["A1"].font.b and rebuilt["A4"].alignment.vertical == "top"


@pytest.mark.parametrize("path", EXPORTS, ids=lambda p: p.name)
def test_json_round_trip(path):
    d = read(path).program.to_dict()
    assert from_dict(json.loads(json.dumps(d))).to_dict() == d


def test_superset_export_parsed():
    p = read(SUPERSET).program
    mon = p.all_blocks()[0].days[0]
    assert [(e.name, e.superset) for e in mon.exercises[:3]] == [
        ("Low Incline Dumbbell Press", 1), ("Wide Grip Cable Lat Pulldown", 1),
        ("Single Arm Behind-The-Back Cable Lateral Raise", None)]


def test_app_version_recorded():
    assert APP["package"] == "com.sbs.train" and APP["version"] == "1.4.5"


# 2. A bunch of valid programs: write -> read -> identical ---------------------------

def _ex(name, **kw):
    return Exercise(name, [Set(reps="8 - 12", rir=2), Set(reps="8 - 12", rir=1)], **kw)


VALID_PROGRAMS = {
    "minimal_one_day": Program("Minimal", 1, days=[Day("Monday", [_ex("Low Incline Dumbbell Press")])]),
    "rir_ramp_per_cycle": Program("Ramp", 6, days=[Day("Monday", [Exercise(
        "Barbell Back Squat", [Set(reps="6 - 10", rir=lambda c: max(2, 4 - c // 2))] * 3)])] + ["Rest"] * 6),
    "rep_range_per_cycle": Program("Reps list", 3, days=[Day("Monday", [Exercise(
        "Cambered Bar Bench Press", [Set(reps=["10 - 12", "8 - 10", "6 - 8"], rir=[3, 2, 1])] * 2)])]),
    "five_sets": Program("Five sets", 2, days=[Day("Monday", [Exercise(
        "Standing Dumbbell Lateral Raise", [Set(reps="12 - 20", rir=1)] * 5), _ex("Cable V-Bar Triceps Pushdown")])]),
    "uneven_set_counts": Program("Uneven", 2, days=[Day("Monday", [
        Exercise("Low Incline Dumbbell Press", [Set(reps="8 - 12", rir=2)] * 4), _ex("Wide Grip Cable Lat Pulldown")])]),
    "supersets_2_and_3": Program("Supersets", 2, days=[Day("Monday", [
        _ex("Low Incline Dumbbell Press", superset=1), _ex("Wide Grip Cable Lat Pulldown", superset=1),
        _ex("Standing Dumbbell Biceps Curl", superset=2), _ex("Cable V-Bar Triceps Pushdown", superset=2),
        _ex("Standing Dumbbell Lateral Raise", superset=2), _ex("Barbell Romanian Deadlift")])] + ["Rest"] * 6),
    "notes_and_skipped_per_cycle": Program("Notes", 3, days=[Day("Monday", [Exercise(
        "Deficit Push-Up", [Set(reps="10 - 20", rir=1)] * 2, notes=["Rings", None, "Rings, slow"],
        skipped=[False, False, True])])]),
    "multiple_gyms": Program("Gyms", 2, gym="Home Gym", days=[
        Day("Monday", [_ex("Low Incline Dumbbell Press")]),
        Day("Tuesday", [_ex("Neutral Grip Cable Row")], gym="Work Gym"), "Rest"]),
    "two_blocks": Program("Two blocks", 2, blocks=[
        Block([Day("Monday", [_ex("Low Incline Dumbbell Press")]), "Rest"]),
        Block([Day("Monday", [_ex("Cambered Bar Bench Press")]), "Rest", "Rest"])]),
    "seven_training_days_unicode": Program("Café – 7 días", 2, days=[
        Day(d, [_ex("Standing Dumbbell Biceps Curl", notes="Ünïcode ✓")]) for d in
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]]),
    "custom_day_names": Program("Named days", 2, days=[Day("Push", [_ex("Cambered Bar Bench Press")]),
                                                       Day("Pull", [_ex("Neutral Grip Cable Row")]), "Rest"]),
    "explicit_cycles": Program("Explicit", 2, days=[Day("Monday", [Exercise("Barbell Romanian Deadlift", cycles=[
        ExerciseCycle([Set(reps="8 - 12", rir=3)] * 2), ExerciseCycle([Set(reps="8 - 12", rir=2)] * 3)])])]),
}


@pytest.mark.parametrize("name", VALID_PROGRAMS)
def test_valid_program_round_trip(name, tmp_path):
    p = VALID_PROGRAMS[name]
    out = tmp_path / f"{name}.xlsx"
    write(p, out)
    res = read(out)
    assert res.errors == [], [str(i) for i in res.errors]
    assert res.program.to_dict() == p.to_dict()


def test_writer_refuses_invalid_program(tmp_path):
    bad = Program("Bad", 1, days=[Day("Monday", [Exercise("Low Incline Dumbbell Press", [Set(reps="12 - 8", rir=1)])])])  # reversed
    with pytest.raises(ValueError, match="rep_range_order"):
        write(bad, tmp_path / "bad.xlsx")


# 3. Import test pack: no errors; warnings flag exactly what each test asks ------------

PACK_EXPECTED_WARNINGS = {
    "T00": set(), "T01": {"drop_set_range"}, "T02": set(), "T03": {"rest_untested"},
    "T04": {"header_set_fields", "duration_distance_untested"}, "T05": {"value_candidate"},
    "T06": {"value_candidate"}, "T07": {"value_candidate"}, "T08": set(), "T09": set(), "T10": {"rep_single"},
    "T11": {"rir_missing", "skipped_yes"}, "T12": set(), "T13": set(),
}


@pytest.mark.parametrize("code,title,program", list(build_pack.tests("Home Gym")), ids=lambda x: x if isinstance(x, str) else "")
def test_pack_file(code, title, program):
    res = read_workbook(to_workbook(program))
    assert res.errors == [], [str(i) for i in res.errors]
    assert codes(res, "warning") == PACK_EXPECTED_WARNINGS[code]


def test_pack_unknown_name_flagged_with_name_list():
    _, _, p = next(t for t in build_pack.tests("Home Gym") if t[0] == "T12")
    res = read_workbook(to_workbook(p), exercise_names=[build_pack.PRESS])
    assert "exercise_name_unknown" in codes(res)


# 4. Broken files: one mutation of a real export per rule ------------------------------

def unmerge(ws, ref):
    ws.unmerge_cells(ref)


def set_cells(**cells):
    def f(wb):
        for ref, v in cells.items():
            wb.active[ref] = v
    return f


BROKEN = [
    # (case id, base export, mutation, expected code)
    ("meta_missing", FIVE_DAY, set_cells(E1=None), "meta_missing"),
    ("meta_bad_cycles", FIVE_DAY, set_cells(B1="Cycles: six"), "meta_bad_cycles"),
    ("meta_empty_name", FIVE_DAY, set_cells(A1="Program: "), "meta_empty_name"),
    ("meta_unknown", FIVE_DAY, set_cells(F1="Author: someone"), "meta_unknown"),
    ("color_unknown", FIVE_DAY, set_cells(D1="Color: Chartreuse"), "value_unknown"),
    ("deload_candidate", FIVE_DAY, set_cells(C1="Deload: First Cycle"), "value_candidate"),
    ("sheet_name", FIVE_DAY, lambda wb: setattr(wb.active, "title", "Sheet1"), "sheet_name"),
    ("extra_sheets", FIVE_DAY, lambda wb: wb.create_sheet("Notes"), "extra_sheets"),
    ("no_block", FIVE_DAY, set_cells(A2=None), "no_block"),
    ("block_numbering", FIVE_DAY, set_cells(A2="Block 2"), "block_numbering"),
    ("no_cycle_header", FIVE_DAY, set_cells(A3="Week 1"), "no_cycle_header"),
    ("header_columns", FIVE_DAY, set_cells(C3="Skip"), "header_columns"),
    ("header_set_column", FIVE_DAY, set_cells(H3="Set 1 Rest Time"), "header_set_column"),
    ("header_set_order", FIVE_DAY, set_cells(F3="Set 1 RIR", G3="Set 1 Rep Range"), "header_set_order"),
    ("cycle_numbering_dup", FIVE_DAY, set_cells(A35="Cycle 1"), "cycle_numbering"),
    ("cycle_structure", FIVE_DAY, set_cells(B36="Seated Cable Fly"), "cycle_structure"),
    ("rest_has_content", FIVE_DAY, set_cells(B33="Walk"), "rest_has_content"),
    ("row_unrecognized", FIVE_DAY, set_cells(A33="Holiday"), "row_unrecognized"),
    ("row_blank", FIVE_DAY, set_cells(A33=None), "row_blank"),
    ("empty_day", FIVE_DAY, set_cells(A33="Saturday @ Home Gym"), "empty_day"),
    ("day_no_gym", FIVE_DAY, set_cells(A4="Monday"), "day_no_gym"),
    ("day_not_merged", FIVE_DAY, lambda wb: unmerge(wb.active, "A4:A10"), "day_not_merged"),
    ("exercise_outside_day", FIVE_DAY, lambda wb: (unmerge(wb.active, "A4:A10"), set_cells(A4=None)(wb)), "exercise_outside_day"),
    ("exercise_name_empty", SUPERSET, set_cells(B4=" ∈ SS1"), "exercise_name_empty"),
    ("superset_lookalike_euro", SUPERSET, set_cells(B4="Low Incline Dumbbell Press € SS1"), "superset_lookalike"),
    ("superset_lookalike_bare", SUPERSET, set_cells(B4="Low Incline Dumbbell Press SS1"), "superset_lookalike"),
    ("superset_single", SUPERSET, set_cells(B5="Wide Grip Cable Lat Pulldown"), "superset_single"),
    ("superset_split", SUPERSET, set_cells(B5="Wide Grip Cable Lat Pulldown",
                                           B6="Single Arm Behind-The-Back Cable Lateral Raise ∈ SS1"), "superset_split"),
    ("superset_numbering", SUPERSET, set_cells(B4="Low Incline Dumbbell Press ∈ SS2",
                                               B5="Wide Grip Cable Lat Pulldown ∈ SS2"), "superset_numbering"),
    ("skipped_value", FIVE_DAY, set_cells(C4="Maybe"), "skipped_value"),
    ("skipped_yes", FIVE_DAY, set_cells(C4="Yes"), "skipped_yes"),
    ("no_sets", FIVE_DAY, set_cells(E4=None, F4=None, G4=None, I4=None, J4=None, K4=None), "no_sets"),
    ("set_gap", FIVE_DAY, set_cells(E4=None, F4=None, G4=None), "set_gap"),
    ("set_no_type", FIVE_DAY, set_cells(E4=None), "set_no_type"),
    ("rep_range_no_spaces", FIVE_DAY, set_cells(F4="10-20"), "rep_range_format"),
    ("rep_range_en_dash", FIVE_DAY, set_cells(F4="10 – 20"), "rep_range_format"),
    ("rep_range_invalid", FIVE_DAY, set_cells(F4="ten to twenty"), "rep_range_invalid"),
    ("rep_range_reversed", FIVE_DAY, set_cells(F4="20 - 10"), "rep_range_order"),
    ("rep_open_on_standard_set", FIVE_DAY, set_cells(F4="10+"), "rep_open_untested"),
    ("rir_pair_on_standard_set", FIVE_DAY, set_cells(G4="1 (0)"), "rir_pair_untested"),
    ("rir_pair_malformed", FIVE_DAY, set_cells(G4="1 (x)"), "rir_invalid"),
    ("drop_syntax_on_standard_set", FIVE_DAY, set_cells(F4="8 - 8 (4 - 4)"), "drop_syntax"),
    ("drop_count_mismatch", FIVE_DAY, set_cells(E4="Drop Set", F4="6 - 6 (4 - 4)", G4="1 (2) (3)"), "drop_count_mismatch"),
    ("drop_multi", FIVE_DAY, set_cells(E4="Drop Set", F4="6 - 6 (4 - 4) (2 - 2)", G4="1 (2) (3)"), "drop_multi_untested"),
    ("drop_reversed", FIVE_DAY, set_cells(E4="Drop Set", F4="6 - 6 (4 - 2)", G4="1 (2)"), "rep_range_order"),
    ("rep_range_reversed_loose", FIVE_DAY, set_cells(F4="20-10"), "rep_range_order"),
    ("rep_single", FIVE_DAY, set_cells(F4="10"), "rep_single"),
    ("reps_missing", FIVE_DAY, set_cells(F4=None), "reps_missing"),
    ("rir_text", FIVE_DAY, set_cells(G4="two"), "rir_invalid"),
    ("rir_negative", FIVE_DAY, set_cells(G4=-1), "rir_invalid"),
    ("rir_fraction", FIVE_DAY, set_cells(G4=1.5), "rir_invalid"),
    ("rir_high", FIVE_DAY, set_cells(G4=12), "rir_high"),
    ("rir_missing", FIVE_DAY, set_cells(G4=None), "rir_missing"),
    ("rest_text", FIVE_DAY, set_cells(H4="1:30"), "rest_untested"),
    ("rest_negative", FIVE_DAY, set_cells(H4=-30), "rest_invalid"),
    ("rest_fraction", FIVE_DAY, set_cells(H4=90.5), "rest_invalid"),
    ("values_past_last_set", FIVE_DAY, set_cells(M4="x"), "row_unrecognized"),
]


@pytest.mark.parametrize("case,base,mutate,expected", BROKEN, ids=[b[0] for b in BROKEN])
def test_broken_file(case, base, mutate, expected):
    wb = openpyxl.load_workbook(base)
    mutate(wb)
    res = read_workbook(wb)
    assert expected in codes(res), [str(i) for i in res.issues]
    if RULES[expected][0] == "error":
        assert res.program is None


def test_not_xlsx(tmp_path):
    f = tmp_path / "program.csv"
    f.write_text("x")
    assert codes(read(f)) == {"not_xlsx"}


def test_exercise_name_list(tmp_path):
    res = read(FIVE_DAY, exercise_names=["Low Incline Dumbbell Press"])
    assert "exercise_name_unknown" in codes(res) and res.errors == []


def test_every_rule_is_exercised():
    covered = {b[3] for b in BROKEN} | {"not_xlsx", "exercise_name_unknown", "header_set_fields",
                                        "duration_distance_untested"}
    covered |= set().union(*PACK_EXPECTED_WARNINGS.values())
    assert set(RULES) - covered == set()


def test_format_md_rules_table_in_sync():
    text = (ROOT / "FORMAT.md").read_text(encoding="utf-8")
    start, end = text.index(FORMAT_RULES_BEGIN) + len(FORMAT_RULES_BEGIN), text.index(FORMAT_RULES_END)
    assert text[start:end].strip() == rules_markdown().strip(), "run: python -m mfxlsx rules > update FORMAT.md"


def test_open_ended_and_equal_ranges_are_valid(tmp_path):
    """Real 6-day export: Failure Sets written as '6+', blank-max Standard Sets as '6 - 6'."""
    from mfxlsx import Day, Exercise, Program, Set, write
    p = Program("Open", 2, days=[Day("Monday", [Exercise("Lever-Arm Machine Belt Squat", [
        Set("Standard Set", "6 - 12", 0), Set("Failure Set", "6+", 0), Set("Standard Set", "6 - 6", 0)])])])
    write(p, tmp_path / "o.xlsx")
    res = read(tmp_path / "o.xlsx")
    assert res.issues == []
    assert [s.reps for s in res.program.all_blocks()[0].days[0].exercises[0].cycle(1).sets] == ["6 - 12", "6+", "6 - 6"]


def test_fixtures_carry_no_author_metadata():
    """App exports put the account holder's name in docProps/core.xml; fixtures must not."""
    import zipfile
    for f in sorted((ROOT / "examples").rglob("*.xlsx")):
        core = zipfile.ZipFile(f).read("docProps/core.xml").decode()
        assert "<dc:creator>" not in core and "<cp:lastModifiedBy>" not in core, f.name
