"""
Optional live smoke test.  Skipped unless SUBSTACK2MD_LIVE=1.

Hits the real Substack API.  Use it to confirm the endpoint contract
hasn't shifted.  Checks a public post; does NOT require
an authenticated session.

Run:
    SUBSTACK2MD_LIVE=1 pytest tests/test_live_smoke.py -v -s
"""

import os

import pytest

import substack2md

pytestmark = pytest.mark.skipif(
    os.getenv("SUBSTACK2MD_LIVE") != "1",
    reason="Live network tests disabled. Set SUBSTACK2MD_LIVE=1 to enable.",
)


# A public post from the maintainer's publication, verified September 5, 2026.
# If it moves, replace the fixture after checking the public archive.
FREE_CASES = [
    # (publication, slug)
    ("sigsub", "good-enough-for-agentic-work"),
]


@pytest.mark.parametrize("pub,slug", FREE_CASES)
def test_live_endpoint_contract_has_audience_field(pub, slug):
    out = substack2md.fetch_paywall_status(pub, slug)
    assert isinstance(out["audience"], str) and out["audience"].strip(), (
        f"Could not verify the live API contract for {pub}/{slug}: "
        "the endpoint was unavailable or returned no audience. "
        "Check connectivity and whether the fixture post still exists."
    )
    assert isinstance(out["is_paid"], bool), (
        f"Unrecognized live audience {out['audience']!r}; update audience handling "
        "only after verifying the current API contract."
    )
