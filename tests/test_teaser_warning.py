"""
Pins the teaser-warning behavior:

- When --detect-paywall reports is_paid=True AND the extracted body is
  shorter than TEASER_WORD_THRESHOLD, substack2md emits a WARNING log
  line advising the user that they may have only captured a teaser.

- When is_paid is False or None, no warning (we can't distinguish a
  short free post from a truncated paid one).

- When the body is long, no warning regardless of is_paid.
"""

import logging
from pathlib import Path

import pytest

import substack2md


@pytest.fixture
def fake_cdp_short_body(monkeypatch):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def fetch_html(self, url):
            return """
            <html><head><title>Hi</title>
              <meta name="author" content="A. Writer">
            </head><body>
              <h1>Hi</h1>
              <article><p>Short teaser text only.</p></article>
            </body></html>
            """

    monkeypatch.setattr(substack2md, "CDPClient", FakeClient)


@pytest.fixture
def fake_cdp_long_body(monkeypatch):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def fetch_html(self, url):
            long_body = "word " * 500
            return f"""
            <html><head><title>Hi</title>
              <meta name="author" content="A. Writer">
            </head><body>
              <h1>Hi</h1>
              <article><p>{long_body}</p></article>
            </body></html>
            """

    monkeypatch.setattr(substack2md, "CDPClient", FakeClient)


def _run(monkeypatch, tmp_path, is_paid, audience):
    def spy(pub, slug, timeout=10.0):
        return {"is_paid": is_paid, "audience": audience}

    monkeypatch.setattr(substack2md, "fetch_paywall_status", spy)
    return substack2md.process_url(
        "https://examplepub.substack.com/p/hello",
        base_dir=tmp_path,
        pub_mappings={},
        also_save_html=False,
        overwrite=True,
        cdp_host="x",
        cdp_port=0,
        timeout=1,
        retries=1,
        detect_paywall=True,
    )


def test_short_paid_body_emits_warning(caplog, monkeypatch, tmp_path, fake_cdp_short_body):
    with caplog.at_level(logging.WARNING, logger="substack2md"):
        _run(monkeypatch, tmp_path, is_paid=True, audience="only_paid")
    assert any("teaser suspected" in rec.message for rec in caplog.records), (
        "Expected a teaser warning when paid + short body"
    )


def test_short_free_body_no_warning(caplog, monkeypatch, tmp_path, fake_cdp_short_body):
    with caplog.at_level(logging.WARNING, logger="substack2md"):
        _run(monkeypatch, tmp_path, is_paid=False, audience="everyone")
    assert not any("teaser suspected" in rec.message for rec in caplog.records)


def test_unknown_paywall_status_no_warning(caplog, monkeypatch, tmp_path, fake_cdp_short_body):
    # is_paid=None (API failed) -- can't conclude teaser
    with caplog.at_level(logging.WARNING, logger="substack2md"):
        _run(monkeypatch, tmp_path, is_paid=None, audience=None)
    assert not any("teaser suspected" in rec.message for rec in caplog.records)


def test_long_paid_body_no_warning(caplog, monkeypatch, tmp_path, fake_cdp_long_body):
    with caplog.at_level(logging.WARNING, logger="substack2md"):
        _run(monkeypatch, tmp_path, is_paid=True, audience="only_paid")
    assert not any("teaser suspected" in rec.message for rec in caplog.records), (
        "Long body from a paid browser session should not warn"
    )
