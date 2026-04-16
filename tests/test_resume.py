"""
Resume-on-interrupt behavior:

- StateFile records cleaned URLs, one per line, at
  <base_dir>/.substack2md-state.
- On subsequent runs, URLs already in the state file are skipped before
  any network/CDP call happens.
- Missing state file is fine (treated as "nothing done yet").
- The file format is intentionally human-readable; deleting it forces a
  full re-run.
"""

from pathlib import Path

import substack2md


def test_statefile_records_and_rereads(tmp_path):
    sf = substack2md.StateFile(tmp_path)
    assert not sf.contains("https://pub.substack.com/p/foo")

    sf.record("https://pub.substack.com/p/foo")
    sf.record("https://pub.substack.com/p/bar")

    # Fresh instance reads the same file
    sf2 = substack2md.StateFile(tmp_path)
    assert sf2.contains("https://pub.substack.com/p/foo")
    assert sf2.contains("https://pub.substack.com/p/bar")
    assert not sf2.contains("https://pub.substack.com/p/baz")


def test_statefile_dedups(tmp_path):
    sf = substack2md.StateFile(tmp_path)
    sf.record("https://pub.substack.com/p/foo")
    sf.record("https://pub.substack.com/p/foo")  # duplicate

    path = tmp_path / ".substack2md-state"
    lines = [l for l in path.read_text().splitlines() if l]
    assert lines.count("https://pub.substack.com/p/foo") == 1


def test_statefile_cleans_query_strings(tmp_path):
    """record() uses cleanup_url, so ?utm_* garbage in the URL doesn't
    defeat the resume check on the next run."""
    sf = substack2md.StateFile(tmp_path)
    sf.record("https://pub.substack.com/p/foo?utm_source=email")
    assert sf.contains("https://pub.substack.com/p/foo")


def test_missing_state_file_treated_as_empty(tmp_path):
    """No .state file yet -- contains() must return False, not raise."""
    sf = substack2md.StateFile(tmp_path)
    assert not sf.contains("https://pub.substack.com/p/foo")


def test_statefile_format_is_one_url_per_line(tmp_path):
    sf = substack2md.StateFile(tmp_path)
    sf.record("https://pub.substack.com/p/foo")
    sf.record("https://pub.substack.com/p/bar")
    content = (tmp_path / ".substack2md-state").read_text()
    assert content == ("https://pub.substack.com/p/foo\nhttps://pub.substack.com/p/bar\n")
