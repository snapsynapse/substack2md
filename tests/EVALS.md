# PR #1 Eval Report — `feat: --detect-paywall`

Target: https://github.com/snapsynapse/substack2md/pull/1
Source branch: drewid74:feat/paywall-detection
Base: snapsynapse:main

## How to run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r tests/requirements-dev.txt

# Fetch PR code into a local checkout
git remote add drew https://github.com/drewid74/substack2md.git
git fetch drew feat/paywall-detection
git checkout drew/feat/paywall-detection -- substack2md.py

pytest tests/ -v
# Optional live:
SUBSTACK2MD_LIVE=1 pytest tests/test_live_smoke.py -v -s
```

## Result against PR HEAD

28 passed, 2 failed, 1 skipped (live smoke, opt-in).

## Failures — merge-blockers to discuss with author

### BUG 1. Founding-tier posts misclassified as free

`test_founding_tier_is_paid_behavior` FAILS.

Substack audience values observed in the wild:
`everyone`, `only_free`, `only_paid`, `founding`.

Current code:
```python
result["is_paid"] = data.get("audience") == "only_paid"
```
`founding` posts (paid, founding-member-only) come through as
`is_paid=False`, `audience="founding"`. Defeats the PR's stated goal of
"avoid accidentally sharing paid content."

Proposed fix:
```python
PAID_AUDIENCES = {"only_paid", "founding"}
result["is_paid"] = data.get("audience") in PAID_AUDIENCES
```

### BUG 2. Missing `audience` key silently reported as "everyone"

`test_missing_audience_key_should_return_unknown` FAILS.

Current code:
```python
result["is_paid"]  = data.get("audience") == "only_paid"  # -> False when missing
result["audience"] = data.get("audience", "everyone")     # -> "everyone" when missing
```
If Substack ever returns a 200 without the `audience` field (schema
drift, cached response, edge account type), the post is tagged as free
when the actual status is unknown. Contradicts the PR's own promise of
"graceful fallback to null on API errors."

Proposed fix:
```python
audience = data.get("audience")
if audience is None:
    return {"is_paid": None, "audience": None}
result["audience"] = audience
result["is_paid"]  = audience in PAID_AUDIENCES
```

## Non-blocking observations (flag, don't block)

- Hardcoded 10s timeout — `--timeout` CLI arg is not threaded through
  to `fetch_paywall_status`. On a large batch a slow endpoint can add
  10s per URL. `test_timeout_is_finite` currently passes at 10s; bump
  the assertion upper bound or plumb the arg before merge if the
  maintainers care.
- Custom-domain Substacks (e.g. `stratechery.com`): `publication` slug
  is derived from the netloc, so the metadata API URL built from it
  will 404 for custom domains. Fails gracefully (is_paid=None) but the
  feature is silently inert for these. See
  `test_custom_domain_publication_is_wrong_for_api` — documents current
  behavior, passes by design.
- `--from-md` path does not support paywall detection. Opt-in and
  explicitly scoped; fine. Pinned by
  `test_from_md_path_has_no_paywall_fields`.
- No test suite shipped with the PR. Recommend adopting `tests/` and
  adding a CI step before merge.

## Coverage map

| Area                        | File                                 |
|-----------------------------|--------------------------------------|
| API contract + failure modes| test_paywall_fetch.py                |
| YAML frontmatter behavior   | test_frontmatter.py                  |
| CLI flag + process_url wiring| test_cli_wiring.py                  |
| Publication/slug derivation | test_publication_slug_edges.py       |
| Real endpoint smoke         | test_live_smoke.py (opt-in)          |

## Decision matrix

| Outcome                            | Action                                  |
|------------------------------------|-----------------------------------------|
| Author agrees on BUG 1 + BUG 2     | Request changes; merge after tests pass |
| Author disagrees, wants to ship    | Either adjust tests to pin current impl as intended, or reject PR |
| Author wants broader scope         | Add follow-up for custom-domain lookup + threading `--timeout` |
