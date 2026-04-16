"""
Evals for fetch_paywall_status() introduced in PR #1
(feat: --detect-paywall, branch drewid74:feat/paywall-detection).

These tests map to concrete merge-blocking questions:

  A. Audience decoding correctness
     - "only_paid"  -> is_paid True
     - "everyone"   -> is_paid False
     - "only_free"  -> is_paid False
     - "founding"   -> is_paid ??  (SUSPECTED BUG: currently returns False;
                                   founding-tier posts are paywalled in
                                   practice, so tagging them is_paid=False
                                   would defeat the feature's stated goal
                                   of "avoid accidentally sharing paid
                                   content".)

  B. Unknown / missing audience field
     - 200 OK but no audience key  -> current code defaults audience to
       "everyone" and is_paid to False.  That silently claims the post is
       free when we actually don't know.  Expected behavior per the PR
       description ("graceful fallback to null") would be is_paid=None,
       audience=None when the signal is absent.

  C. Graceful-failure contract
     - 404 / 500 / timeout / non-JSON body -> is_paid=None, audience=None
     - Never raises; never blocks the pipeline.

  D. Request shape
     - Hits https://{publication}.substack.com/api/v1/posts/{slug}
     - Sends Accept: application/json and a User-Agent
     - Has a finite timeout (the PR hardcodes 10s -- flagged below)

Run:
    pip install pytest responses
    pytest tests/test_paywall_fetch.py -v
"""
import json
import pytest

pytest.importorskip("responses")
import responses
from responses import matchers

import substack2md


PUB = "examplepub"
SLUG = "some-post"
API_URL = f"https://{PUB}.substack.com/api/v1/posts/{SLUG}"


# ---------------------------------------------------------------------------
# A. Audience decoding
# ---------------------------------------------------------------------------

@responses.activate
def test_only_paid_marks_is_paid_true():
    responses.add(responses.GET, API_URL,
                  json={"audience": "only_paid"}, status=200)
    out = substack2md.fetch_paywall_status(PUB, SLUG)
    assert out["is_paid"] is True
    assert out["audience"] == "only_paid"


@responses.activate
def test_everyone_marks_is_paid_false():
    responses.add(responses.GET, API_URL,
                  json={"audience": "everyone"}, status=200)
    out = substack2md.fetch_paywall_status(PUB, SLUG)
    assert out["is_paid"] is False
    assert out["audience"] == "everyone"


@responses.activate
def test_only_free_marks_is_paid_false():
    # Substack uses "only_free" for free-subscribers-only posts.
    # These aren't "paid" but they ARE gated (require a free subscription).
    # Worth deciding: should is_paid reflect "gated" or strictly "$$"?
    # Current code returns False.  Test documents current behavior.
    responses.add(responses.GET, API_URL,
                  json={"audience": "only_free"}, status=200)
    out = substack2md.fetch_paywall_status(PUB, SLUG)
    assert out["audience"] == "only_free"
    assert out["is_paid"] is False, (
        "Current impl: is_paid strictly means paywalled. "
        "Consider whether only_free subscribers-only should also be flagged."
    )


@responses.activate
def test_founding_tier_is_paid_behavior():
    """
    Substack also exposes 'founding' audience for founding-member-only posts.
    These ARE paid.  Current impl returns is_paid=False because it only
    matches 'only_paid' exactly.  This test will FAIL against the current
    PR -- that is the point.  If maintainers agree it's a bug, fix by
    widening the check, e.g.:

        paid_audiences = {"only_paid", "founding"}
        result["is_paid"] = data.get("audience") in paid_audiences
    """
    responses.add(responses.GET, API_URL,
                  json={"audience": "founding"}, status=200)
    out = substack2md.fetch_paywall_status(PUB, SLUG)
    assert out["audience"] == "founding"
    assert out["is_paid"] is True, (
        "Founding-tier posts are paywalled. "
        "Current PR misclassifies them as free -- likely needs fix before merge."
    )


# ---------------------------------------------------------------------------
# B. Missing / unknown audience key
# ---------------------------------------------------------------------------

@responses.activate
def test_missing_audience_key_should_return_unknown():
    """
    PR description promises 'graceful fallback to null on API errors'.
    When the API returns 200 but without the audience field, we also
    don't know the status.  Current impl defaults audience='everyone'
    and is_paid=False, which is a false negative.

    Expected: both fields None so downstream code can treat it as
    'not checked' and avoid drawing conclusions.
    """
    responses.add(responses.GET, API_URL, json={"title": "no audience key"},
                  status=200)
    out = substack2md.fetch_paywall_status(PUB, SLUG)
    assert out["is_paid"] is None, (
        "Missing 'audience' field should yield None, not False. "
        "Current PR defaults to False -> will tag posts as free when status "
        "is actually unknown."
    )
    assert out["audience"] is None


@responses.activate
def test_unknown_audience_value_leaves_is_paid_unknown():
    """
    Future-proofing: Substack may add new audience tiers (e.g. only_trial,
    only_gift).  Since the point of is_paid is to avoid leaking paid
    content, misclassifying an unknown tier as free is the dangerous
    failure mode.  Contract: preserve the raw audience string so the
    frontmatter still carries a debuggable signal, but set is_paid=None
    so downstream treats it as "status unknown, handle with care".
    """
    responses.add(responses.GET, API_URL,
                  json={"audience": "some_future_tier"}, status=200)
    out = substack2md.fetch_paywall_status(PUB, SLUG)
    assert out["audience"] == "some_future_tier"
    assert out["is_paid"] is None, (
        "Unknown audience values must not be silently classified as free. "
        "Return is_paid=None so callers can detect 'unknown' vs 'free'."
    )


# ---------------------------------------------------------------------------
# C. Graceful failure
# ---------------------------------------------------------------------------

@responses.activate
def test_404_returns_none_none():
    responses.add(responses.GET, API_URL, status=404)
    out = substack2md.fetch_paywall_status(PUB, SLUG)
    assert out == {"is_paid": None, "audience": None}


@responses.activate
def test_500_returns_none_none():
    responses.add(responses.GET, API_URL, status=500)
    out = substack2md.fetch_paywall_status(PUB, SLUG)
    assert out == {"is_paid": None, "audience": None}


@responses.activate
def test_non_json_body_returns_none_none():
    responses.add(responses.GET, API_URL, body="<html>cloudflare</html>",
                  status=200, content_type="text/html")
    out = substack2md.fetch_paywall_status(PUB, SLUG)
    assert out == {"is_paid": None, "audience": None}


@responses.activate
def test_connection_error_returns_none_none():
    # No stub registered -> responses raises ConnectionError, caught inside.
    responses.add(responses.GET, API_URL,
                  body=ConnectionError("boom"))
    out = substack2md.fetch_paywall_status(PUB, SLUG)
    assert out == {"is_paid": None, "audience": None}


def test_never_raises_on_network_failure(monkeypatch):
    """Even if requests.get itself blows up, caller must not see an exception."""
    def boom(*args, **kwargs):
        raise RuntimeError("unexpected transport failure")
    monkeypatch.setattr(substack2md.requests, "get", boom)
    out = substack2md.fetch_paywall_status(PUB, SLUG)
    assert out == {"is_paid": None, "audience": None}


# ---------------------------------------------------------------------------
# D. Request shape
# ---------------------------------------------------------------------------

@responses.activate
def test_request_url_shape():
    responses.add(responses.GET, API_URL,
                  json={"audience": "everyone"}, status=200)
    substack2md.fetch_paywall_status(PUB, SLUG)
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == API_URL


@responses.activate
def test_sends_accept_and_user_agent_headers():
    responses.add(
        responses.GET, API_URL,
        json={"audience": "everyone"}, status=200,
        match=[matchers.header_matcher({"Accept": "application/json"})],
    )
    substack2md.fetch_paywall_status(PUB, SLUG)
    req = responses.calls[0].request
    assert "User-Agent" in req.headers
    assert req.headers["User-Agent"]  # non-empty


def test_timeout_is_finite(monkeypatch):
    """
    Sanity check: a timeout is passed to requests.get.  The PR hardcodes 10s
    and ignores the --timeout CLI flag.  Consider threading --timeout
    through to fetch_paywall_status before merge so a single slow API call
    can't stall a large batch.
    """
    seen = {}

    def fake_get(url, headers=None, timeout=None):
        seen["timeout"] = timeout

        class R:
            status_code = 200
            def json(self_inner):
                return {"audience": "everyone"}
        return R()

    monkeypatch.setattr(substack2md.requests, "get", fake_get)
    substack2md.fetch_paywall_status(PUB, SLUG)
    assert seen["timeout"] is not None
    assert seen["timeout"] > 0
    assert seen["timeout"] < 120  # finite-and-reasonable
