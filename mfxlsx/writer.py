"""Write MacroFactor Workouts program files (.xlsx). Layout: see FORMAT.md."""
from __future__ import annotations

import openpyxl
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from .model import DEFAULT_SET_FIELDS, Day, Program

SHEET = "Training Programs"
SUPERSET_MARK = "∈"  # "∈"; members are named "<exercise> ∈ SS<n>"
_WIDTH = {"Type": 18.29, "Rep Range": 16.28, "RIR": 9.68, "Rest": 10.76, "Duration": 10.0, "Distance": 10.0}


def superset_name(name: str, n: int | None) -> str:
    return name if n is None else f"{name} {SUPERSET_MARK} SS{n}"


def to_workbook(p: Program) -> openpyxl.Workbook:
    blocks = p.all_blocks()
    fields = p.set_fields or DEFAULT_SET_FIELDS
    max_sets = max((len(e.cycle(c).sets) for b in blocks for d in b.days if isinstance(d, Day)
                    for e in d.exercises for c in range(1, p.cycles + 1)), default=1)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = SHEET
    wb.properties.creator = None
    meta = [f"Program: {p.name}", f"Cycles: {p.cycles}", f"Deload: {p.deload}", f"Color: {p.color}",
            f"Icon: {p.icon}", *p.metadata_extra]
    for col, v in enumerate(meta, 1):
        ws.cell(1, col, v)
    ws["A1"].font = Font(bold=True)

    header = ["Exercise", "Skipped", "Notes"]
    for s in range(1, max_sets + 1):
        header += [f"Set {s} {f}" for f in fields]

    row = 2
    for bi, block in enumerate(blocks, 1):
        ws.cell(row, 1, block.name or f"Block {bi}")
        row += 1
        for cycle in range(1, p.cycles + 1):
            ws.cell(row, 1, f"Cycle {cycle}")
            for col, v in enumerate(header, 2):
                ws.cell(row, col, v)
            row += 1
            for day in block.days:
                if not isinstance(day, Day):
                    ws.cell(row, 1, "Rest")
                    row += 1
                    continue
                start = row
                for ex in day.exercises:
                    ec = ex.cycle(cycle)
                    ws.cell(row, 2, superset_name(ex.name, ex.superset))
                    ws.cell(row, 3, "Yes" if ec.skipped else "No")
                    if ec.notes:
                        ws.cell(row, 4, ec.notes)
                    for si, st in enumerate(ec.sets):
                        for fi, f in enumerate(fields):
                            v = st.get(f)
                            if v is not None:
                                ws.cell(row, 5 + si * len(fields) + fi, v)
                    row += 1
                ws.cell(start, 1, f"{day.name} @ {day.gym or p.gym}").alignment = Alignment(vertical="top")
                if row - 1 > start:
                    ws.merge_cells(start_row=start, start_column=1, end_row=row - 1, end_column=1)

    widths = [21.79, 41.16, 17.89, 14.53] + [_WIDTH[f] for f in fields] * max_sets
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    return wb


def write(p: Program, out, validate: bool = True) -> None:
    """Write `p` to `out`. With validate=True, refuse to write a file that has errors."""
    wb = to_workbook(p)
    if validate:
        from .reader import read_workbook
        res = read_workbook(wb)
        if res.errors:
            raise ValueError("refusing to write an invalid program:\n" + "\n".join(map(str, res.errors)))
    wb.save(out)
