"""Program model shared by the reader and the writer.

A program has blocks; a block has a list of days that repeats once per cycle; a day is
"Rest" or a list of exercises. Each exercise has one target per cycle (sets, notes,
skipped), which matches how MacroFactor stores programs.

Two ways to give an exercise's targets:
- ``cycles=[ExerciseCycle, ...]``: explicit, one per cycle (what the reader returns)
- ``sets=[Set, ...]``: a template; each Set field may be a scalar, a list indexed by
  cycle (cycle 1 = index 0), or a function of the cycle number (1-based)
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Union

Value = Union[str, int, float, None, list, Callable[[int], Any]]
SET_FIELDS = ["Type", "Rep Range", "RIR", "Rest", "Duration", "Distance"]
DEFAULT_SET_FIELDS = SET_FIELDS[:4]
_ATTR = {"Type": "type", "Rep Range": "reps", "RIR": "rir", "Rest": "rest", "Duration": "duration", "Distance": "distance"}


def _at(v, cycle):
    if callable(v):
        return v(cycle)
    if isinstance(v, (list, tuple)):
        return v[cycle - 1]
    return v


@dataclass
class Set:
    type: Value = "Standard Set"
    reps: Value = None  # "8 - 12" or "10"
    rir: Value = None
    rest: Value = None
    duration: Value = None
    distance: Value = None

    def at(self, cycle: int) -> "Set":
        return Set(**{k: _at(v, cycle) for k, v in asdict(self).items()})

    def get(self, column: str):
        return getattr(self, _ATTR[column])


@dataclass
class ExerciseCycle:
    sets: list[Set]
    notes: str | None = None
    skipped: bool = False


@dataclass
class Exercise:
    name: str
    sets: list[Set] | None = None
    notes: Value = None
    skipped: Value = False
    superset: int | None = None
    cycles: list[ExerciseCycle] | None = None

    def cycle(self, n: int) -> ExerciseCycle:
        if self.cycles is not None:
            return self.cycles[n - 1]
        return ExerciseCycle([s.at(n) for s in self.sets or []], _at(self.notes, n), bool(_at(self.skipped, n)))


@dataclass
class Day:
    name: str
    exercises: list[Exercise]
    gym: str | None = None  # defaults to Program.gym


DayOrRest = Union[Day, str]


@dataclass
class Block:
    days: list[DayOrRest]
    name: str | None = None  # defaults to "Block <n>"


@dataclass
class Program:
    name: str
    cycles: int
    days: list[DayOrRest] = field(default_factory=list)  # shorthand for one block
    blocks: list[Block] = field(default_factory=list)
    deload: str = "Last Cycle"
    color: str = "Orange"
    icon: str = "Chess Queen"
    gym: str = "Home Gym"
    set_fields: list[str] | None = None  # per-set columns; default Type, Rep Range, RIR, Rest
    metadata_extra: list[str] = field(default_factory=list)

    def all_blocks(self) -> list[Block]:
        return self.blocks or [Block(self.days)]

    def to_dict(self) -> dict:
        """Fully expanded, JSON-ready form (explicit per-cycle targets)."""
        blocks = []
        for bi, b in enumerate(self.all_blocks(), 1):
            days = []
            for d in b.days:
                if not isinstance(d, Day):
                    days.append("Rest")
                    continue
                exs = []
                for e in d.exercises:
                    cyc = []
                    for c in range(1, self.cycles + 1):
                        ec = e.cycle(c)
                        cyc.append({"skipped": ec.skipped, "notes": ec.notes,
                                    "sets": [{k: v for k, v in asdict(s).items() if v is not None} for s in ec.sets]})
                    exs.append({"name": e.name, "superset": e.superset, "cycles": cyc})
                days.append({"name": d.name, "gym": d.gym or self.gym, "exercises": exs})
            blocks.append({"name": b.name or f"Block {bi}", "days": days})
        return {"name": self.name, "cycles": self.cycles, "deload": self.deload, "color": self.color,
                "icon": self.icon, "set_fields": self.set_fields or DEFAULT_SET_FIELDS, "blocks": blocks}


def from_dict(d: dict) -> Program:
    """Inverse of Program.to_dict(); also accepts the shorthand forms (top-level "days",
    template "sets" with per-cycle lists)."""
    def mk_set(s):
        return Set(type=s.get("type", "Standard Set"), reps=s.get("reps"), rir=s.get("rir"), rest=s.get("rest"),
                   duration=s.get("duration"), distance=s.get("distance"))

    def mk_ex(e):
        if "cycles" in e:
            cyc = [ExerciseCycle([mk_set(s) for s in c.get("sets", [])], c.get("notes"), bool(c.get("skipped")))
                   for c in e["cycles"]]
            return Exercise(e["name"], superset=e.get("superset"), cycles=cyc)
        return Exercise(e["name"], [mk_set(s) for s in e.get("sets", [])], e.get("notes"), e.get("skipped", False),
                        e.get("superset"))

    def mk_days(days):
        return ["Rest" if x == "Rest" else Day(x["name"], [mk_ex(e) for e in x.get("exercises", [])], x.get("gym"))
                for x in days]

    blocks = [Block(mk_days(b["days"]), b.get("name")) for b in d.get("blocks", [])]
    return Program(d["name"], int(d["cycles"]), days=mk_days(d.get("days", [])), blocks=blocks,
                   deload=d.get("deload", "Last Cycle"), color=d.get("color", "Orange"),
                   icon=d.get("icon", "Chess Queen"), gym=d.get("gym", "Home Gym"), set_fields=d.get("set_fields"))
