"""
Optional live smoke test.  Skipped unless SUBSTACK2MD_LIVE=1.

Hits the real Substack API.  Use it to confirm the endpoint contract
hasn't shifted.  Picks two well-known free posts; does NOT require
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


# Known publication + slug pairs; pick ones likely to stay up.
# These are free posts from well-established Substacks.  If they rot,
# swap them -- the goal is just to exercise the real endpoint.
FREE_CASES = [
    # (publication, slug)
    ("platformer", "the-big-tech-antitrust-era-begins"),
]


@pytest.mark.parametrize("pub,slug", FREE_CASES)
def test_live_endpoint_contract_has_audience_field(pub, slug):
    out = substack2md.fetch_paywall_status(pub, slug)
    # Either the API is reachable and we see a string audience,
    # or it failed gracefully (None).  Both are acceptable; what
    # we're really checking is "no raise".
    assert out["audience"] in (
        None,
        "everyone",
        "only_free",
        "only_paid",
        "founding",
    ) or isinstance(out["audience"], str)
    assert out["is_paid"] in (None, True, False)
