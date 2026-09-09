# INTENT

Status: Authoritative for the substack2md product scope.
Scope: Repository-level purpose, maintenance boundaries, and standards applicability. This document consolidates the existing scope in [README.md](README.md) and [docs/MAINTENANCE.md](docs/MAINTENANCE.md); it does not expand the product or authorize publication.

## What this product is

substack2md is a Python command-line tool for personal Substack archives. It converts posts available through the user's authenticated CDP browser session into Obsidian-friendly Markdown, and can clean existing Markdown exports. The repository also owns a static documentation website at https://substack2md.space/ and a bounded AI-assisted installation guide.

## Why it exists

The tool makes a reading archive usable outside Substack by preserving post metadata, organizing notes by publication, and converting cross-references into local wikilinks. It uses the user's existing access to content; it does not grant access or permission to redistribute that content.

## Design invariants

These summarize existing behavior and maintenance requirements, rather than introducing new product commitments.

1. Capture uses a user-controlled browser session. The documented setup isolates its profile and keeps the sensitive CDP endpoint local; credentials and private captured content are excluded from fixtures and routine logs.
2. Archive paths remain inside the configured output root. Requested artifacts must be written before a capture is recorded as complete, and failed batch items produce a nonzero exit status.
3. Unknown paywall metadata remains unknown. Capture and metadata checks do not prove article completeness or redistribution rights.
4. Offline regression checks work without a browser or credentials. API compatibility and authenticated browser capture require their own evidence.
5. Installation guidance identifies exact guide bytes and explicit actions. Local mirror/hash checks do not establish hosted conformance, publisher identity, dependency safety, or release publication.

## Scope boundaries

In scope: correctness and security fixes, dependency and browser compatibility, regression coverage, documentation corrections, and maintenance of the existing CLI, website, and installation guide.

Out of scope: new publishing platforms, export formats, user interfaces, and publication to PyPI. The approved distribution channels are GitHub Releases and the separately maintained Homebrew formula; [the distribution decision](docs/MAINTENANCE.md#distribution-decision) explains the PyPI exclusion. Commit, push, release, tap update, and deployment remain separate delivery steps.

## Standards applicability

[repo-standards.yaml](repo-standards.yaml) records repository roles, owned surfaces, applicable standards, adoption state, existing checks, and reassessment triggers. It declares expectations and evidence gaps; it is not a conformance certificate. Review it when scope, build paths, public surfaces, or claimed standards change.

The installation guide declares GuideCheck profile 0.3.0. Hosted-site changes use the evidence-based [Siteline assessment procedure](CONTRIBUTING.md#hosted-site-siteline-assessment). Related-standard links on the website are not adoption claims. A change to the CLI does not by itself establish that agent-specific standards apply to its runtime.

## Exceptions to Repo Standards

- No portfolio-standard waiver is established by this document. Unresolved applicability and missing assessment evidence stay explicit in `repo-standards.yaml` until reviewed.
- The existing guide mirrors and manifests are local integrity aids. Their agreement is not evidence of independently administered trust anchors.

## Changelog

- 2026-09-08: Consolidated existing maintenance scope and distribution boundaries; added a repository-local standards declaration pilot without changing runtime behavior or publication status.
