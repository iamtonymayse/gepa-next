import pathlib
import re

FORBIDDEN = [
    r"\brequests\.",
    r"\burllib\.request\.",
    r"\baiohttp\.ClientSession\(",
]


def test_no_blocking_http_in_endpoints():
    root = pathlib.Path(__file__).resolve().parents[1]
    routers = root / "innerloop" / "api" / "routers"
    bad = []
    for py in routers.rglob("*.py"):
        txt = py.read_text(encoding="utf-8", errors="ignore")
        for pat in FORBIDDEN:
            if re.search(pat, txt):
                bad.append((py, pat))
    assert not bad, f"Blocking HTTP usage in endpoints: {bad}"
