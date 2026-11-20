"""Compare a file we built with the app's re-export of it.

Usage: python -m mfxlsx compare SENT.xlsx REEXPORT.xlsx

Import the file in MacroFactor, export it again (Program Settings > Export Program),
then compare. Every difference is something the app changed on import: a renamed
exercise (an alias it mapped to its own name), a dropped or rewritten value, or an
edit you made in the app.
"""
from __future__ import annotations

from dataclasses import dataclass

from .reader import read


@dataclass
class Change:
    where: str
    field: str
    sent: object
    exported: object
    cycles: list[int] | None = None

    def __str__(self):
        cyc = ""
        if self.cycles:
            c = self.cycles
            cyc = f" (cycle {c[0]})" if len(c) == 1 else (
                f" (cycles {c[0]}-{c[-1]})" if c == list(range(c[0], c[-1] + 1)) else f" (cycles {c})")
        return f"{self.where}: {self.field} {self.sent!r} -> {self.exported!r}{cyc}"


def _set_key(s):
    return {k: s.get(k) for k in ("type", "reps", "rir", "rest", "duration", "distance")}


def diff(sent: dict, exported: dict) -> list[Change]:
    raw: list[tuple] = []  # (where, field, a, b, cycle)
    for k in ("name", "cycles", "deload", "color", "icon", "set_fields"):
        if sent.get(k) != exported.get(k):
            raw.append(("program", k, sent.get(k), exported.get(k), None))
    for bi in range(max(len(sent["blocks"]), len(exported["blocks"]))):
        a = sent["blocks"][bi] if bi < len(sent["blocks"]) else None
        b = exported["blocks"][bi] if bi < len(exported["blocks"]) else None
        bname = (a or b)["name"]
        if a is None or b is None:
            raw.append((bname, "block", a and a["name"], b and b["name"], None))
            continue
        for di in range(max(len(a["days"]), len(b["days"]))):
            da = a["days"][di] if di < len(a["days"]) else None
            db = b["days"][di] if di < len(b["days"]) else None
            label = f"{bname} / day {di + 1}"
            if da is None or db is None or da == "Rest" or db == "Rest":
                if da != db:
                    raw.append((label, "day", _day_label(da), _day_label(db), None))
                continue
            label = f"{bname} / {da['name']}"
            for k in ("name", "gym"):
                if da[k] != db[k]:
                    raw.append((label, f"day {k}", da[k], db[k], None))
            for ei in range(max(len(da["exercises"]), len(db["exercises"]))):
                ea = da["exercises"][ei] if ei < len(da["exercises"]) else None
                eb = db["exercises"][ei] if ei < len(db["exercises"]) else None
                elabel = f"{label} #{ei + 1}"
                if ea is None or eb is None:
                    raw.append((elabel, "exercise", ea and ea["name"], eb and eb["name"], None))
                    continue
                elabel = f"{label} #{ei + 1} {ea['name']}"
                if ea["name"] != eb["name"]:
                    raw.append((elabel, "exercise name", ea["name"], eb["name"], None))
                if ea.get("superset") != eb.get("superset"):
                    raw.append((elabel, "superset", ea.get("superset"), eb.get("superset"), None))
                for ci, (ca, cb) in enumerate(zip(ea["cycles"], eb["cycles"]), 1):
                    for k in ("skipped", "notes"):
                        if ca.get(k) != cb.get(k):
                            raw.append((elabel, k, ca.get(k), cb.get(k), ci))
                    for si in range(max(len(ca["sets"]), len(cb["sets"]))):
                        sa = _set_key(ca["sets"][si]) if si < len(ca["sets"]) else None
                        sb = _set_key(cb["sets"][si]) if si < len(cb["sets"]) else None
                        if sa is None or sb is None:
                            raw.append((elabel, f"set {si + 1}", sa, sb, ci))
                            continue
                        for k in sa:
                            if sa[k] != sb[k]:
                                raw.append((elabel, f"set {si + 1} {k}", sa[k], sb[k], ci))
    grouped: dict[tuple, Change] = {}
    for where, field, a, b, cycle in raw:
        key = (where, field, repr(a), repr(b))
        if key not in grouped:
            grouped[key] = Change(where, field, a, b, [] if cycle else None)
        if cycle:
            grouped[key].cycles.append(cycle)
    return list(grouped.values())


def _day_label(d):
    if d is None:
        return None
    return "Rest" if d == "Rest" else f"{d['name']} @ {d['gym']}"


def aliases(changes: list[Change]) -> dict[str, str]:
    """Exercise renames: the name we sent -> the name the app exported."""
    return {c.sent: c.exported for c in changes if c.field == "exercise name"}


def compare_files(sent_path, exported_path):
    a, b = read(sent_path), read(exported_path)
    for label, res in (("sent", a), ("re-export", b)):
        if res.program is None:
            raise ValueError(f"{label} file has errors:\n" + "\n".join(map(str, res.errors)))
    return diff(a.program.to_dict(), b.program.to_dict())
