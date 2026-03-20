"""
Flaky Test Detector - pytest plugin via conftest.py hooks.

Usage:
    pytest --flaky-runs=10 --flaky-report=flaky_report.json

Options:
    --flaky-runs   Number of times to run each test (default: 5)
    --flaky-report Path to JSON report output (default: flaky_report.json)
"""

import json
import time
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# CLI options
# ---------------------------------------------------------------------------

def pytest_addoption(parser):
    group = parser.getgroup("flaky-detector")
    group.addoption(
        "--flaky-runs",
        type=int,
        default=5,
        metavar="N",
        help="Run each test N times to detect flakiness (default: 5)",
    )
    group.addoption(
        "--flaky-report",
        default="flaky_report.json",
        metavar="PATH",
        help="Output path for the JSON flakiness report (default: flaky_report.json)",
    )


# ---------------------------------------------------------------------------
# State shared across the session
# ---------------------------------------------------------------------------

class FlakyTracker:
    def __init__(self, runs: int):
        self.runs = runs
        # nodeid -> list of "passed" | "failed" | "error" | "skipped"
        self.results: dict[str, list[str]] = defaultdict(list)
        # nodeid -> list of durations (seconds)
        self.durations: dict[str, list[float]] = defaultdict(list)
        self._start: dict[str, float] = {}

    def record_start(self, nodeid: str):
        self._start[nodeid] = time.perf_counter()

    def record_outcome(self, nodeid: str, outcome: str):
        elapsed = time.perf_counter() - self._start.pop(nodeid, 0.0)
        self.results[nodeid].append(outcome)
        self.durations[nodeid].append(round(elapsed, 4))

    def flakiness_score(self, nodeid: str) -> float:
        """
        Score in [0.0, 1.0].
        0.0 = perfectly stable (always same outcome).
        1.0 = maximally flaky (alternates every run).

        Formula: transitions / (n - 1), where a transition is any run
        whose outcome differs from the previous run.
        """
        outcomes = self.results[nodeid]
        n = len(outcomes)
        if n < 2:
            return 0.0
        transitions = sum(
            1 for i in range(1, n) if outcomes[i] != outcomes[i - 1]
        )
        return round(transitions / (n - 1), 4)

    def report(self) -> dict:
        tests = []
        for nodeid, outcomes in self.results.items():
            unique = set(outcomes)
            passes = outcomes.count("passed")
            failures = outcomes.count("failed") + outcomes.count("error")
            skips = outcomes.count("skipped")
            score = self.flakiness_score(nodeid)
            durations = self.durations[nodeid]

            tests.append({
                "nodeid": nodeid,
                "runs": len(outcomes),
                "outcomes": outcomes,
                "passes": passes,
                "failures": failures,
                "skips": skips,
                "flakiness_score": score,
                "is_flaky": score > 0.0,
                "avg_duration_s": round(sum(durations) / len(durations), 4) if durations else 0,
            })

        tests.sort(key=lambda t: t["flakiness_score"], reverse=True)

        flaky = [t for t in tests if t["is_flaky"]]
        stable = [t for t in tests if not t["is_flaky"]]

        return {
            "summary": {
                "total_tests": len(tests),
                "flaky_tests": len(flaky),
                "stable_tests": len(stable),
                "runs_per_test": self.runs,
            },
            "tests": tests,
        }


# ---------------------------------------------------------------------------
# Plugin hooks
# ---------------------------------------------------------------------------

class FlakyPlugin:
    def __init__(self, tracker: FlakyTracker, runs: int):
        self.tracker = tracker
        self.runs = runs

    # Re-run each test item `runs` times by re-inserting it into the queue.
    def pytest_collection_modifyitems(self, session, config, items):  # noqa: ARG002
        expanded = []
        for item in items:
            for _ in range(self.runs):
                expanded.append(item)
        items[:] = expanded

    def pytest_runtest_logstart(self, nodeid, location):  # noqa: ARG002
        self.tracker.record_start(nodeid)

    def pytest_runtest_logreport(self, report):
        if report.when != "call":
            # Only care about the actual test call, not setup/teardown.
            # But capture setup errors too.
            if report.when == "setup" and report.failed:
                self.tracker.record_outcome(report.nodeid, "error")
            return

        if report.passed:
            outcome = "passed"
        elif report.failed:
            outcome = "failed"
        elif report.skipped:
            outcome = "skipped"
        else:
            outcome = "unknown"

        self.tracker.record_outcome(report.nodeid, outcome)


# ---------------------------------------------------------------------------
# Session-level wiring
# ---------------------------------------------------------------------------

def pytest_configure(config):
    runs = config.getoption("--flaky-runs", default=5)
    if runs < 2:
        raise ValueError("--flaky-runs must be at least 2 (need 2+ runs to detect flakiness)")
    tracker = FlakyTracker(runs=runs)
    plugin = FlakyPlugin(tracker=tracker, runs=runs)
    config._flaky_tracker = tracker
    config.pluginmanager.register(plugin, "flaky_detector")


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    config = session.config
    tracker: FlakyTracker = getattr(config, "_flaky_tracker", None)
    if tracker is None:
        return

    report_data = tracker.report()
    report_path = Path(config.getoption("--flaky-report", default="flaky_report.json"))
    report_path.write_text(json.dumps(report_data, indent=2))

    # Print a quick summary to the terminal
    summary = report_data["summary"]
    tests = report_data["tests"]
    flaky = [t for t in tests if t["is_flaky"]]

    print("\n" + "=" * 60)
    print("  FLAKY TEST DETECTOR REPORT")
    print("=" * 60)
    print(f"  Runs per test : {summary['runs_per_test']}")
    print(f"  Total tests   : {summary['total_tests']}")
    print(f"  Flaky tests   : {summary['flaky_tests']}")
    print(f"  Stable tests  : {summary['stable_tests']}")
    print(f"  Report saved  : {report_path.resolve()}")

    if flaky:
        print("\n  Flaky tests (sorted by score):")
        for t in flaky:
            bar = _score_bar(t["flakiness_score"])
            print(
                f"    [{bar}] {t['flakiness_score']:.2f}  "
                f"{t['passes']}P/{t['failures']}F  "
                f"{t['nodeid']}"
            )
    else:
        print("\n  No flaky tests detected.")

    print("=" * 60 + "\n")


def _score_bar(score: float, width: int = 10) -> str:
    filled = round(score * width)
    return "#" * filled + "." * (width - filled)
