# Flasky Test Detector

A pytest plugin that reruns each test N times and computes a **flakiness score** per test — no extra packages, no configuration files, just drop `conftest.py` into your project.

## Why

Flaky tests silently erode trust in your test suite. A test that passes 9 out of 10 times looks healthy in CI until it doesn't. This tool surfaces those tests by tracking outcome consistency across multiple runs and giving each test a score.

## How it works

1. Every test is collected and run N times (default: 5).
2. Each run's outcome (pass/fail/skip/error) is recorded with its duration.
3. After the session, a **flakiness score** is computed per test:

```
score = transitions / (N - 1)
```

A *transition* is any run whose outcome differs from the previous run.

| Score | Meaning |
|-------|---------|
| `0.00` | Perfectly stable — always the same outcome |
| `0.50` | Moderately flaky — alternates roughly half the time |
| `1.00` | Maximally flaky — outcome flips every single run |

Results are written to a JSON report and printed as a terminal summary.

## Usage

```bash
pip install pytest

# Run each test 10 times, output to report.json
pytest --flaky-runs=10 --flaky-report=report.json -v

# View the colorized report
python show_report.py report.json
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--flaky-runs` | `5` | Number of times to run each test |
| `--flaky-report` | `flaky_report.json` | Path to write the JSON report |

## Terminal output

```
============================================================
  FLAKY TEST DETECTOR REPORT
============================================================
  Runs per test : 10
  Total tests   : 8
  Flaky tests   : 4
  Stable tests  : 4
  Report saved  : /your/project/flaky_report.json

  Flaky tests (sorted by score):
    [##########] 1.00  5P/5F  test_random_50_50
    [######....] 0.57  8P/2F  test_random_80_pass
    [###.......] 0.29  1P/9F  test_random_10_pass
    [##........] 0.22  2P/8F  test_timing_sensitive
============================================================
```

## JSON report shape

```json
{
  "summary": {
    "total_tests": 8,
    "flaky_tests": 4,
    "stable_tests": 4,
    "runs_per_test": 10
  },
  "tests": [
    {
      "nodeid": "test_examples.py::test_random_50_50",
      "runs": 10,
      "outcomes": ["passed","failed","passed","failed","failed","passed","failed","passed","failed","passed"],
      "passes": 5,
      "failures": 5,
      "skips": 0,
      "flakiness_score": 0.89,
      "is_flaky": true,
      "avg_duration_s": 0.002
    }
  ]
}
```

## Files

| File | Purpose |
|------|---------|
| `conftest.py` | The pytest plugin — copy this into your project root |
| `test_examples.py` | Demo tests: stable, flaky, and timing-sensitive |
| `show_report.py` | Colorized terminal report viewer |
| `requirements.txt` | `pytest>=7.0` |

## Requirements

- Python 3.9+
- pytest 7.0+
