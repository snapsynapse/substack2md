# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CI: GitHub Actions workflow running `pytest tests/` on push and pull request across Python 3.10, 3.11, 3.12, 3.13.
- `CONTRIBUTING.md` with local dev setup, PR guidelines, and test instructions.
- `CHANGELOG.md` (this file).

### Changed
- Centralized the version string into a single `__version__` module constant. All `source:` frontmatter lines now derive from it instead of three hardcoded copies.
- README: documented all four known Substack `audience` enum values (`everyone`, `only_free`, `only_paid`, `founding`) and the "unknown tier -> `is_paid=null`" contract.
- README: fixed placeholder clone URL (`yourusername` -> `snapsynapse`).

### Fixed
- Replaced deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)` so Python 3.12+ runs without `DeprecationWarning` and Python 3.14 (which removes `utcnow`) still works.

## [1.2.0] - 2026-04-16

### Added
- `--detect-paywall` CLI flag (from #1, @drewid74): queries Substack's public `/api/v1/posts/{slug}` API to classify posts as free or subscriber-only. Adds `is_paid` (bool) and `audience` (str) to YAML frontmatter. Opt-in, graceful fallback to `null` on API errors, no additional authentication required.
- Test suite: 30 tests under `tests/` covering audience decoding, HTTP failure modes, request shape, frontmatter serialization, CLI wiring, and publication-slug edge cases. Opt-in live smoke test under `SUBSTACK2MD_LIVE=1`.
- `tests/EVALS.md` documenting the paywall-detection eval report.

### Fixed
- Founding-tier posts (Substack `audience: founding`) are now correctly classified as `is_paid: true`. Previously matched only `only_paid` exactly, silently leaking paid content as free.
- Missing `audience` field in a 200 response now returns `(is_paid=None, audience=None)` instead of defaulting to `"everyone"/False`. Matches the docstring's null-on-uncertainty promise.
- Unknown audience values (future Substack tiers) are preserved verbatim as `audience` but `is_paid` is left as `null` so downstream workflows treat the post as "status unknown" rather than silently free.

## [1.1.0] - prior

First tagged reference point. CDP-driven Substack-to-markdown converter with Obsidian wikilink rewriting, publication mapping, transcript cleanup, and batch URL file support.
