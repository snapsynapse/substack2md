# Security

## Threat model

substack2md connects to a running Chrome/Brave instance via the Chrome DevTools Protocol (CDP) on `127.0.0.1:9222` by default. While connected, it can:

- Read the full DOM of any tab in that browser
- Navigate to URLs using your authenticated session cookies
- Create and destroy tabs

This is intentional and required for the tool to work. It also means the CDP endpoint is a sensitive local interface that should not be exposed beyond the machine running it.

## Recommended setup

Launch your browser with the exact flags shown in the README. In particular:

- `--remote-debugging-port=9222` opens the CDP port on the loopback interface only.
- `--remote-allow-origins=http://127.0.0.1:9222` restricts WebSocket upgrade requests to the loopback origin, mitigating DNS-rebinding attacks.
- `--user-data-dir="$HOME/.brave-cdp-profile"` isolates the CDP-enabled profile from your main browsing profile.

Do not:

- Bind CDP to `0.0.0.0` or a public interface.
- Share the `--user-data-dir` with a browser you use for general browsing.
- Run substack2md against an untrusted CDP endpoint on another machine.

## Paywall API calls

When `--detect-paywall` is enabled, substack2md makes unauthenticated HTTPS calls to `https://<publication>.substack.com/api/v1/posts/<slug>`. The User-Agent is `substack2md/<version>`. No cookies, credentials, or personal data are sent. The endpoint is publicly accessible.

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
