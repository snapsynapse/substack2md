# Security

The link filtering and launcher safeguards described below were added in v2.2.1. Check the installed version before relying on them.

## Threat model

URL capture connects to a running Chrome/Brave instance via the Chrome DevTools Protocol (CDP) on `127.0.0.1:9222` by default. While connected, it can:

- Read the full DOM of any tab in that browser
- Navigate to URLs using your authenticated session cookies
- Create and destroy tabs

This is intentional and required for the tool to work. It also means the CDP endpoint is a sensitive local interface that should not be exposed beyond the machine running it.

## Recommended setup

Launch your browser with the exact flags shown in the README. In particular:

- `--remote-debugging-port=9222` opens the CDP port. The documented browser setup expects a loopback listener; verify the actual bind address on your machine.
- `--remote-allow-origins=http://127.0.0.1:9222` permits that WebSocket origin; it does not set the listening interface or authenticate clients. Keep the endpoint local and do not forward its port.
- `--user-data-dir="$HOME/.brave-cdp-profile"` isolates the CDP-enabled profile from your main browsing profile.

Do not:

- Bind CDP to `0.0.0.0` or a public interface.
- Share the `--user-data-dir` with a browser you use for general browsing.
- Run substack2md against an untrusted CDP endpoint on another machine.

The macOS launcher refuses to replace a process already listening on port 9222. If it reports a conflict, identify and close the listener yourself before retrying. A dedicated profile is the recommended field setup, even on a personal machine; a CDP-enabled regular browsing profile can expose unrelated signed-in accounts to other local processes.

## Archive content

Captured publication HTML is untrusted input. Conversion keeps HTTP(S), mail and telephone links and resolves relative links against the source page. Other link schemes become plain text; link destinations are escaped for Markdown. Cross-references with unsafe Obsidian wikilink delimiters stay as ordinary Markdown links. These measures protect links created from captured HTML; they do not sanitize article prose, `--from-md` imports, or optional raw HTML sidecars. Review archive content before an agent acts on it or before sharing it, and keep `--also-save-html` off unless you need a raw capture for debugging.

## Paywall API calls

In the final-release candidate, `--detect-paywall` uses a fresh Requests session with `trust_env=False` and redirects disabled. It sends no browser cookies and does not load `.netrc` credentials, environment proxies or ambient certificate overrides. The request still reveals the publication and post slug to Substack. Non-200 responses, including redirects, leave paywall status unknown.

The candidate accepts HTTPS publication URLs with no embedded credentials or nonstandard ports. Substack URLs must use `/p/slug`; custom domains can retain their own post paths. Literal IP targets and common internal suffixes are rejected. The browser may follow redirects or resolve public-looking names to private addresses, so this is input validation, not a network sandbox. Only operator-selected publication URLs belong in the input list.

Captured HTML is limited to 8 MiB before Python parsing, with an early browser-side size check. CLI concurrency is limited to 8. These are resource bounds, not a process memory limit or a parser wall-clock deadline. Article URLs and raw transport exception messages are omitted from CLI progress and failure logs. Library callers control their own logging and must protect returned error detail.

## AI-assisted install guide

The repository includes `.well-known/assistant-guide.txt`, a byte-identical root `assistant-guide.txt` copy, a GitHub Pages source copy under `docs/.well-known/assistant-guide.txt`, and `assistant-guide-manifest.txt` for GuideCheck-style AI-assisted local installation. The guide targets profile 0.3.0, and the manifest is a local integrity aid; verify exact bytes before relying on a conformance result. Treat these files as security-relevant operational instructions:

- Review the full plain-text guide before authorizing an assistant to act.
- Verify the guide with a conformant verifier such as https://guidecheck.org/verify.
- Do not treat GuideCheck conformance as proof that commands, dependencies, or publishers are safe.
- Keep all three guide copies and both manifests in sync with install, dependency, test, lint, and local setup changes.

## Reporting a vulnerability

If you find a security issue:

1. Do **not** open a public GitHub issue.
2. Email the maintainer at the address in the GitHub profile of [@snapsynapse](https://github.com/snapsynapse), or open a private GitHub security advisory via the repo's Security tab.
3. Include a clear reproduction, affected version, and any relevant logs.

You can expect an initial response within 7 days. Please hold public disclosure until a fix is available or 90 days have elapsed, whichever comes first.

## Scope

In scope:
- Command injection, path traversal, or arbitrary-file-write via crafted URLs, config files, or markdown input.
- Credential leakage via logs, frontmatter, or sidecar HTML files.
- CDP client misbehavior that could attack the connected browser.

Out of scope:
- Anything that requires prior local code execution on your machine.
- Substack's own API behavior.
- Issues in upstream dependencies (report those to the dependency maintainers; we'll bump versions as patches land).
