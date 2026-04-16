"""
Concurrency tests:
- StateFile is thread-safe under parallel record() calls.
- Per-host serialization logic (exercised indirectly via StateFile
  concurrent writes simulating the pool).
"""

import threading
from concurrent.futures import ThreadPoolExecutor

import substack2md


def test_statefile_parallel_record_is_consistent(tmp_path):
    sf = substack2md.StateFile(tmp_path)
    urls = [f"https://pub.substack.com/p/post-{i}" for i in range(200)]

    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(sf.record, urls))

    # All 200 URLs should be recorded, no corruption
    path = tmp_path / ".substack2md-state"
    lines = [l for l in path.read_text().splitlines() if l]
    assert len(lines) == 200
    assert len(set(lines)) == 200


def test_statefile_parallel_dup_record_dedups(tmp_path):
    sf = substack2md.StateFile(tmp_path)
    url = "https://pub.substack.com/p/hot-post"

    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(sf.record, [url] * 100))

    path = tmp_path / ".substack2md-state"
    lines = [l for l in path.read_text().splitlines() if l]
    # Exactly one entry despite 100 concurrent attempts
    assert lines == [url]


def test_statefile_load_is_idempotent_under_race(tmp_path):
    """contains() called from many threads simultaneously must not
    double-load or crash."""
    # Pre-seed the file
    (tmp_path / ".substack2md-state").write_text(
        "https://pub.substack.com/p/foo\nhttps://pub.substack.com/p/bar\n"
    )
    sf = substack2md.StateFile(tmp_path)

    results = []

    def check():
        results.append(sf.contains("https://pub.substack.com/p/foo"))

    threads = [threading.Thread(target=check) for _ in range(32)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(results)
    assert len(results) == 32
