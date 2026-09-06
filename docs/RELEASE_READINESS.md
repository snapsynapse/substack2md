# Version 2.2.0 release preparation

Prepared: 2026-09-05. Scope: substack2md only.
Baseline: `563f685830a61bd35910341e33307b5b3e404d02` on `main`; release baseline for the maintenance changes.

## Candidate

Version 2.2.0 is selected for additive detailed outcomes and output-aware recovery while preserving default Path/None library results. README, package version, website metadata and examples, machine summary, changelog, and assistant guide now describe the implemented maintenance scope. Documentation distinguishes source version from publication status.

Release notes: [v2.2.0](releases/v2.2.0.md). Continuing procedure: [MAINTENANCE.md](MAINTENANCE.md). Publication evidence is recorded in the [GitHub release](https://github.com/snapsynapse/substack2md/releases/tag/v2.2.0).

## Local validation and artifact record

The source suite passes 123 tests with one opt-in live test skipped, using Python 3.14.7 and Ruff 0.16.1. The separate public API test passed during maintenance implementation. No authenticated browser capture was performed. HTML fixtures are synthetic and CDP messages are simulated.

The ignored local `dist/2.2.0/` bundle holds the prepared artifacts, checksums, exact working-tree fingerprint, stage-path inventory, and release-state record. This record, rather than an earlier 2.1.2 validation wheel, owns candidate package evidence. Recheck its fingerprint before staging; any source edit requires rebuilding affected artifacts and rerunning their gates.

Planned GitHub assets:
- `substack2md-2.2.0-py3-none-any.whl`
- `substack2md-2.2.0.tar.gz` (Python source distribution)
- `substack2md-v2.2.0.tar.gz` and `substack2md-v2.2.0.zip` (complete reviewed source snapshots)
- `RELEASE_NOTES-v2.2.0.md`
- `SHA256SUMS`

The source snapshots exclude ignored handoffs, local configuration, browser profiles, caches, and Git metadata. No PyPI publication or Homebrew repository mutation is included in local preparation. Homebrew remains a separate distribution follow-up after the release exists.

## Prepared delivery sequence

1. Recheck remote main, absence of a conflicting v2.2.0 tag/release, candidate fingerprint, and the exact path list. Finalize the changelog date under publication authority and refresh affected artifacts.
2. Stage only reviewed paths and create a signed commit titled `release: prepare substack2md v2.2.0 maintenance release`. Verify locally using an explicitly trusted allowed-signers file.
3. Push that commit to main and verify GitHub signature status and required CI on its exact SHA. Pushing main also triggers the configured GitHub Pages deployment from `/docs`; the delivery approval must cover that consequence.
4. Create the annotated signed `v2.2.0` tag at that verified commit, verify it locally, then push the tag.
5. Create GitHub Release `substack2md v2.2.0` from the reviewed notes and upload the named assets. Do not replace an existing tag or asset silently.
6. Verify remote main/tag/release identity, asset digests and clean consumption, and deployed website/guide/machine-summary bytes. Reconcile the Homebrew formula only within its authorized scope.
7. Update the release-state record with immutable provider evidence and process the existing signing handoff once all of its criteria are met.

Delivery was authorized on September 5, 2026. The GitHub release and its tagged source identify the published result; this document records preparation and the verification procedure.

## Signing and remaining limits

The account setup prerequisite is complete and traced to the durable convention plus GitHub-verified profile commit `ce5994a`. Do not repeat account setup or change keys. The local candidate bundle may provide an allowed-signers file derived from the account's public GitHub signing keys; its verification evidence is in the release-state record. No global signing configuration is changed.

PR #3 remains closed without merging. The repository's signing handoff remains open for its next signed commit, GitHub verification, and annotated signed release tag. Local checks do not establish hosted CI, publication, deployment, or authenticated capture for the final release.
