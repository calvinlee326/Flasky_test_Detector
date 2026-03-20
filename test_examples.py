"""
Example tests with varying degrees of flakiness.
Run with: pytest --flaky-runs=10 -v
"""

import random
import time

import pytest


# ---------------------------------------------------------------------------
# Stable tests (always pass or always fail)
# ---------------------------------------------------------------------------

def test_always_passes():
    assert 1 + 1 == 2


def test_always_fails():
    # Intentionally broken — stable failure, not flaky.
    assert 1 == 2, "this always fails"


def test_pure_computation():
    result = sorted([3, 1, 2])
    assert result == [1, 2, 3]


# ---------------------------------------------------------------------------
# Flaky tests (outcome depends on randomness / timing)
# ---------------------------------------------------------------------------

def test_random_50_50():
    """Fails ~50% of the time — maximally flaky."""
    assert random.random() > 0.5


def test_random_80_pass():
    """Fails ~20% of the time — mildly flaky."""
    assert random.random() > 0.2


def test_random_10_pass():
    """Fails ~90% of the time — mostly fails but occasionally passes."""
    assert random.random() > 0.9


def test_timing_sensitive():
    """
    Simulates a race condition: sleeps a random amount then checks
    if elapsed time is within a tight window — flaky by design.
    """
    start = time.perf_counter()
    time.sleep(random.uniform(0.001, 0.020))
    elapsed_ms = (time.perf_counter() - start) * 1000
    # Passes only if the sleep happened to be short enough
    assert elapsed_ms < 10, f"took {elapsed_ms:.1f}ms (expected < 10ms)"


def test_order_dependent():
    """
    Relies on dict ordering staying stable across CPython runs — stable
    in CPython 3.7+ but included as an example of a test that *could*
    be flaky on older interpreters.
    """
    d = {"a": 1, "b": 2, "c": 3}
    assert list(d.keys()) == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# Skipped test
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="not implemented yet")
def test_future_feature():
    assert False
