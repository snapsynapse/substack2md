# Contributing to substack2md

This is a small personal archival tool with a maintenance-only contribution scope. Contributions should address correctness, security, dependency or browser compatibility, regression coverage, or documentation. New platforms, formats, and UI features are outside the current scope. See [docs/MAINTENANCE.md](docs/MAINTENANCE.md).

## Local checks

Create and activate an isolated environment, then install the development dependencies declared in `pyproject.toml`. Use its pinned Ruff version, which is also used in CI.
Literal
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest tests/ -v --tb=short
python -m ruff check substack2md tests scripts
python -m ruff format --check substack2md tests scripts
git diff --check
```
The offline suite must pass without a browser or credentials. The live API check is opt-in; the exact test count changes as regressions are added.

The following command contacts Substack's public API. An unavailable endpoint must be distinguished from verified API compatibility; a skipped test is not live verification.
Literal
```bash
SUBSTACK2MD_LIVE=1 python -m pytest tests/test_live_smoke.py -v -s
```
## PR guidelines

- Keep changes focused and include the problem, resulting behavior, and validation in the description.
- Use [Conventional Commits](https://conventionalcommits.org/) titles such as `fix:`, `docs:`, `ci:`, or `test:`.
- Update `README.md` and `CHANGELOG.md` when behavior changes. Keep website and machine-readable descriptions accurate, and identify unreleased behavior explicitly.
- Cover externally visible behavior with meaningful tests. Use synthetic or suitably licensed public HTML fixtures and mocked HTTP/CDP responses for deterministic regression coverage.
- Identify network access and side effects in the PR description. Do not include private URLs, cookies, or captured subscriber content in fixtures or logs.
- If install, dependency, test, lint, or local setup instructions change, update `.well-known/assistant-guide.txt`, `assistant-guide.txt`, and `docs/.well-known/assistant-guide.txt` together. Regenerate the root and Pages guide manifests, then run `tests/test_assistant_guide.py`.
- Follow the signing and publication gates in [docs/MAINTENANCE.md](docs/MAINTENANCE.md). Historical public tags are not rewritten merely to add signatures.

## Style

- Use four-space indentation and the configured Ruff formatting.
- Add type hints where they clarify public interfaces and outcomes.
- Use `logging` for diagnostics. Reserve direct console output for intentional CLI summaries and boot-time errors.
- Avoid em dashes in generated Markdown, CLI help, and documentation.

## Code of conduct

Be kind and assume good faith. Small documentation corrections, reproducible bug reports, and platform compatibility evidence are welcome.
