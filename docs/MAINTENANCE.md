# Maintenance and release procedure

## Scope

This repository has a maintenance-only contribution scope. Publication status and immutable artifacts are recorded in [GitHub Releases](https://github.com/snapsynapse/substack2md/releases). The supported product remains a Python CLI for personal Substack archives using an authenticated CDP browser, plus cleanup of existing Markdown. Maintenance covers correctness, security, compatibility, regression tests, and documentation. Additional publishing platforms, export formats, and user interfaces are outside the current scope.

Maintenance readiness requires reliable capture and recovery, meaningful failure exit codes, clean installation from a built wheel, and agreement between documentation and behavior. Local validation establishes readiness for review; publication and live verification remain separate steps.

## Distribution decision

Decision: 2026-09-05, approved by the maintainer. Do not publish this project to PyPI. Supported distribution channels are GitHub Releases (wheel and source archives) and the `snapsynapse/tap/substack2md` Homebrew formula. The PyPI name `substack2md` belongs to a different project; a renamed PyPI distribution and its publishing infrastructure are outside maintenance scope. Python dependencies may still be obtained from PyPI. Revisit only through an explicit maintainer decision.

## Release checklist

1. Review the scoped diff, outstanding issues, and unprocessed handoffs. Preserve unrelated local changes. Select a version appropriate to the final change, then update `substack2md/_version.py`, `CHANGELOG.md`, and version surfaces together during authorized local preparation. Mark the release date only when publication is authorized.
2. Run the offline suite and pinned Ruff checks documented in [CONTRIBUTING.md](../CONTRIBUTING.md), followed by `git diff --check`. Exercise the supported Python versions in CI. Do not treat a test run with a different Ruff version as the pinned check.
3. Build a wheel from the intended source and install it in a fresh virtual environment. Run the console entry point and module entry point outside the checkout, verify the version and import location, and perform an offline Markdown conversion. Use `scripts/smoke_wheel.py` with the path to the built wheel for the isolated installation and conversion check; dependency installation may contact the package index. Record the artifact and source commit used.
4. Review the synthetic extraction and CDP fixtures when Substack or browser behavior changes. Run the optional public API test when useful and record its actual outcome. Authenticated browser capture requires separate authorization and is not established by offline or API tests.
5. Review README, website, machine-readable documentation, examples, and assistant guide copies. Verify guide hashes and byte identity after guide changes. Keep release notes and candidate records explicit about publication status; source version metadata is not publication evidence.
6. With commit authority, create the next natural signed commit using the maintainer's approved signing setup. Verify its signature locally with `git verify-commit HEAD`. Do not change global signing configuration as part of routine release preparation.
7. With push authority, push the reviewed commit and verify that GitHub shows it as Verified and exact-commit CI passes. A locally valid signature does not establish GitHub verification.
8. With release authority, create a new annotated signed version tag and verify it locally with `git verify-tag`. Publish the authorized tag and release; check GitHub signature status, release version, source commit, and downloadable artifact. Never replace an existing public tag solely to add a signature.
9. Reconcile the Homebrew formula against the published source/archive and checksum through the separately authorized tap update. Verify installation from the updated formula. Confirm any website deployment references the intended release; do not equate a successful test run with deployment.
10. Record durable release evidence in the changelog or release record. Delete a processed handoff only after its durable facts are transferred and every completion criterion is met; retain it while any requirement remains outstanding.

## Signing baseline and completion criteria

At the September 5, 2026 preparation review, the September 1 signing handoff was pending. Its baseline is `563f685830a61bd35910341e33307b5b3e404d02`; that commit and the annotated `v2.1.2` tag were unsigned. Preserve them unchanged.

The handoff's account-level prerequisite pointer is stale: the old profile handoff has been processed. The maintainer's durable Git SSH Signing Convention records the completed setup. GitHub verification of the profile test commit [`ce5994a`](https://github.com/snapsynapse/snapsynapse/commit/ce5994abae84230948abfa2b5464a6f337e930c0) was rechecked on September 5, 2026 and returned `verified: true`, `reason: valid`. Effective Git settings in this checkout use SSH signing with commit and tag signing enabled. Do not repeat account setup or change keys.

Local signature verification currently requires an explicitly trusted allowed-signers file: `gpg.ssh.allowedSignersFile` is not configured in this checkout. Resolve that verification input from the approved convention at delivery time, without changing global configuration or exposing key material. This does not negate GitHub's verified test-commit evidence.

The release procedure above records this repository's durable signing workflow. Completing the handoff requires the next natural signed commit to be Verified on GitHub and the next release to use an annotated signed tag. Do not delete the handoff based on documentation work alone.

## Historical contribution review

PR #3, `chore: add paywall API test script`, was closed without merging. Keep its useful intent in the maintained live smoke test rather than restoring an import-time network script without assertions. [tests/EVALS.md](../tests/EVALS.md) preserves the historical PR #1 evaluation and identifies its resolution through PR #2; it is not a current blocker list.
