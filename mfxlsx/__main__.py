"""Command line: validate, dump, and build MacroFactor program files.

  python -m mfxlsx validate FILE.xlsx [--strict] [--names exercises.txt]
  python -m mfxlsx dump FILE.xlsx            # program as JSON (per-cycle targets)
  python -m mfxlsx build PROGRAM.json -o OUT.xlsx [--strict]
  python -m mfxlsx rules                     # validation rules as a Markdown table
"""
import argparse
import json
import sys

from . import APP_LABEL, from_dict, read, read_workbook, to_workbook


def _names(path):
    if not path:
        return None
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def _report(res, strict):
    for i in res.issues:
        print(i)
    e, w = len(res.errors), len(res.warnings)
    ok = res.ok(strict)
    print(f"{'VALID' if ok else 'INVALID'}: {e} error(s), {w} warning(s). Rules checked against {APP_LABEL}.")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m mfxlsx")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("file")
    v.add_argument("--strict", action="store_true", help="treat warnings as errors")
    v.add_argument("--names", help="text file of valid exercise names, one per line")
    d = sub.add_parser("dump")
    d.add_argument("file")
    b = sub.add_parser("build")
    b.add_argument("json")
    b.add_argument("-o", "--out", required=True)
    b.add_argument("--strict", action="store_true")
    b.add_argument("--names")
    sub.add_parser("rules")
    a = ap.parse_args(argv)

    if a.cmd == "rules":
        from .reader import rules_markdown
        print(rules_markdown())
        return 0

    if a.cmd == "validate":
        return _report(read(a.file, _names(a.names)), a.strict)
    if a.cmd == "dump":
        res = read(a.file)
        if res.program is None:
            return _report(res, False)
        json.dump(res.program.to_dict(), sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 0
    with open(a.json, encoding="utf-8") as f:
        program = from_dict(json.load(f))
    wb = to_workbook(program)
    res = read_workbook(wb, _names(a.names))
    if not res.ok(a.strict):
        _report(res, a.strict)
        print("not written", file=sys.stderr)
        return 1
    wb.save(a.out)
    for i in res.issues:
        print(i)
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
