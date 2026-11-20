"""Known-good exercise names bundled with the package (see data/)."""
import pathlib

DATA = pathlib.Path(__file__).with_name("data")


def load_names(path) -> list[str]:
    """One name per line; '#' starts a comment."""
    out = []
    for line in open(path, encoding="utf-8"):
        name = line.split("#", 1)[0].strip()
        if name:
            out.append(name)
    return out


def load_aliases(path=DATA / "exercise-aliases.tsv") -> dict[str, str]:
    out = {}
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or "\t" not in line:
            continue
        sent, app = line.rstrip("\n").split("\t", 1)
        out[sent.strip()] = app.strip()
    return out


def known_names() -> list[str]:
    """Names seen in real exports, plus aliases the app is known to accept."""
    return load_names(DATA / "exercise-names.txt") + list(load_aliases())
