# Final-release preparation

Prepared: 2026-11-22 America/Denver. Scope: this repository only. Candidate: v3.0.0, requiring Python >=3.11.5. Latest published release: [v2.2.1](https://github.com/snapsynapse/substack2md/releases/tag/v2.2.1), commit `f876cf8`.

## Lifecycle decision

Owner decision, November 22, 2026: v3.0.0 is the last planned release. Critical security and breakage fixes remain in scope until retirement is announced. Retirement is expected soon; optional maintenance may still be considered before then. The repository is not retired or archived. No branch/worktree deletion is required.

## Roadmap disposition

| Item | Disposition | Evidence or remaining boundary |
|---|---|---|
| GitHub issues and pull requests | Closed queue | Live check on November 22 returned no issues and no open PRs. PRs 1 and 2 are merged; PR 3 is closed. |
| Captured HTML links and wikilinks | Shipped in v2.2.1 | Synthetic unsafe-scheme, delimiter and legitimate-link checks pass. Renderer execution remains untested. |
| Ambient paywall authentication | Implemented in candidate | Fresh session disables trust_env and redirects; regression uses matching netrc plus a redirect response and confirms no Authorization/Cookie headers. |
| Capture resources | Implemented in candidate | Early DOM byte check, 8 MiB check before parsing, at most 8 CLI workers. No claim of a browser memory sandbox or parser wall-clock deadline. |
| Private URL logs | Implemented in candidate | CLI success/failure logs omit URLs and raw transport messages. HTTP debug logging is suppressed. Caller-controlled library logging and returned error objects remain private data. |
| URL admission | Implemented in candidate | HTTPS, no credentials/nonstandard ports/literal IP targets; Substack /p paths, custom publication paths preserved. DNS and browser redirects are not network-isolated. |
| Dependencies and CI | Implemented and locally verified | Raised direct/transitive security floors, tested runtime constraints, immutable official action SHAs, contents-read-only CI, dependency audit job. Python 3.11.5, 3.12.16, 3.13.18 and 3.14 pass locally. CI now covers 3.11.5 and latest 3.11 through 3.14. Exact-candidate hosted CI remains pending. |
| Mac launcher process ownership | Shipped in v2.2.1 | Refuses an occupied port. Candidate also removes blanket advice to close unrelated browser windows. |
| Imported Markdown | Explicit trust boundary | Keep content-preserving cleanup. Imported text, code examples and raw HTML are operator-selected untrusted data, not sanitized documents. Drop a universal Markdown sanitizer from this product's roadmap. |
| HTML sidecar retention | Operator responsibility | Off by default; private archive confirmed. No automatic deletion or retention daemon. Captured HTML can be active content when opened. |
| Public/team publishing guardrails | Out of scope | Owner confirmed private local archive. Paywall metadata never grants sharing rights or blocks output. Do not add a publishing product. |
| New platforms, formats, UI, crawling, PyPI | Dropped from roadmap | Existing maintenance-only scope and distribution decision remain authoritative. |
| Signing handoff | Delivery criteria met | v2.2.1 commit and signed annotated tag verified locally and on GitHub; exact-commit CI and published wheel consumer check passed. Historical unsigned tags stay unchanged. |
| Old branches and detached worktree | Preserve | No branch commits absent from main or fetched remotes, no stashes. Detached `.claude/worktrees/vigilant-germain` is retained; no deletion needed for release. |
| Homebrew | Separate delivery follow-up | Tap is separately owned and was not changed here. Final release preparation does not assert its version or installation result. |
| Standards expansion | No runtime expansion | Keep unresolved applicability explicit. Related-standard links and local guide hashes are not conformance evidence. |
| Search-console work | Excluded | No search submission or ranking outcome is required to deliver this CLI. Existing provider state remains unassessed. |
| Hosted assessments and browser acceptance | Partly verified | Siteline pre-delivery assessment and local GuideCheck Level 3 verification completed; authenticated capture and rendered accessibility remain unobserved. Post-deployment verification must use deployed candidate bytes. |

## Security audit disposition

The [original audit](security/audits/audit-2026-11-22.md) is a dated baseline at `c01d2aa`, not a claim that its original findings remain unchanged.

| Finding | Candidate disposition |
|---|---|
| SEC-001 | HTML link generation mitigated in v2.2.1; imported Markdown has an explicit untrusted-input boundary rather than a universal sanitizer. |
| SEC-002 | Generated-link delimiter handling mitigated in v2.2.1. |
| SEC-003 | Bounded HTML and worker count implemented; process/parse isolation remains a documented residual. |
| DEP-001 | Safe certificate minimum required; fresh consumer resolves certifi 2026.11.20 and audit is clear. Existing user environments need reinstall/upgrade. |
| SEC-004 | CLI logging mitigation implemented and regression-tested; no promise to scrub library caller logs or returned error objects. |
| SEC-005 | Action pins, dependency audit, safe floors and tested constraints implemented. Constraints are a tested version set, not hash-verified supply-chain provenance. |
| SEC-006 | Launcher fix shipped in v2.2.1. |
| SEC-007 | Size bound added; private archive and opt-in sidecar retention remain operator choices. |
| FIELD-001 | Dedicated profile acceptable; actual browser binding/profile acceptance remains unobserved. |
| FIELD-002 | Private local archive removes the proposed automated-publishing use case; no redistribution permission inferred. |
| FIELD-003 | HTTPS admission reduces accidental scope; only trusted operator-selected URLs are supported. Browser navigation is not an SSRF sandbox. |

## Optional work before retirement

These items may be considered after v3.0.0; they do not hold this release or promise another one.

| Item | Decision boundary |
|---|---|
| Custom-domain paywall lookup | Retain as optional compatibility work. Existing custom-domain capture stays supported; metadata may remain unknown. No new authenticated metadata channel. |
| Additional public/synthetic extraction fixtures | Accept narrowly scoped output-quality and browser-compatibility coverage. No private subscriber fixtures or expanded crawling. |
| Retirement documentation | Prepare a final support notice and channel disposition when the owner declares retirement. Do not archive or shut down delivery channels now. |

## Release gates

| Gate | State and evidence |
|---|---|
| Version and support decision | Settled: v3.0.0, Python >=3.11.5, last planned release; critical security and breakage fixes until retirement. |
| Source and guide integrity | Local version/copy/hash checks pass. Guide 1.0.3 targets 3.0.x; its planned v3.0.0 provenance URL is not published yet. |
| Offline checks | 160 tests pass with one opt-in API skip on each of Python 3.11.5, 3.12.16, 3.13.18 and 3.14; the API test separately passes. Final artifact identity is recorded in the local preparation receipt. Ruff 0.16.1, shell syntax and whitespace checks pass. |
| Public API | Public Substack metadata fixture passed on Python 3.11.5. No subscriber content or browser session used. |
| Dependency audit | Fresh minimum-version environment: 26 distributions audited, zero known advisories. Constraints record tested versions, not package hashes. The minimum-version bootstrap initially exposed setuptools 65.5.0 (nine raw advisory records, five distinct IDs); installation guidance, CI, wheel smoke and the isolated build floor now require setuptools >=84.1.0. |
| GuideCheck | Reference verifier at evaluator commit d64f269befb3a561ce570c7688f6ee965ae18c4b, version 0.7.1, explicitly selected profile 0.3.0: Level 3, no blocking findings or warnings. Local guide SHA-256: 5db67193bdf5c9fc7bb8ea302b08dfb2d6c663c905b6f61edc3191fd32f65590. This is local evaluation, not hosted acceptance or publisher provenance. |
| Siteline before delivery | Completed against the published v2.2.1 site on 2026-11-23T00:46:01.628Z (November 22 locally). Stored result substack2md-space-v2-34fd9020193fe0e14ec4a489-20261123, scanner 2.1.2, rubric 2.4.0: D/63. All nine reported checks pass; all five ranked findings are passing opportunities. The low grade is retained as reported, not converted to a target defect. No missing commerce features are added to this CLI documentation site. Passive guide screening is not full GuideCheck; absent Graceful Boundaries evidence is informational. No candidate deployment acceptance is inferred. |
| Packed artifact | Wheel and sdist built; metadata, source membership and package bytes match the candidate. Clean wheel consumers pass both entry points, expected failures and offline conversion on Python 3.11.5 and 3.14. The installer rejects Python 3.11.4. The Unix smoke environment uses symlinks, matching the venv CLI and preserving standalone macOS Python shared-library lookup. Final hashes and working-tree fingerprint are in the local preparation receipt. |
| Rendered accessibility | Pending Comet availability. No axe/WCAG result or keyboard/device acceptance is claimed. No browser-policy exception or alternate controller is assumed. |
| Dedicated-profile capture | Pending human-gated browser acceptance. Verify a public post and a custom publication domain, output, failure behavior and dedicated loopback profile without retaining private content. Offline CDP fixtures do not establish this gate. |
| Delivery | Await explicit v3.0.0 commit/push/publication authority. Pushing main deploys Pages. Verify signed commit, exact-commit five-job CI, signed tag and assets/checksums before declaring delivery. Recheck deployed website/guide bytes and hosted assessments after deployment. |
| Homebrew | Separate tap update and installation check after the GitHub release exists; no claim that the current formula contains this candidate. |

This document replaces the processed repository-state handoff. Historical release preparation remains in `RELEASE_READINESS.md`; it is not an active queue. No final commit, tag or release has been published.

The baseline scanner run `20261122T235432Z-81cb08` had intact collectors and found missing ignore families plus the retained handoff; those local repairs are made. Standards declaration intake now validates with jsonschema installed in the temporary tooling environment. Semantic conformance and unresolved applicability remain unassessed. Search-console activity remains excluded. The preparation scanner run `20261123T005059Z-7cf607` has intact collectors: handoffs and baseline ignore families pass; the working tree is intentionally dirty, semantic standards/search/accuracy remain unknown, and its green CI belongs to the published base rather than the candidate. It is not a final-release acceptance result.
