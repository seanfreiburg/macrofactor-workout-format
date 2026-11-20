"""Write MacroFactor Workouts program files (.xlsx) for Import From File.

See FORMAT.md for the format. Minimal use:

    from mfxlsx.writer import Program, Day, Exercise, Set, write
    day = Day("Monday", [Exercise("Low Incline Dumbbell Press", sets=[Set(reps="8 - 12", rir=2)] * 2)])
    write(Program("My Program", cycles=4, days=[day, "Rest", ...]), "my-program.xlsx")

Per-cycle variation: any Set field may be a function of the cycle number (1-based),
for example rir=lambda c: 3 if c <= 2 else 1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Union

import openpyxl
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

SHEET = "Training Programs"
SUPERSET_MARK = "∈"  # "∈"; members are named "<exercise> ∈ SS<n>"
SET_FIELDS = ["Type", "Rep Range", "RIR", "Rest", "Duration", "Distance"]

Value = Union[str, int, float, None, Callable[[int], Any]]


@dataclass
class Set:
    type: Value = "Standard Set"
    reps: Value = None  # "8 - 12" (range) or e.g. "10"
    rir: Value = None
    rest: Value = None
    duration: Value = None
    distance: Value = None

    def values(self, cycle: int) -> dict:
        raw = {"Type": self.type, "Rep Range": self.reps, "RIR": self.rir, "Rest": self.rest,
               "Duration": self.duration, "Distance": self.distance}
        return {k: (v(cycle) if callable(v) else v) for k, v in raw.items()}


@dataclass
class Exercise:
    name: str
    sets: list[Set]
    notes: str | None = None
    skipped: bool = False
    superset: int | None = None  # exercises sharing a number on one day form a superset


@dataclass
class Day:
    name: str  # e.g. "Monday"
    exercises: list[Exercise]
    gym: str | None = None  # defaults to Program.gym


@dataclass
class Block:
    days: list[Union[Day, str]]  # "Rest" for a rest day
    name: str | None = None  # defaults to "Block <n>"


@dataclass
class Program:
    name: str
    cycles: int
    days: list[Union[Day, str]] = field(default_factory=list)  # shorthand for a single block
    blocks: list[Block] = field(default_factory=list)
    deload: str = "Last Cycle"
    color: str = "Orange"
    icon: str = "Chess Queen"
    gym: str = "Home Gym"
    set_fields: list[str] | None = None  # per-set columns; default: Type, Rep Range, RIR, Rest
    metadata_extra: list[str] = field(default_factory=list)  # extra row-1 cells, for experiments


def _blocks(p: Program) -> list[Block]:
    return p.blocks or [Block(p.days)]


def write(p: Program, out) -> None:
    blocks = _blocks(p)
    fields = p.set_fields or SET_FIELDS[:4]
    max_sets = max((len(e.sets) for b in blocks for d in b.days if isinstance(d, Day) for e in d.exercises), default=1)

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
                    name = ex.name if ex.superset is None else f"{ex.name} {SUPERSET_MARK} SS{ex.superset}"
                    ws.cell(row, 2, name)
                    ws.cell(row, 3, "Yes" if ex.skipped else "No")
                    if ex.notes:
                        ws.cell(row, 4, ex.notes)
                    for si, st in enumerate(ex.sets):
                        vals = st.values(cycle)
                        for fi, f in enumerate(fields):
                            if vals.get(f) is not None:
                                ws.cell(row, 5 + si * len(fields) + fi, vals[f])
                    row += 1
                ws.cell(start, 1, f"{day.name} @ {day.gym or p.gym}").alignment = Alignment(vertical="top")
                if row - 1 > start:
                    ws.merge_cells(start_row=start, start_column=1, end_row=row - 1, end_column=1)

    widths = [21.79, 41.16, 17.89, 14.53] + [18.29, 16.28, 9.68, 10.76, 10.0, 10.0][: len(fields)] * max_sets
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    wb.save(out)
