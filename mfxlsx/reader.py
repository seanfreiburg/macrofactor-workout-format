"""Parse and validate MacroFactor Workouts program files (.xlsx).

This is an independent implementation of the format in FORMAT.md, not the app's code.
Each check has a code, a severity and a source of evidence (see RULES):

- error:   the app's own exports never do this, the program model can't represent it, or
           the app's strings name the rule. Expect the import to fail or go wrong.
- warning: valid in principle but not yet confirmed by an import test, or an unknown value
           from an open-ended list (icons, set types). --strict treats these as errors.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

import openpyxl

from .model import DEFAULT_SET_FIELDS, SET_FIELDS, Block, Day, Exercise, ExerciseCycle, Program, Set
from .versions import CANDIDATE, CONFIRMED

SET_HEADER = re.compile(r"^Set\s+(\d+)\s+(Type|Rep Range|RIR|Rest|Duration|Distance)$")
SUPERSET = re.compile(r"^(.*?) ∈ SS(\d+)$")
LOOKALIKE_SUPERSET = re.compile(r"\s(?:∈|€|ε|e|in|E)\s*SS\s*\d+\s*$|\bSS\d+\s*$")
REP_RANGE = re.compile(r"^(\d+) - (\d+)$")
REP_OPEN = re.compile(r"^(\d+)\+$")  # open-ended: "6+" = at least 6 (exports write this on Failure Sets)
RIR_PAIR = re.compile(r"^(\d+)((?: \(\d+\))+)$")  # drop set: "<main RIR> (<drop RIR>)..."
REP_DROPS = re.compile(r"^(\d+) - (\d+)((?: \(\d+ - \d+\))+)$")  # drop set: "<main> (<drop>)..."
REP_RANGE_LOOSE = re.compile(r"^\s*(\d+)\s*[-–]\s*(\d+)\s*$")
META = re.compile(r"^(Program|Cycles|Deload|Color|Icon):\s?(.*)$")
BLOCK = re.compile(r"^Block (\d+)$")
CYCLE = re.compile(r"^Cycle (\d+)$")

# code -> (severity, evidence)
RULES = {
    "not_xlsx": ("error", "app string: 'We only support select spreadsheet formats with a .xlsx extension'"),
    "sheet_name": ("warning", "exports use one sheet named 'Training Programs'; other names untested"),
    "extra_sheets": ("warning", "exports have exactly one sheet; extra sheets untested"),
    "meta_missing": ("error", "every export has Program, Cycles, Deload, Color, Icon in row 1"),
    "meta_unknown": ("warning", "row-1 keys other than the five exported ones are untested"),
    "meta_bad_cycles": ("error", "Cycles must be a positive integer"),
    "meta_empty_name": ("error", "program name is required"),
    "value_candidate": ("warning", "value found in app strings but not yet confirmed by an import"),
    "value_unknown": ("warning", "value not seen in exports or app strings"),
    "no_block": ("error", "exports always start the program with a 'Block 1' row"),
    "block_numbering": ("warning", "blocks are numbered 1, 2, ... in order (multi-block files untested)"),
    "no_cycle_header": ("error", "every cycle starts with a 'Cycle <n>' header row"),
    "header_columns": ("error", "B-D must be Exercise, Skipped, Notes (as exported)"),
    "header_set_column": ("error", "set columns must match the app's header pattern 'Set <k> <Type|Rep Range|RIR|Rest|Duration|Distance>'"),
    "header_set_order": ("error", "set groups are numbered 1..k and each repeats the same columns in the same order"),
    "header_set_fields": ("warning", "exports use Type, Rep Range, RIR, Rest; Duration/Distance are in the app's header pattern but untested"),
    "cycle_numbering": ("error", "a block must list cycles 1..Cycles, in order"),
    "cycle_structure": ("error", "every cycle must repeat the same days and exercises (the app stores one target per cycle for each exercise)"),
    "row_unrecognized": ("error", "row doesn't match any exported row kind"),
    "row_blank": ("warning", "exports contain no blank rows"),
    "exercise_outside_day": ("error", "an exercise row must follow a '<Day> @ <Gym>' cell"),
    "day_no_gym": ("error", "day cells are '<Day> @ <Gym>'"),
    "day_not_merged": ("warning", "exports merge the day cell down over its exercise rows"),
    "rest_has_content": ("error", "rest rows contain only 'Rest'"),
    "empty_day": ("error", "a training day has at least one exercise"),
    "exercise_name_empty": ("error", "exercise name is required"),
    "exercise_name_unknown": ("warning", "name not in the supplied exercise list; the import fails on unknown names"),
    "superset_lookalike": ("error", "superset suffix must be ' ∈ SS<n>' with U+2208 (exports)"),
    "superset_single": ("warning", "a superset normally has 2+ members"),
    "superset_split": ("error", "superset members are adjacent rows (exports)"),
    "superset_numbering": ("warning", "exports number supersets SS1, SS2, ... within a day (only SS1 confirmed)"),
    "skipped_value": ("error", "Skipped is 'No' or 'Yes'"),
    "skipped_yes": ("warning", "'Yes' untested"),
    "no_sets": ("warning", "exports always have at least one set per exercise"),
    "set_gap": ("error", "set groups are filled from Set 1 with no gaps"),
    "set_no_type": ("error", "a set with values must have a Type"),
    "rep_range_format": ("warning", "exports write ranges as '<low> - <high>' with single spaces"),
    "rep_range_invalid": ("error", "rep range must be '<low> - <high>', '<low>+' or a single number"),
    "rep_range_order": ("error", "reversed range (max below min); app string: 'Reps Max must be higher than Reps Min'"),
    "drop_set_range": ("warning", "the app keeps only the low end of a drop set's range ('8 - 12' became '8 - 8', T01); write 'N - N'"),
    "drop_syntax": ("warning", "'<main> (<drop>)' rep/RIR syntax is exported for Drop Sets (T01 edit); on other set types untested"),
    "drop_count_mismatch": ("warning", "rep range and RIR list different numbers of drops"),
    "drop_multi_untested": ("warning", "more than one drop: the export syntax for several drops is unconfirmed"),
    "rep_open_untested": ("warning", "open-ended '<n>+' range: exports write it on Failure Sets; untested on other set types"),
    "rep_single": ("warning", "single rep target untested"),
    "reps_missing": ("warning", "exports always give a rep range"),
    "rir_invalid": ("error", "RIR is a whole number >= 0, or 'X (Y)' text as exports write for drop sets"),
    "rir_pair_untested": ("warning", "'X (Y)' RIR is exported for drop sets (T01); meaning of Y and use on other set types untested"),
    "rir_high": ("warning", "RIR above 10 is unusual"),
    "rir_missing": ("warning", "blank RIR untested"),
    "rest_invalid": ("error", "Rest is whole seconds >= 0 (T02: 90 and 150 round-trip unchanged)"),
    "rest_untested": ("warning", "Rest given as text (e.g. '1:30'); only whole seconds are confirmed (T02)"),
    "duration_distance_untested": ("warning", "Duration/Distance values untested"),
}


@dataclass
class Issue:
    code: str
    message: str
    row: int | None = None

    @property
    def level(self) -> str:
        return RULES[self.code][0]

    def __str__(self):
        where = f"row {self.row}: " if self.row else ""
        return f"{self.level.upper():7} {where}{self.message} [{self.code}]"


@dataclass
class Result:
    program: Program | None
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self):
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self):
        return [i for i in self.issues if i.level == "warning"]

    def ok(self, strict: bool = False) -> bool:
        return not (self.issues if strict else self.errors)


class _Ctx:
    def __init__(self):
        self.issues: list[Issue] = []

    def add(self, code, msg, row=None):
        self.issues.append(Issue(code, msg, row))


def read(path, exercise_names=None) -> Result:
    if not str(path).lower().endswith(".xlsx"):
        return Result(None, [Issue("not_xlsx", f"{path} is not an .xlsx file")])
    return read_workbook(openpyxl.load_workbook(path), exercise_names)


def _s(v):
    if v is None:
        return None
    if isinstance(v, str):
        return v if v.strip() else None
    return v


def _check_value(ctx, key, value, row):
    if value in CONFIRMED[key]:
        return
    code = "value_candidate" if value in CANDIDATE[key] else "value_unknown"
    ctx.add(code, f"{key} '{value}' is {'a candidate' if code == 'value_candidate' else 'unknown'}", row)


def read_workbook(wb, exercise_names=None) -> Result:
    ctx = _Ctx()
    names = {n.lower() for n in exercise_names} if exercise_names else None
    if wb.sheetnames != ["Training Programs"]:
        if "Training Programs" not in wb.sheetnames:
            ctx.add("sheet_name", f"sheet is {wb.sheetnames[0]!r}, not 'Training Programs'")
        if len(wb.sheetnames) > 1:
            ctx.add("extra_sheets", f"{len(wb.sheetnames)} sheets: {wb.sheetnames}")
    ws = wb["Training Programs"] if "Training Programs" in wb.sheetnames else wb.worksheets[0]
    rows = [[_s(v) for v in r] for r in ws.iter_rows(values_only=True)]
    merged_tops = {(m.min_row, m.max_row) for m in ws.merged_cells.ranges if m.min_col == 1 and m.max_col == 1}

    # Row 1: metadata
    meta = {}
    for v in (rows[0] if rows else []):
        if v is None:
            continue
        m = META.match(str(v))
        if not m:
            ctx.add("meta_unknown", f"unrecognized metadata cell {v!r}", 1)
            continue
        meta[m.group(1)] = m.group(2).strip()
    for k in ("Program", "Cycles", "Deload", "Color", "Icon"):
        if k not in meta:
            ctx.add("meta_missing", f"'{k}:' missing from row 1", 1)
    if meta.get("Program") == "":
        ctx.add("meta_empty_name", "program name is empty", 1)
    try:
        n_cycles = int(meta.get("Cycles", ""))
        if n_cycles < 1:
            raise ValueError
    except ValueError:
        if "Cycles" in meta:
            ctx.add("meta_bad_cycles", f"Cycles {meta['Cycles']!r} is not a positive integer", 1)
        n_cycles = None
    for k in ("Deload", "Color", "Icon"):
        if k in meta:
            _check_value(ctx, k, meta[k], 1)

    # Rows 2+: blocks > cycles > days > exercises
    blocks = []  # [{"name", "row", "cycles": {n: {"row", "fields", "nsets", "days": [...]}}}]
    cur_block = cur_cycle = cur_day = None
    for i, r in enumerate(rows[1:], 2):
        a = r[0] if r else None
        rest = r[1:] if r else []
        if all(v is None for v in r or [None]):
            ctx.add("row_blank", "blank row", i)
            continue
        if isinstance(a, str) and BLOCK.match(a) and all(v is None for v in rest):
            cur_block = {"name": a, "num": int(BLOCK.match(a).group(1)), "row": i, "cycles": {}}
            blocks.append(cur_block)
            cur_cycle = cur_day = None
            continue
        if isinstance(a, str) and CYCLE.match(a):
            if cur_block is None:
                ctx.add("no_block", "cycle before any 'Block <n>' row", i)
                cur_block = {"name": "Block 1", "num": 1, "row": i, "cycles": {}}
                blocks.append(cur_block)
            fields, nsets = _parse_header(ctx, r, i)
            n = int(CYCLE.match(a).group(1))
            cur_cycle = {"num": n, "row": i, "fields": fields, "nsets": nsets, "days": []}
            if n in cur_block["cycles"]:
                ctx.add("cycle_numbering", f"cycle {n} appears twice in {cur_block['name']}", i)
            cur_block["cycles"][n] = cur_cycle
            cur_day = None
            continue
        if cur_cycle is None:
            ctx.add("no_cycle_header" if cur_block else "no_block", f"row before any cycle header: {a or r[1]!r}", i)
            continue
        if a == "Rest":
            if any(v is not None for v in rest):
                ctx.add("rest_has_content", "rest row has other cells filled", i)
            cur_cycle["days"].append("Rest")
            cur_day = None
            continue
        if isinstance(a, str):
            if " @ " not in a:
                ctx.add("day_no_gym" if r[1] is not None else "row_unrecognized",
                        f"{a!r} is not '<Day> @ <Gym>'" if r[1] is not None else f"unrecognized row {a!r}", i)
                if r[1] is None:
                    continue
                name, gym = a, ""
            else:
                name, gym = a.split(" @ ", 1)
            cur_day = {"name": name.strip(), "gym": gym.strip(), "row": i, "exercises": []}
            cur_cycle["days"].append(cur_day)
        elif a is not None:
            ctx.add("row_unrecognized", f"unrecognized value {a!r} in column A", i)
            continue
        if r[1] is None:
            if cur_day is not None and not cur_day["exercises"]:
                ctx.add("empty_day", f"day {cur_day['name']!r} has no exercise", i)
            else:
                ctx.add("row_unrecognized", "row has values but no exercise name", i)
            continue
        if cur_day is None:
            ctx.add("exercise_outside_day", f"exercise {r[1]!r} isn't under a day", i)
            continue
        cur_day["exercises"].append(_parse_exercise(ctx, r, i, cur_cycle, names))

    # Close days: merge check
    for b in blocks:
        for c in b["cycles"].values():
            for d in c["days"]:
                if isinstance(d, dict):
                    if not d["exercises"]:
                        ctx.add("empty_day", f"day {d['name']!r} has no exercise", d["row"])
                    last = d["row"] + len(d["exercises"]) - 1
                    if len(d["exercises"]) > 1 and (d["row"], last) not in merged_tops:
                        ctx.add("day_not_merged", f"day cell {d['name']!r} isn't merged over rows {d['row']}-{last}", d["row"])
                    _check_supersets(ctx, d)

    if not blocks:
        ctx.add("no_block", "no 'Block <n>' row found", 2)
    for bi, b in enumerate(blocks, 1):
        if b["num"] != bi:
            ctx.add("block_numbering", f"{b['name']!r} is block #{bi}", b["row"])
        if not b["cycles"]:
            ctx.add("no_cycle_header", f"{b['name']} has no cycles", b["row"])
        if n_cycles is not None and sorted(b["cycles"]) != list(range(1, n_cycles + 1)):
            ctx.add("cycle_numbering", f"{b['name']} lists cycles {sorted(b['cycles'])}, expected 1..{n_cycles}", b["row"])
        nums = list(b["cycles"])
        if nums != sorted(nums):
            ctx.add("cycle_numbering", f"{b['name']} cycles out of order: {nums}", b["row"])
        _check_cycle_structure(ctx, b)

    program = None if any(i.level == "error" for i in ctx.issues) else _build(meta, n_cycles, blocks)
    return Result(program, ctx.issues)


def _parse_header(ctx, r, i):
    if [r[1] if len(r) > 1 else None, r[2] if len(r) > 2 else None, r[3] if len(r) > 3 else None] != ["Exercise", "Skipped", "Notes"]:
        ctx.add("header_columns", f"columns B-D are {r[1:4]!r}", i)
    cols = [v for v in r[4:]]
    while cols and cols[-1] is None:
        cols.pop()
    parsed = []
    for v in cols:
        m = SET_HEADER.match(str(v)) if v is not None else None
        if not m:
            ctx.add("header_set_column", f"bad set column header {v!r}", i)
            return DEFAULT_SET_FIELDS, 0
        parsed.append((int(m.group(1)), m.group(2)))
    if not parsed:
        return DEFAULT_SET_FIELDS, 0
    fields = [f for k, f in parsed if k == 1]
    nsets = max(k for k, _ in parsed)
    expected = [(k, f) for k in range(1, nsets + 1) for f in fields]
    if parsed != expected or len(set(fields)) != len(fields):
        ctx.add("header_set_order", "set columns are not Set 1..k with the same fields each", i)
    if fields != DEFAULT_SET_FIELDS:
        ctx.add("header_set_fields", f"set fields {fields} differ from exports {DEFAULT_SET_FIELDS}", i)
    return fields, nsets


def _parse_exercise(ctx, r, i, cycle, names):
    raw = str(r[1])
    m = SUPERSET.match(raw)
    name, ss = (m.group(1), int(m.group(2))) if m else (raw, None)
    if not m and LOOKALIKE_SUPERSET.search(raw):
        ctx.add("superset_lookalike", f"{raw!r} looks like a superset but doesn't use ' ∈ SS<n>'", i)
    name = name.strip()
    if not name:
        ctx.add("exercise_name_empty", "empty exercise name", i)
    elif names is not None and name.lower() not in names:
        ctx.add("exercise_name_unknown", f"{name!r} not in exercise list", i)
    skipped = r[2] if len(r) > 2 else None
    if skipped not in ("No", "Yes"):
        ctx.add("skipped_value", f"Skipped is {skipped!r}", i)
    elif skipped == "Yes":
        ctx.add("skipped_yes", "Skipped 'Yes'", i)
    notes = r[3] if len(r) > 3 else None
    fields, width = cycle["fields"], len(cycle["fields"])
    sets, seen_empty = [], False
    for k in range(cycle["nsets"]):
        vals = {f: (r[4 + k * width + j] if len(r) > 4 + k * width + j else None) for j, f in enumerate(fields)}
        if all(v is None for v in vals.values()):
            seen_empty = True
            continue
        if seen_empty:
            ctx.add("set_gap", f"Set {k + 1} filled after an empty set", i)
        sets.append(_parse_set(ctx, vals, i, k + 1))
    extra = r[4 + cycle["nsets"] * width:]
    if any(v is not None for v in extra):
        ctx.add("row_unrecognized", "values beyond the last set column", i)
    if not sets:
        ctx.add("no_sets", f"{name!r} has no sets", i)
    return {"name": name, "superset": ss, "row": i, "skipped": skipped == "Yes", "notes": notes, "sets": sets}


def _parse_set(ctx, vals, i, k):
    t, reps, rir = vals.get("Type"), vals.get("Rep Range"), vals.get("RIR")
    if t is None:
        ctx.add("set_no_type", f"Set {k} has values but no Type", i)
    else:
        _check_value(ctx, "Set Type", t, i)
    if reps is None:
        ctx.add("reps_missing", f"Set {k} has no rep range", i)
    else:
        s = str(reps)
        md = REP_DROPS.match(s)
        if md:
            n_rep_drops = md.group(3).count("(")
            if t != "Drop Set":
                ctx.add("drop_syntax", f"Set {k} rep range {s!r} uses drop syntax on a {t!r}", i)
            if n_rep_drops > 1:
                ctx.add("drop_multi_untested", f"Set {k} has {n_rep_drops} drops", i)
            for lo, hi in re.findall(r"(\d+) - (\d+)", s):
                if int(hi) < int(lo):
                    ctx.add("rep_range_order", f"Set {k} rep range {s!r}: max is below min", i)
            if isinstance(rir, str) and RIR_PAIR.match(rir) and RIR_PAIR.match(rir).group(2).count("(") != n_rep_drops:
                ctx.add("drop_count_mismatch", f"Set {k} rep range {s!r} vs RIR {rir!r}", i)
        m = None if md else REP_RANGE.match(s)
        if md:
            pass
        elif m:
            lo, hi = int(m.group(1)), int(m.group(2))
            if hi < lo:
                ctx.add("rep_range_order", f"Set {k} rep range {s!r}: max is below min", i)
            elif hi > lo and t == "Drop Set":
                ctx.add("drop_set_range", f"Set {k} drop set range {s!r} will import as '{lo} - {lo}'", i)
        elif REP_RANGE_LOOSE.match(s):
            lo, hi = map(int, REP_RANGE_LOOSE.match(s).groups())
            ctx.add("rep_range_format", f"Set {k} rep range {s!r}; exports write '{lo} - {hi}'", i)
            if hi < lo:
                ctx.add("rep_range_order", f"Set {k} rep range {s!r}: max is below min", i)
        elif REP_OPEN.match(s):
            if t != "Failure Set":
                ctx.add("rep_open_untested", f"Set {k} open-ended rep range {s!r} on a {t!r}", i)
        elif re.fullmatch(r"\d+", s.strip()):
            ctx.add("rep_single", f"Set {k} single rep target {s!r}", i)
        else:
            ctx.add("rep_range_invalid", f"Set {k} rep range {s!r}", i)
    if rir is None:
        ctx.add("rir_missing", f"Set {k} has no RIR", i)
    elif isinstance(rir, str) and RIR_PAIR.match(rir):
        if t != "Drop Set":
            ctx.add("rir_pair_untested", f"Set {k} RIR {rir!r} on a {t!r}", i)
        if RIR_PAIR.match(rir).group(2).count("(") > 1 and not (reps and REP_DROPS.match(str(reps))):
            ctx.add("drop_multi_untested", f"Set {k} RIR {rir!r} lists several drops", i)
    elif isinstance(rir, bool) or not isinstance(rir, (int, float)) or rir < 0 or rir != int(rir):
        ctx.add("rir_invalid", f"Set {k} RIR {rir!r}", i)
    elif rir > 10:
        ctx.add("rir_high", f"Set {k} RIR {rir}", i)
    rest = vals.get("Rest")
    if rest is not None:
        if isinstance(rest, bool) or (isinstance(rest, (int, float)) and (rest < 0 or rest != int(rest))):
            ctx.add("rest_invalid", f"Set {k} Rest {rest!r}", i)
        elif not isinstance(rest, (int, float)):
            ctx.add("rest_untested", f"Set {k} Rest {rest!r}", i)
    if vals.get("Duration") is not None or vals.get("Distance") is not None:
        ctx.add("duration_distance_untested", f"Set {k} Duration/Distance values", i)
    return Set(type=t, reps=reps, rir=int(rir) if isinstance(rir, (int, float)) and not isinstance(rir, bool) and rir == int(rir) else rir,
               rest=vals.get("Rest"), duration=vals.get("Duration"), distance=vals.get("Distance"))


def _check_supersets(ctx, day):
    groups = {}
    for idx, e in enumerate(day["exercises"]):
        if e["superset"] is not None:
            groups.setdefault(e["superset"], []).append(idx)
    for n, idxs in groups.items():
        if len(idxs) == 1:
            ctx.add("superset_single", f"SS{n} has one member", day["exercises"][idxs[0]]["row"])
        if idxs != list(range(idxs[0], idxs[0] + len(idxs))):
            ctx.add("superset_split", f"SS{n} members aren't adjacent", day["exercises"][idxs[0]]["row"])
    order = list(dict.fromkeys(e["superset"] for e in day["exercises"] if e["superset"] is not None))
    if order and order != list(range(1, len(order) + 1)):
        ctx.add("superset_numbering", f"supersets numbered {order} in {day['name']!r}", day["row"])


def _shape(cycle):
    return [d if d == "Rest" else (d["name"], d["gym"], tuple((e["name"], e["superset"]) for e in d["exercises"]))
            for d in cycle["days"]]


def _check_cycle_structure(ctx, b):
    cyc = [b["cycles"][n] for n in sorted(b["cycles"])]
    if len(cyc) < 2:
        return
    first = _shape(cyc[0])
    for c in cyc[1:]:
        if _shape(c) != first:
            ctx.add("cycle_structure", f"Cycle {c['num']} days/exercises differ from Cycle {cyc[0]['num']}", c["row"])


def _build(meta, n_cycles, blocks):
    gyms = Counter(d["gym"] for b in blocks for c in b["cycles"].values() for d in c["days"] if isinstance(d, dict))
    default_gym = gyms.most_common(1)[0][0] if gyms else "Home Gym"
    fields = next((c["fields"] for b in blocks for c in b["cycles"].values()), DEFAULT_SET_FIELDS)
    out_blocks = []
    for b in blocks:
        cyc = [b["cycles"][n] for n in sorted(b["cycles"])]
        days = []
        for di, d0 in enumerate(cyc[0]["days"]):
            if d0 == "Rest":
                days.append("Rest")
                continue
            exs = []
            for ei, e0 in enumerate(d0["exercises"]):
                per = [c["days"][di]["exercises"][ei] for c in cyc]
                exs.append(Exercise(e0["name"], superset=e0["superset"],
                                    cycles=[ExerciseCycle(p["sets"], p["notes"], p["skipped"]) for p in per]))
            days.append(Day(d0["name"], exs, None if d0["gym"] == default_gym else d0["gym"]))
        out_blocks.append(Block(days, b["name"] if b["name"] != f"Block {len(out_blocks) + 1}" else None))
    return Program(meta["Program"], n_cycles, blocks=out_blocks, deload=meta["Deload"], color=meta["Color"],
                   icon=meta["Icon"], gym=default_gym, set_fields=None if fields == DEFAULT_SET_FIELDS else fields)


FORMAT_RULES_BEGIN = "<!-- rules:begin (generated by `python -m mfxlsx rules`) -->"
FORMAT_RULES_END = "<!-- rules:end -->"


def rules_markdown() -> str:
    lines = ["| Code | Severity | Evidence |", "|---|---|---|"]
    for code, (level, evidence) in RULES.items():
        lines.append(f"| `{code}` | {level} | {evidence} |")
    return "\n".join(lines)
