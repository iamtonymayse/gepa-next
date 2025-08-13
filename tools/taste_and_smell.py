#!/usr/bin/env python3
from __future__ import annotations
import ast
import json
import re
import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
@dataclass
class Finding:
    severity: str
    tag: str
    file: str
    line: int
    message: str
    snippet: str
    diff: str = ""


def detect_proj_dir() -> Path:
    root = Path.cwd()
    if (root / "innerloop").exists():
        return root
    if (root / "gepa-next" / "innerloop").exists():
        return root / "gepa-next"
    return root


def run(cmd: List[str], cwd: Path, timeout: int = 300) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(  # nosec B603
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 127, "", f"{cmd[0]} not installed"
    except subprocess.TimeoutExpired as exc:  # pragma: no cover - defensive
        return 124, str(exc.stdout or ""), f"timeout after {timeout}s"


def run_json(cmd: List[str], cwd: Path) -> Tuple[Any, int]:
    code, out, err = run(cmd, cwd)
    raw = out or err or "{}"
    try:
        return json.loads(raw), code
    except Exception:
        return None, code


# Tool wrappers
def check_ruff(proj: Path) -> Dict[str, Any]:
    data, code = run_json(["ruff", "check", str(proj), "--output-format=json"], proj)
    issues = data if isinstance(data, list) else []
    return {"issues": issues, "code": code}


def check_mypy(proj: Path) -> Dict[str, Any]:
    code, out, err = run(
        [
            "mypy",
            str(proj / "innerloop"),
            "--hide-error-context",
            "--pretty",
            "--show-error-codes",
        ],
        proj,
    )
    lines = [ln for ln in (out + err).splitlines() if ": error:" in ln]
    return {"errors": lines, "code": code}


def check_bandit(proj: Path) -> Dict[str, Any]:
    data, code = run_json(
        [
            "bandit",
            "-r",
            str(proj),
            "-f",
            "json",
            "-q",
            "-x",
            str(proj / "tests"),
        ],
        proj,
    )
    issues = (data or {}).get("results", []) if isinstance(data, dict) else []
    return {"issues": issues, "code": code}


def check_radon(proj: Path) -> Dict[str, Any]:
    cc, _ = run_json(["radon", "cc", "-j", str(proj)], proj)
    mi, _ = run_json(["radon", "mi", "-j", str(proj)], proj)
    return {"cc": cc or {}, "mi": mi or {}}


def run_pytest_smoke(proj: Path) -> Dict[str, Any]:
    code, out, err = run(
        [
            "pytest",
            "-q",
            "--maxfail=1",
            "--disable-warnings",
            "-k",
            "health or sse",
        ],
        proj,
    )
    return {"code": code, "out": out, "err": err}


def run_pytest_cov(proj: Path) -> Dict[str, Any]:
    code, out, err = run(
        [
            "pytest",
            "-q",
            f"--cov={proj / 'innerloop'}",
            "--cov-report=term:skip-covered",
        ],
        proj,
    )
    text = out + err
    m = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", text)
    cov = int(m.group(1)) if m else 0
    return {"code": code, "out": out, "err": err, "coverage": cov}


# FastAPI heuristics & smell scans
def parse_python(path: Path) -> ast.AST | None:
    try:
        return ast.parse(path.read_text(), filename=str(path))
    except Exception:
        return None


def check_middleware_order(main_py: Path) -> Tuple[str, List[Finding]]:
    expected = [
        "LoggingMiddleware",
        "AuthMiddleware",
        "RateLimitMiddleware",
        "SizeLimitMiddleware",
    ]
    order: List[str] = []
    findings: List[Finding] = []
    if not main_py.exists():
        return "main.py not found", findings
    txt = main_py.read_text().splitlines()
    for idx, line in enumerate(txt, 1):
        m = re.search(r"app\.add_middleware\((\w+)", line)
        if m:
            name = m.group(1)
            if name in expected:
                order.append(name)
    if order != expected:
        findings.append(
            Finding(
                "MED",
                "CORRECTNESS",
                str(main_py.relative_to(main_py.parents[1])),
                0,
                f"Middleware order {order} != {expected}",
                "\n".join(txt[:40]),
                diff="# reorder middlewares: Logging -> Auth -> RateLimit -> SizeLimit",
            )
        )
    status = "ok" if order == expected else "misordered"
    return status, findings


def check_sse_route(opt_py: Path) -> Tuple[str, List[Finding]]:
    findings: List[Finding] = []
    status = "missing"
    if not opt_py.exists():
        return status, findings
    txt = opt_py.read_text()
    if "StreamingResponse" in txt:
        status = "ok"
        headers = ["Cache-Control", "Connection", "X-Accel-Buffering"]
        for h in headers:
            if h not in txt:
                findings.append(
                    Finding(
                        "MED",
                        "API",
                        str(opt_py.relative_to(opt_py.parents[2])),
                        0,
                        f"SSE missing header {h}",
                        "",
                        diff=f"# add header {h}",
                    )
                )
        if "prelude_retry_ms" not in txt:
            findings.append(
                Finding(
                    "LOW",
                    "API",
                    str(opt_py.relative_to(opt_py.parents[2])),
                    0,
                    "SSE retry prelude missing",
                    "",
                    diff="# yield retry prelude",
                )
            )
    return status, findings


def check_auth(auth_py: Path) -> Tuple[str, List[Finding]]:
    findings: List[Finding] = []
    status = "missing"
    if not auth_py.exists():
        return status, findings
    txt = auth_py.read_text()
    status = "ok"
    if "hmac.compare_digest" not in txt:
        findings.append(
            Finding(
                "HIGH",
                "SECURITY",
                str(auth_py.relative_to(auth_py.parents[2])),
                0,
                "Auth token check not constant time",
                "",
                diff="hmac.compare_digest(token, expected)",
            )
        )
    if "OPENROUTER_API_KEY" not in txt or "authorization" not in txt.lower():
        findings.append(
            Finding(
                "MED",
                "SECURITY",
                str(auth_py.relative_to(auth_py.parents[2])),
                0,
                "Auth bypass rule missing",
                "",
            )
        )
    return status, findings


def scan_smells(proj: Path) -> List[Finding]:
    findings: List[Finding] = []
    for path in proj.rglob("*.py"):
        if path.parts[0] == "tests" or "tests" in path.parts:
            continue
        txt = path.read_text()
        rel = str(path.relative_to(proj))
        for pat, sev, tag, msg in [
            (r"time\.sleep\(", "MED", "PERF", "time.sleep in async context"),
            (r"subprocess\.run\(", "MED", "PERF", "blocking subprocess.run"),
            (r"requests\.", "MED", "PERF", "requests usage in endpoint"),
            (r"print\(", "LOW", "STYLE", "print statement"),
            (r"from .* import \*", "LOW", "STYLE", "star import"),
        ]:
            for m in re.finditer(pat, txt):
                line = txt[: m.start()].count("\n") + 1
                snippet = txt.splitlines()[line - 1].strip()
                findings.append(Finding(sev, tag, rel, line, msg, snippet))
        # FastAPI route hygiene
        tree = parse_python(path)
        if not tree:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                decos = node.decorator_list
                for deco in decos:
                    if (
                        isinstance(deco, ast.Call)
                        and isinstance(deco.func, ast.Attribute)
                        and deco.func.attr in {"get", "post", "put", "delete"}
                        and isinstance(deco.func.value, ast.Name)
                        and deco.func.value.id == "router"
                    ):
                        kw_names = {kw.arg for kw in deco.keywords if kw.arg}
                        if "status_code" not in kw_names:
                            findings.append(
                                Finding(
                                    "LOW",
                                    "API",
                                    rel,
                                    node.lineno,
                                    "Missing status_code",
                                    ast.get_source_segment(txt, node) or node.name,
                                    diff="@router.{method}(..., status_code=200)",
                                )
                            )
                        if "response_model" not in kw_names:
                            findings.append(
                                Finding(
                                    "LOW",
                                    "API",
                                    rel,
                                    node.lineno,
                                    "Missing response_model",
                                    ast.get_source_segment(txt, node) or node.name,
                                    diff="@router.{method}(..., response_model=Model)",
                                )
                            )
    return findings


def fastapi_checks(proj: Path) -> Tuple[Dict[str, str], List[Finding]]:
    checks: Dict[str, str] = {}
    findings: List[Finding] = []
    main_py = proj / "innerloop" / "main.py"
    status, f = check_middleware_order(main_py)
    checks["middleware_order"] = status
    findings.extend(f)
    opt_py = proj / "innerloop" / "api" / "routers" / "optimize.py"
    status, f = check_sse_route(opt_py)
    checks["sse_route"] = status
    findings.extend(f)
    auth_py = proj / "innerloop" / "api" / "middleware" / "auth.py"
    status, f = check_auth(auth_py)
    checks["auth"] = status
    findings.extend(f)
    return checks, findings


# Report rendering
def render_markdown(
    summary: List[str],
    score: Dict[str, Any],
    fastapi_info: Dict[str, str],
    findings: List[Finding],
    appendices: Dict[str, str],
) -> str:
    lines: List[str] = []
    lines.append("# Taste & Smell Report")
    lines.append("\n## 1. Executive summary")
    for b in summary:
        lines.append(f"- {b}")
    lines.append("\n## 2. Scorecard")
    lines.append("| Check | Result |")
    lines.append("| --- | --- |")
    lines.append(f"| Ruff issues | {len(score.get('ruff', []))} |")
    lines.append(f"| Mypy errors | {len(score.get('mypy', []))} |")
    lines.append(f"| Bandit issues | {len(score.get('bandit', []))} |")
    lines.append(f"| Complexity hotspots | {score.get('complexity', 0)} |")
    lines.append(f"| Coverage % | {score.get('coverage', 0)} |")
    lines.append("\n## 3. FastAPI checks")
    for k, v in fastapi_info.items():
        lines.append(f"- **{k.replace('_', ' ').title()}**: {v}")
    lines.append("\n## 4. Smell catalog")
    for f in findings:
        lines.append(f"- `{f.severity}` `{f.tag}` {f.file}:{f.line} – {f.message}\n\n````\n{f.snippet}\n````")
        if f.diff:
            lines.append(f"  Suggested diff:\n  ```diff\n{f.diff}\n  ```")
    lines.append("\n## 5. Polish plan")
    for idx, f in enumerate(findings[:8], 1):
        payoff = "HIGH" if f.severity == "HIGH" else "MED"
        effort = "S" if f.severity == "LOW" else "M"
        lines.append(f"{idx}. {f.message} ({f.file}:{f.line}) – effort {effort}, payoff {payoff}")
    lines.append("\n## 6. Appendices")
    for name, content in appendices.items():
        lines.append(f"### {name}\n````\n{content}\n````")
    return "\n".join(lines)


# Main
def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="skip heavier checks")
    args = parser.parse_args(list(argv) if argv is not None else None)

    proj = detect_proj_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    reports = proj / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    report = reports / f"taste_and_smell_report_{ts}.md"

    try:
        ruff = check_ruff(proj)
        mypy = check_mypy(proj)
        bandit = check_bandit(proj)
        radon = check_radon(proj) if not args.fast else {"cc": {}, "mi": {}}
        run_pytest_smoke(proj)
        cov = run_pytest_cov(proj) if not args.fast else {"coverage": 0, "out": "", "err": ""}
        fastapi_info, fa_findings = fastapi_checks(proj)
        smell_findings = scan_smells(proj)
        findings = fa_findings + smell_findings
        score = {
            "ruff": ruff["issues"],
            "mypy": mypy["errors"],
            "bandit": bandit["issues"],
            "complexity": sum(
                len(v) for v in radon.get("cc", {}).values() if isinstance(v, list)
            ),
            "coverage": cov.get("coverage", 0),
        }
        by_sev: Dict[str, int] = {}
        for f in findings:
            by_sev[f.severity] = by_sev.get(f.severity, 0) + 1
        summary = [
            f"{sev}: {cnt} issue(s)" for sev, cnt in sorted(by_sev.items(), reverse=True)
        ][:3]
        appendices = {
            "ruff": json.dumps(ruff["issues"], indent=2)[:1000],
            "mypy": "\n".join(mypy["errors"][:20]),
            "bandit": json.dumps(bandit["issues"], indent=2)[:1000],
        }
        content = render_markdown(
            summary, score, fastapi_info, findings, appendices
        )
    except Exception as exc:  # pragma: no cover - defensive
        import traceback

        tb = traceback.format_exc(limit=5)
        content = f"# Taste and Smell Audit\n\nError during audit: {exc}\n\n````\n{tb}\n````"

    report.write_text(content, encoding="utf-8")
    print(f"Wrote {report}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main())
