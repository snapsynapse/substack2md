# Contributing to substack2md

Thanks for your interest. A few conventions that keep the repo easy to maintain.

## Before you open a PR

1. Install in editable mode with dev extras and run the test suite locally:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   pytest tests/ -v
   ```
   Expect 50+ passed, 1 skipped (the live smoke test is opt-in via `SUBSTACK2MD_LIVE=1`).

2. Before pushing, run the linter the way CI does:
   ```bash
   ruff check substack2md tests
   ruff format --check substack2md tests
   ```

2. If you changed behavior that users see, update `README.md` and `CHANGELOG.md` in the same PR.

3. If you added a new CLI flag, new frontmatter field, or changed the shape of any public function, add a test covering the new behavior.

## PR guidelines

- Keep PRs focused. One concern per PR beats one giant PR.
- Title in [Conventional Commits](https://www.conventionalcommits.org/) style: `feat:`, `fix:`, `refactor:`, `docs:`, `ci:`, `test:`, etc.
- PR description should answer: what problem does this solve, what changed, how did you test it.
- If your PR introduces network or side-effect code, flag it in the description so reviewers know to look closely.

## Style

- Follow existing code style. Indent is 4 spaces.
- Type hints on new function signatures are encouraged but not strictly required yet.
- Use the `logging` module for diagnostics. The module-level `log` object in `substack2md._core` is the shared logger; reserve `print()` for boot-time errors that happen before logging is configured.
- Run `ruff check` and `ruff format` before pushing; CI enforces both.
- No em dashes in user-facing strings (markdown output, CLI help, README, docs).

## Tests

Tests live in `tests/`. The suite uses `pytest` plus the [`responses`](https://github.com/getsentry/responses) library for HTTP mocking. A Chrome/Brave CDP session is **not** required to run tests; CDP is stubbed out in the CLI wiring tests.

To run just the unit tests:
```bash
pytest tests/ -v
```

To run the optional live smoke test (hits Substack's real API):
```bash
SUBSTACK2MD_LIVE=1 pytest tests/test_live_smoke.py -v -s
```

## Code of conduct

Be kind. Assume good faith. This is a small personal-archival tool; the bar is functionality, not ceremony.

## Where to start

Check the issues list for ideas, or look at the `## Contributing` section of the README for areas that could use help. Small docs fixes, edge-case test additions, and platform-specific troubleshooting notes are always welcome.
