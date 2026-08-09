"""Concurrency tests for the thread-safe :class:`gui.state.ServerState`."""

from __future__ import annotations

import threading

from gui.state import ServerState


def test_concurrent_increment_and_update_stay_consistent():
    state = ServerState()
    state.running = True

    n_threads = 12
    increments_per_thread = 50

    def worker(idx: int) -> None:
        for _ in range(increments_per_thread):
            state.increment_requests()
            state.update(device_count=idx + 1, adb_available=True)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    snap = state.snapshot()

    # Every increment must be accounted for (no lost updates under the lock).
    assert snap["request_count"] == n_threads * increments_per_thread
    # Last writer wins but the value must be one of the valid writes.
    assert snap["device_count"] in range(1, n_threads + 1)
    assert snap["adb_available"] is True
    assert snap["running"] is True


def test_snapshot_returns_independent_copy():
    state = ServerState()
    state.log_lines.append("a")

    snap = state.snapshot()
    snap["log_lines"].append("b")  # mutate the copy

    # The original shared state must be untouched (deep enough for the list).
    assert len(state.log_lines) == 1
    assert len(state.snapshot()["log_lines"]) == 1


def test_update_ignores_unknown_keys():
    state = ServerState()
    state.update(not_a_field=123, running=True)
    snap = state.snapshot()
    assert snap["running"] is True
    assert not hasattr(state, "not_a_field")
