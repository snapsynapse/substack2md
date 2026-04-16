# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_Nothing yet._

## [2.0.0] - 2026-04-16

Major release. Restructures the project from a single-file script into an installable package with a console entry point, ships a much larger feature set, and tightens every user-facing surface. All Python-level library imports (`import substack2md; substack2md.fetch_paywall_status(...)`) remain backward compatible.

### Breaking changes

- **Removed the flat `substack2md.py` file.** Invocation has moved from `python substack2md.py URL` to the installed console script `substack2md URL` (or `python -m substack2md URL`). After `pip install .` the CLI is on your PATH.
- **Removed `requirements.txt` and `tests/requirements-dev.txt`.** `pyproject.toml` is now the single source of truth for dependencies. Use `pip install .` or `pip install -e ".[dev]"` instead.

### Migration

| v1.x | v2.0.0 |
|-|-|
| `git clone && pip install -r requirements.txt` | `git clone && pip install .` |
| `python substack2md.py URL` | `substack2md URL` |
| `python substack2md.py --urls-file urls.txt` | `substack2md --urls-file urls.txt` |
| `pip install -r tests/requirements-dev.txt` | `pip install -e ".[dev]"` |

### Added

- **`--detect-paywall` flag** (originally #1 from @drewid74): queries Substack's public `/api/v1/posts/{slug}` API to classify posts as free or subscriber-only. Writes `is_paid` and `audience` fields to YAML frontmatter. Opt-in, graceful fallback to `null` on API errors, no additional authentication required.
- **`--concurrency N` flag**: opt-in parallel processing. Defaults to 1 (sequential). Posts from the same publication are still serialized via per-host locks to avoid bot heuristics; parallelism is across different publications only.
- **Resume-from-interrupt**: every successfully written URL is appended to `<base-dir>/.substack2md-state`. Subsequent runs skip already-completed URLs before any network call. Pass `--no-resume` to disable. Clean `KeyboardInterrupt` handling reports progress before exit.
- **`--log-level {DEBUG,INFO,WARNING,ERROR}`, `--quiet`/`-q`, `--version` flags**. Diagnostics now flow through the `logging` module; `[ok]`/`[skip]` progress becomes `INFO`-level so `--quiet` can suppress them cleanly.
- **Teaser-warning detection**: when `--detect-paywall` reports a paid post and the extracted body is under 300 words, substack2md logs a warning that you may have only captured the teaser and need to authenticate in the CDP-connected browser.
- **Custom-domain Substack support**: publications with custom domains (e.g. stratechery.com) now route paywall API calls to their canonical `<pub>.substack.com` subdomain via the new `resolve_substack_canonical()` helper.
- **Richer tag extraction**: merges `<meta name="keywords">`, ld+json `keywords`, and ld+json `articleSection` before normalization, so posts get the author's real taxonomy instead of just `["substack"]`.
- **`--from-md` + `--detect-paywall`**: backfill paywall metadata on existing markdown archives without re-fetching HTML.
- **`launch-browser.sh`**: macOS helper that detects Brave or Chrome, isolates a dedicated CDP profile at `$HOME/.*-cdp-profile`, opens port 9222 on loopback, and verifies the endpoint before exiting.
- **CI via GitHub Actions**: `pytest` and `ruff` run on push and PR across Python 3.10, 3.11, 3.12, 3.13.
- **Test suite**: 58 tests covering audience decoding, HTTP failure modes, request shape, frontmatter serialization, CLI wiring, publication-slug edges, canonical resolution, tag extraction, teaser warning, resume state, and concurrency.
- **Docs**: `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, and `tests/EVALS.md`.

### Changed

- **Package layout**: `substack2md.py` → `substack2md/` package with `_core.py` (library), `cli.py` (pipeline + main), `_version.py` (single-source version), `__main__.py` (enables `python -m substack2md`).
- **`pyproject.toml`**: registers `substack2md` as a console script, declares runtime and dev dependencies, sets Python ≥ 3.10, wires the `ruff` lint/format config and the `pytest` config.
- **README**: rewritten installation and Quick Start for the package flow; full and current CLI reference; paywall section documents all four `audience` enum values; links to `launch-browser.sh` and `CONTRIBUTING.md`.
- **Logging**: `print(..., file=sys.stderr)` replaced with the `substack2md` logger. Formatter includes level + logger name so downstream aggregators can filter.
- **Code style**: full `ruff` format pass applied. 100-char soft limit, isort-sorted imports, modern type-hint syntax under `UP`.

### Fixed

- **Founding-tier posts** (`audience: founding`) are now correctly classified as `is_paid: true`. Previously matched only `only_paid` exactly, which silently leaked paid content as free.
- **Missing `audience` field** in a 200 response now returns `(is_paid=None, audience=None)` instead of defaulting to `"everyone"`/`False`. Matches the documented null-on-uncertainty contract.
- **Unknown audience values** (future Substack tiers) are preserved verbatim as `audience` but `is_paid` is left as `null` so downstream treats the post as "status unknown" rather than silently free.
- **`datetime.utcnow()` deprecation**: swapped for `datetime.now(timezone.utc)` so Python 3.12+ runs without `DeprecationWarning` and Python 3.14 (which removes `utcnow`) works.
- **CDP target leak**: `CDPClient.fetch_html` now wraps navigate/eval in `try/finally` so `Target.closeTarget` always runs, preventing tab-pool exhaustion during long batches.
- **`--timeout` not threaded through to paywall API**: the CLI `--timeout` value now reaches `fetch_paywall_status` instead of being hardcoded to 10s.

## [1.1.0] - prior

First tagged reference point. CDP-driven Substack-to-markdown converter with Obsidian wikilink rewriting, publication mapping, transcript cleanup, and batch URL file support.

[Unreleased]: https://github.com/snapsynapse/substack2md/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/snapsynapse/substack2md/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/snapsynapse/substack2md/releases/tag/v1.1.0
