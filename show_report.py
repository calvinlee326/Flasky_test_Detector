#!/usr/bin/env python3
"""
Pretty-print a flaky_report.json produced by the detector.

Usage:
    python show_report.py [path/to/flaky_report.json]
"""

import json
import sys
from pathlib import Path

# Strip ANSI codes when output is not a real terminal (e.g. piped to a file).
_TTY = sys.stdout.isatty()

RESET = "\033[0m"  if _TTY else ""
RED   = "\033[31m" if _TTY else ""
YEL   = "\033[33m" if _TTY else ""
GRN   = "\033[32m" if _TTY else ""
BOLD  = "\033[1m"  if _TTY else ""
DIM   = "\033[2m"  if _TTY else ""


def color_score(score: float) -> str:
    if score >= 0.5:
        c = RED
    elif score > 0.0:
        c = YEL
    else:
        c = GRN
    # Return (plain_text, colored_text) so callers can pad by plain width.
    return f"{score:.2f}", f"{c}{score:.2f}{RESET}"


def outcome_char(o: str) -> str:
    return {"passed": f"{GRN}P{RESET}", "failed": f"{RED}F{RESET}",
            "error": f"{RED}E{RESET}", "skipped": f"{DIM}S{RESET}"}.get(o, "?")


def bar(score: float, width: int = 20) -> str:
    filled = round(score * width)
    return f"{RED}{'█' * filled}{DIM}{'░' * (width - filled)}{RESET}"


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("flaky_report.json")
    if not path.exists():
        print(f"Report not found: {path}")
        sys.exit(1)

    try:
        data = json.loads(path.read_text())
        s = data["summary"]
        tests = data["tests"]
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Invalid report file ({e}). Re-run pytest to regenerate it.")
        sys.exit(1)

    print(f"\n{BOLD}{'=' * 70}{RESET}")
    print(f"{BOLD}  FLAKY TEST DETECTOR — {path}{RESET}")
    print(f"{BOLD}{'=' * 70}{RESET}")
    print(f"  Runs per test : {s['runs_per_test']}")
    print(f"  Total tests   : {s['total_tests']}")
    print(f"  {RED}Flaky tests   : {s['flaky_tests']}{RESET}")
    print(f"  {GRN}Stable tests  : {s['stable_tests']}{RESET}")

    print(f"\n{BOLD}  {'Score':<8} {'Bar':<22} {'P/F':<8} {'Avg(s)':<8} Test{RESET}")
    print(f"  {'-' * 64}")

    for t in tests:
        plain_score, colored_score = color_score(t["flakiness_score"])
        # Pad using plain width so ANSI codes don't throw off alignment.
        padding = " " * (8 - len(plain_score))
        b = bar(t["flakiness_score"])
        pf = f"{GRN}{t['passes']}P{RESET}/{RED}{t['failures']}F{RESET}"
        pf_plain = f"{t['passes']}P/{t['failures']}F"
        pf_pad = " " * (8 - len(pf_plain))
        duration = f"{t['avg_duration_s']:.3f}"
        run_trace = " ".join(outcome_char(o) for o in t["outcomes"])
        short_id = t["nodeid"].split("::")[-1]
        print(f"  {colored_score}{padding}{b} {pf}{pf_pad}{duration:<8} {short_id}")
        print(f"  {' ' * 40} {DIM}{run_trace}{RESET}")

    print(f"{BOLD}{'=' * 70}{RESET}\n")


if __name__ == "__main__":
    main()
