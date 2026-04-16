"""
Evals for the --detect-paywall CLI flag and its wiring through process_url.

Merge-blocking questions:

  C1. CLI parse: --detect-paywall is recognized; default is False.
  C2. Opt-in: without the flag, fetch_paywall_status is NEVER called.
      (Avoids unexpected network traffic for existing users.)
  C3. When flag is on, process_url calls fetch_paywall_status exactly once
      per URL, with the correct (publication, slug).
  C4. When the API call returns None/None (failure mode), the pipeline
      still succeeds -- the .md file is written.
  C5. --from-md path is unaffected (paywall detection is opt-in on the
      live-fetch path only).  This is a conscious scope choice; test
      pins it so future refactors don't silently break it.
"""

import sys
from pathlib import Path
from unittest import mock

import pytest

import substack2md

# --- C1: parser ------------------------------------------------------------


def test_cli_accepts_detect_paywall(monkeypatch, tmp_path):
    """Argparse must recognise --detect-paywall; default False."""
    # Drive main() far enough to hit argparse, then bail.
    called = {}

    def fake_process_url(
        url,
        base_dir,
        pub_mappings,
        also_save_html,
        overwrite,
        cdp_host,
        cdp_port,
        timeout,
        retries,
        detect_paywall=False,
    ):
        called["detect_paywall"] = detect_paywall
        return None

    monkeypatch.setattr(substack2md, "process_url", fake_process_url)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "substack2md.py",
            "https://examplepub.substack.com/p/hello",
            "--base-dir",
            str(tmp_path),
            "--detect-paywall",
        ],
    )
    substack2md.main()
    assert called.get("detect_paywall") is True


def test_cli_default_is_false(monkeypatch, tmp_path):
    called = {}

    def fake_process_url(
        url,
        base_dir,
        pub_mappings,
        also_save_html,
        overwrite,
        cdp_host,
        cdp_port,
        timeout,
        retries,
        detect_paywall=False,
    ):
        called["detect_paywall"] = detect_paywall
        return None

    monkeypatch.setattr(substack2md, "process_url", fake_process_url)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "substack2md.py",
            "https://examplepub.substack.com/p/hello",
            "--base-dir",
            str(tmp_path),
        ],
    )
    substack2md.main()
    assert called.get("detect_paywall") is False


# --- C2 / C3: wiring inside process_url -----------------------------------


@pytest.fixture
def fake_cdp(monkeypatch):
    """Stub CDPClient so process_url doesn't need a real browser."""

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def fetch_html(self, url):
            # Minimal HTML that extract_article_fields can parse.
            return """
            <html><head>
              <title>Hello</title>
              <meta name="author" content="A. Writer">
            </head><body>
              <h1>Hello</h1>
              <h3>Sub</h3>
              <article><p>Body text here with enough words to pass
              readability's heuristic threshold for article detection,
              padding padding padding padding padding padding padding.</p>
              </article>
            </body></html>
            """

    monkeypatch.setattr(substack2md, "CDPClient", FakeClient)
    return FakeClient


@pytest.fixture
def fake_cdp_custom_domain(monkeypatch):
    """A custom-domain Substack publication that embeds its canonical subdomain."""

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def fetch_html(self, url):
            return """
            <html><head>
              <title>Hello</title>
              <meta name="author" content="A. Writer">
              <link rel="canonical" href="https://realpub.substack.com/p/canonical-slug">
            </head><body>
              <h1>Hello</h1>
              <article><p>Body text here with enough words to pass
              readability's heuristic threshold, padding padding padding
              padding padding padding padding padding padding padding.</p>
              </article>
            </body></html>
            """

    monkeypatch.setattr(substack2md, "CDPClient", FakeClient)
    return FakeClient


def test_paywall_not_called_when_flag_off(monkeypatch, tmp_path, fake_cdp):
    called = {"count": 0}

    def spy(*args, **kwargs):
        called["count"] += 1
        return {"is_paid": None, "audience": None}

    monkeypatch.setattr(substack2md, "fetch_paywall_status", spy)
    substack2md.process_url(
        "https://examplepub.substack.com/p/hello",
        base_dir=tmp_path,
        pub_mappings={},
        also_save_html=False,
        overwrite=True,
        cdp_host="x",
        cdp_port=0,
        timeout=1,
        retries=1,
        detect_paywall=False,
    )
    assert called["count"] == 0, "No network call without the flag"


def test_paywall_called_once_with_correct_args(monkeypatch, tmp_path, fake_cdp):
    seen = []

    def spy(publication, slug, timeout=10.0):
        seen.append((publication, slug, timeout))
        return {"is_paid": True, "audience": "only_paid"}

    monkeypatch.setattr(substack2md, "fetch_paywall_status", spy)
    out = substack2md.process_url(
        "https://examplepub.substack.com/p/hello",
        base_dir=tmp_path,
        pub_mappings={},
        also_save_html=False,
        overwrite=True,
        cdp_host="x",
        cdp_port=0,
        timeout=7,
        retries=1,
        detect_paywall=True,
    )
    assert len(seen) == 1
    pub, slug, timeout = seen[0]
    assert pub == "examplepub"
    assert slug == "hello"
    # CLI --timeout should thread through to the paywall HTTP call
    assert timeout == 7
    assert out is not None and Path(out).exists()
    # Produced file carries the paywall fields
    text = Path(out).read_text()
    assert "is_paid: true" in text
    assert "audience: only_paid" in text


# --- Custom-domain canonical resolution ------------------------------------


def test_custom_domain_uses_canonical_substack_subdomain(
    monkeypatch, tmp_path, fake_cdp_custom_domain
):
    """
    When the input URL is a custom domain but the page's canonical link
    points to `<pub>.substack.com/p/<slug>`, the paywall call must hit
    the canonical subdomain, not the netloc-derived prefix.
    """
    seen = []

    def spy(publication, slug, timeout=10.0):
        seen.append((publication, slug))
        return {"is_paid": True, "audience": "only_paid"}

    monkeypatch.setattr(substack2md, "fetch_paywall_status", spy)
    out = substack2md.process_url(
        "https://custom-domain.example.com/2026/some-post",
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
    assert out is not None
    assert len(seen) == 1
    pub, slug = seen[0]
    # Canonical resolver should have overridden the netloc-derived values
    assert pub == "realpub"
    assert slug == "canonical-slug"


# --- C4: API failure must not kill the pipeline ---------------------------


def test_api_failure_still_writes_file(monkeypatch, tmp_path, fake_cdp):
    def failing(pub, slug, timeout=10.0):
        return {"is_paid": None, "audience": None}

    monkeypatch.setattr(substack2md, "fetch_paywall_status", failing)
    out = substack2md.process_url(
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
    assert out is not None and Path(out).exists()
    text = Path(out).read_text()
    # None-valued keys should be filtered out of frontmatter
    assert "is_paid" not in text
    assert "audience" not in text


# --- C5: --from-md path unchanged -----------------------------------------


def test_from_md_path_default_has_no_paywall_fields(tmp_path):
    """Without detect_paywall, --from-md still does no network call."""
    src = tmp_path / "raw.md"
    src.write_text("# Some Title\n\nBody.\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    out = substack2md.process_from_md(
        src,
        base_dir=out_dir,
        pub_mappings={},
        url="https://examplepub.substack.com/p/hello",
        overwrite=True,
    )
    assert out is not None and Path(out).exists()
    text = Path(out).read_text()
    assert "is_paid" not in text
    assert "audience" not in text


def test_from_md_path_with_paywall_enabled(monkeypatch, tmp_path):
    """--from-md + detect_paywall=True calls fetch_paywall_status and tags the output."""
    src = tmp_path / "raw.md"
    src.write_text("# Some Title\n\nBody.\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    calls = []

    def spy(pub, slug, timeout=10.0):
        calls.append((pub, slug, timeout))
        return {"is_paid": True, "audience": "only_paid"}

    monkeypatch.setattr(substack2md, "fetch_paywall_status", spy)
    out = substack2md.process_from_md(
        src,
        base_dir=out_dir,
        pub_mappings={},
        url="https://examplepub.substack.com/p/hello",
        overwrite=True,
        detect_paywall=True,
        paywall_timeout=8,
    )
    assert out is not None and Path(out).exists()
    assert calls == [("examplepub", "hello", 8)]
    text = Path(out).read_text()
    assert "is_paid: true" in text
    assert "audience: only_paid" in text
