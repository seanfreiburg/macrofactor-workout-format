"""App version the rules were checked against, and the known value lists.

CONFIRMED: seen in real exports or accepted by an import test.
CANDIDATE: found in the app's strings, not yet confirmed.
Update both when tests/RESULTS.md gets new results.
"""

APP = {
    "name": "MacroFactor Workouts",
    "platform": "Android",
    "package": "com.sbs.train",
    "version": "1.4.5",
    "version_code": 160,
    "checked": "2026-11-20",
}
APP_LABEL = f"{APP['name']} {APP['version']} ({APP['platform']}, {APP['package']}, version code {APP['version_code']})"

CONFIRMED = {
    "Deload": {"Last Cycle"},
    "Color": {"Orange"},
    "Icon": {"Chess Queen"},
    "Set Type": {"Standard Set"},
}
CANDIDATE = {
    "Deload": {"First Cycle", "None"},
    "Color": {"Red", "Yellow", "Green", "Teal", "Blue", "Purple"},
    "Icon": {"Chess King", "Chess King 2", "Chess Rook", "Chess Bishop", "Chess Bishop 2", "Chess Knight", "Chess Pawn"},
    "Set Type": {"Drop Set", "Myo Set", "Failure Set"},
}
