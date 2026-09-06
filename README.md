# substack2md

Convert Substack posts to clean, Obsidian-friendly Markdown using your authenticated browser session.

This documentation describes version 2.2.0. Check [GitHub Releases](https://github.com/snapsynapse/substack2md/releases) for published artifacts; local source changes do not establish publication. See [CHANGELOG.md](CHANGELOG.md) for version history and [docs/MAINTENANCE.md](docs/MAINTENANCE.md) for release gates.

## Why This Exists

Substack doesn't let you bulk-export your reading list or subscriptions in a useful format. This tool:
- Uses your logged-in browser via Chrome DevTools Protocol (CDP)
- Preserves frontmatter metadata
- Converts images/embeds to links (Obsidian-friendly)
- Rewrites cross-references as wikilinks `[[Publication/YYYY-MM-DD-slug|Original label]]`
- Organizes by publication into folders

## Features

- **No password management** - Uses your live browser session
- **Batch processing** - Single URLs or text files with multiple URLs
- **Sequential with delays** - Configurable sleep between requests to be polite
- **Obsidian wikilinks** - Auto-converts internal links to existing notes
- **Configurable naming** - Map publication slugs to custom directory names
- **Transcript cleaning** - Strips timestamps and speaker labels from podcast transcripts
- **Paywall detection** - Optionally tags posts as free or subscriber-only via Substack's public API, so you can avoid accidentally sharing paid content

## Installation

Homebrew (macOS and Linux):
Literal
```bash
brew install snapsynapse/tap/substack2md
```
Or from source in an isolated environment (macOS or Linux):
Literal
```bash
git clone https://github.com/snapsynapse/substack2md.git
cd substack2md
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```
For Windows PowerShell:
Literal
```powershell
git clone https://github.com/snapsynapse/substack2md.git
cd substack2md
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install .
```

## AI-Assisted Installation

This repo includes a GuideCheck Human-Verifiable Assistant Guide for bounded AI-assisted local install:

- https://substack2md.space/.well-known/assistant-guide.txt
- `.well-known/assistant-guide.txt`
- `assistant-guide.txt`
- `assistant-guide-manifest.txt`

The guide targets GuideCheck profile `0.3.0`. Verify the exact guide bytes before use; local copy/hash checks do not establish a current hosted conformance level.

The Pages source includes `docs/_headers` so hosts that support static header rules can serve the guide with `X-Content-Type-Options: nosniff` and `Strict-Transport-Security`. GitHub Pages does not honor `_headers`; if `https://substack2md.space/` remains on GitHub Pages directly, a hosted verifier may report missing-header findings.

Use it this way:

1. Open `.well-known/assistant-guide.txt` or the byte-identical root `assistant-guide.txt` copy and read it in full.
2. Verify `https://substack2md.space/.well-known/assistant-guide.txt` with a conformant verifier such as https://guidecheck.org/verify.
3. Check that the verifier reports the guide SHA-256 and no blocking findings. Compare that SHA-256 with the local guide you intend to execute; do not use a hosted result for different local bytes.
4. Confirm to your assistant that you have read the guide, understand that conformance is not safety, and approve proceeding under the reported level.
5. Let the assistant execute only the explicit `[action]` blocks, with per-action approval where required.

The canonical served path is the `substack2md.space` `.well-known` URL above. The repository path `.well-known/assistant-guide.txt`, the root `assistant-guide.txt` copy, and the Pages source copy under `docs/.well-known/assistant-guide.txt` are kept byte-identical. The sidecar manifest is maintained as a local integrity aid for byte count and SHA-256. Use the canonical served URL when verifying; rendered GitHub file pages and `raw.githubusercontent.com` repository paths are not the standard discoverable location for this project.

For development work:
Literal
```bash
pip install -e ".[dev]"
```
Installing registers a `substack2md` console script on your PATH. You can also invoke the package as a module: `python -m substack2md`.

## Quick Start

### 1. Launch Your Browser with Remote Debugging

The whole tool depends on connecting to a Brave or Chrome instance that was started with `--remote-debugging-port=9222`. The exact invocation differs per OS.

Regardless of OS, three principles apply:

1. Use a **dedicated, isolated profile** (`--user-data-dir`) so your regular browser cookies and extensions are untouched.
2. Keep the debugging endpoint on **loopback only**. The origin allowlist (`--remote-allow-origins=http://127.0.0.1:9222`) controls WebSocket origins; it does not choose the listening address. Never expose or forward the debugging port.
3. Only **one CDP-enabled browser** should use port 9222 at a time.

#### macOS (tested, helper provided)

The repo ships a helper that detects Brave or Chrome, isolates a dedicated CDP profile, and opens the debugging port on loopback:
Literal
```bash
./launch-browser.sh
```
What it does:

- Prefers Brave; falls back to Chrome (arch-aware on Apple Silicon).
- Creates an isolated profile at `$HOME/.brave-cdp-profile` or `$HOME/.chrome-cdp-profile`.
- Binds `--remote-debugging-port=9222` to loopback only and sets `--remote-allow-origins`.
- If port 9222 is already in use, prompts before killing the existing process.
- Verifies CDP is reachable after launch.

Prefer to run the commands yourself? The underlying invocations are:

**Brave (Recommended):**
Literal
```bash
open -na "Brave Browser" --args \
  --remote-debugging-port=9222 \
  --remote-allow-origins=http://127.0.0.1:9222 \
  --user-data-dir="$HOME/.brave-cdp-profile"
```
**Chrome (Apple Silicon):**
Literal
```bash
arch -arm64 /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --remote-allow-origins=http://127.0.0.1:9222 \
  --user-data-dir="$HOME/.chrome-cdp-profile"
```
**Chrome (Intel):**
Literal
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --remote-allow-origins=http://127.0.0.1:9222 \
  --user-data-dir="$HOME/.chrome-cdp-profile"
```
#### Linux (untested by maintainer, reports welcome)

The CDP flags are identical to macOS. Distro packaging determines the binary name. Try, in order of likelihood:

**Brave:**
Literal
```bash
brave-browser \
  --remote-debugging-port=9222 \
  --remote-allow-origins=http://127.0.0.1:9222 \
  --user-data-dir="$HOME/.brave-cdp-profile"
```
If `brave-browser` isn't on your PATH, try `brave` instead.

**Chrome / Chromium:**
Literal
```bash
google-chrome \
  --remote-debugging-port=9222 \
  --remote-allow-origins=http://127.0.0.1:9222 \
  --user-data-dir="$HOME/.chrome-cdp-profile"
```
If `google-chrome` isn't available, try `chromium` or `chromium-browser`.

If nothing works, `which -a brave brave-browser google-chrome chromium chromium-browser` will list whatever is installed.

Linux compatibility reports and corrections to these instructions are welcome.

#### Windows (untested by maintainer, reports welcome)

Use PowerShell. The `&` call operator lets you run executables whose paths contain spaces; the backtick is a line continuation.

**Brave:**
Literal
```powershell
& "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" `
  --remote-debugging-port=9222 `
  --remote-allow-origins=http://127.0.0.1:9222 `
  --user-data-dir="$env:USERPROFILE\.brave-cdp-profile"
```
**Chrome:**
Literal
```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --remote-allow-origins=http://127.0.0.1:9222 `
  --user-data-dir="$env:USERPROFILE\.chrome-cdp-profile"
```
If your install path differs, check `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe` or just search your `C:\Program Files` tree.

Windows compatibility reports and corrections to these instructions are welcome.

### 2. Log Into Substack

In the browser window that just opened, navigate to Substack and log in normally.

### 3. Convert Posts

**Single URL:**
Replace: POST_URL -> the full HTTPS URL of the Substack post you want to archive. Quote paths that contain spaces.
Customize
```bash
substack2md POST_URL
```
**Multiple URLs from file:**
Replace: URLS_FILE -> the path to your text file of post URLs. Quote paths that contain spaces.
Customize
```bash
substack2md --urls-file URLS_FILE
```
**Specify output directory:**
Replace: POST_URL -> the full HTTPS URL of the Substack post you want to archive. Quote paths that contain spaces.
Replace: OUTPUT_DIR -> the destination directory for your archive. Quote paths that contain spaces.
Customize
```bash
substack2md POST_URL --base-dir OUTPUT_DIR
```
## Configuration

### Environment Variables
Literal
```bash
export SUBSTACK2MD_BASE_DIR=~/Documents/substack-notes
```
After creating a configuration file, optionally point to it. The file must already exist.
Replace: CONFIG_PATH -> the absolute path to your existing configuration file. Keep the quotes.
Customize
```bash
export SUBSTACK2MD_CONFIG="CONFIG_PATH"
```
### Config File

Create a configuration file and pass its path with `--config`, or set `SUBSTACK2MD_CONFIG`. Without either setting, the tool looks for `config.yaml` alongside the installed package:
Literal
```yaml
# Base directory for markdown output
base_dir: ~/Documents/substack-notes

# Map publication slugs to custom directory names
publication_mappings:
  sigsub: Signals_And_Subtractions
  natesnewsletter: Nates_Notes
  daveshap: David_Shapiro
```
Mapping values are treated as relative directories under `base_dir`. Absolute paths and `..` components are rejected so a config mistake cannot write outside your archive root.

See `config.yaml.example` for a template.

## Usage Examples
Replace: POST_URL -> the full HTTPS URL of the Substack post you want to archive. Quote paths that contain spaces.
Replace: URLS_FILE -> the path to your text file of post URLs. Quote paths that contain spaces.
Replace: OUTPUT_DIR -> the destination directory for your archive. Quote paths that contain spaces.
Replace: MARKDOWN_FILE -> the path to your existing Markdown export. Quote paths that contain spaces.
Customize
```bash
# Single post with custom output directory
substack2md POST_URL --base-dir OUTPUT_DIR

# Batch processing with slower delays (be nice to servers)
substack2md --urls-file URLS_FILE --sleep-ms 500

# Parallel workers for large reading lists (per-publication rate limits preserved)
substack2md --urls-file URLS_FILE --concurrency 4

# Save HTML alongside markdown (for debugging)
substack2md POST_URL --also-save-html

# Overwrite existing files
substack2md POST_URL --overwrite

# Process from existing markdown export (cleanup only)
substack2md --from-md MARKDOWN_FILE --url POST_URL

# Tag posts with paywall status (respects creators' rights)
substack2md --urls-file URLS_FILE --detect-paywall

# Quiet mode for scripted use; errors still surface
substack2md --urls-file URLS_FILE --quiet
```
## URL File Format

Create a text file with one URL per line. Replace these sample URLs with posts you want to archive.
```
https://sigsub.substack.com/p/the-trust-gap
https://natesnewsletter.substack.com/p/i-surveyed-100-ai-tools-that-launched
# Comments start with #
https://daveshap.substack.com/p/the-merits-of-doing-things-the-hard
```
## Output Structure
```
~/Documents/substack-notes/
├── Signals_And_Subtractions/
│   └── 2025-09-29-the-trust-gap.md
├── Nates_Notes/
│   ├── 2025-10-20-i-surveyed-100-ai-tools-that-launched.md
│   └── 2025-10-18-i-read-17-hours-of-ai-news-this-week.md
└── David_Shapiro/
    └── 2025-10-18-the-merits-of-doing-things-the-hard.md
```
## Markdown Frontmatter

Example output with optional paywall detection enabled:
```yaml
---
title: "Post Title"
subtitle: "Optional subtitle"
author: "David Shapiro"
publication: "daveshap"
published: "2025-10-18"
updated: "2025-10-18"
retrieved: "2025-10-20T15:30:00Z"
url: "https://daveshap.substack.com/p/post-slug"
canonical: "https://daveshap.substack.com/p/post-slug"
slug: "post-slug"
tags: [substack, ai, automation]
image: "https://substackcdn.com/image.jpg"
is_paid: false
audience: "everyone"
links_internal: 3
links_external: 12
source: "substack2md v2.2.0"
---

Content starts here...
```
## Paywall Detection

When `--detect-paywall` is passed, substack2md queries Substack's public API to determine whether each post is free or subscriber-only. This adds two fields to the YAML frontmatter:

- **`is_paid`** (`true`/`false`/`null`) - whether the post requires a paid subscription
- **`audience`** - the raw Substack audience enum; known values:
  - `everyone` - public, free to read
  - `only_free` - requires a free subscription (not paywalled)
  - `only_paid` - requires a paid subscription
  - `founding` - requires founding-member subscription (paid)

If Substack returns an unrecognized audience value (a new tier), `audience` is preserved verbatim and `is_paid` is set to `null` so downstream workflows treat the post as "status unknown" rather than silently classifying it as free. On API failure (non-200, timeout, non-JSON) both fields are `null` and the pipeline continues.

This is opt-in and requires no additional authentication; the metadata endpoint is public. Without `--detect-paywall`, both fields are omitted. Version 2.2.0 preserves explicit nulls for unknown status; v2.1.2 omitted null fields. Paywall metadata does not establish that a captured article contains its full text.

**Why this matters:** If you have a paid subscription, CDP will fetch the full content of subscriber-only posts. The paywall metadata lets you build guardrails in your own workflows to avoid accidentally sharing or redistributing content that creators intended for paying subscribers only. Respect the creators whose work you value enough to pay for.

## Troubleshooting

### "No CDP connection"
- Make sure your browser launched with `--remote-debugging-port=9222`
- Check that no other process is using port 9222
- Try closing all Chrome/Brave windows and launching again

### "Missing modules" error
Literal
```bash
pip install .
```
### URLs not being converted to wikilinks
- The tool only converts links to posts you've already downloaded
- Run the same URL list with `--overwrite` to refresh links to notes now present. This refetches posts; there is no offline relinking command.
- With released v2.1.2, also pass `--no-resume`; its resume filter otherwise prevents the overwrite pass.

### Rate limiting / bot detection
- Increase `--sleep-ms` (default: 150ms)
- Use smaller batches
- Substack shouldn't rate-limit authenticated sessions, but YMMV

## Advanced Options
Literal
```bash
substack2md --help
```
```
options:
  --urls-file FILE         File with URLs, one per line
  --from-md FILE           Clean existing markdown export
  --url URL                URL for --from-md mode
  --base-dir DIR           Output directory
  --config FILE            Path to config.yaml
  --also-save-html         Save HTML sidecar files
  --overwrite              Replace existing files
  --cdp-host HOST          CDP hostname (default: 127.0.0.1)
  --cdp-port PORT          CDP port (default: 9222)
  --timeout SECONDS        Page load + paywall API timeout (default: 45)
  --retries N              Total attempts per URL, at least 1 (default: 2)
  --sleep-ms MS            Delay between requests per publication (default: 150)
  --detect-paywall         Add is_paid/audience to frontmatter via Substack API
  --concurrency N          Parallel worker threads, 1=sequential (default: 1)
  --no-resume              Disable the .substack2md-state resume file
  --log-level LEVEL        DEBUG/INFO/WARNING/ERROR (default: INFO)
  --quiet, -q              Suppress per-URL progress lines
  --version                Print version and exit
```
### Resume after interruption

The `.substack2md-state` file under your output directory records completed captures as JSON lines containing the URL and relative output path. Existing URL-only state entries remain readable; the archive index and files are checked before skipping them. A later run skips completed URLs only while their requested output artifacts still exist. Missing Markdown is regenerated. Missing requested HTML sidecars are recovered while preserving existing Markdown unless `--overwrite` is passed. `--overwrite` bypasses resume and replaces existing outputs; `--no-resume` disables state tracking but does not itself replace existing files.

Completion is recorded only after every requested artifact is written. A hidden `.<markdown-name>.pending` marker tracks an interrupted artifact replacement. Leave it in place during ordinary reruns: the next capture regenerates the requested artifacts and removes the marker after recovery. Interrupted writes can be retried. On interruption, queued work is canceled and active captures finish within their configured bounds before the command exits. A batch reports written, skipped, and failed totals and exits nonzero if any URL fails. Navigation errors and clearly invalid captures are failures, not completed notes. Capture validation cannot prove that every article is complete; inspect important archives, especially when a subscription or site layout changes.

These recovery behaviors apply to 2.2.0. In v2.1.2, state contains URLs only, missing output is not checked, and a forced refresh requires both `--no-resume` and `--overwrite`.

## Contributing

Pull requests welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for local test setup and PR conventions.

The contribution scope is maintenance-only: correctness fixes, security fixes, dependency and browser compatibility, regression tests, and documentation corrections. New platforms, export formats, and UI features are outside the current scope. Platform troubleshooting reports are welcome; see the [maintenance policy](docs/MAINTENANCE.md).

## License

MIT License - see LICENSE file for details.

## Credits

Built with:
- [websocket-client](https://github.com/websocket-client/websocket-client)
- [BeautifulSoup](https://crummy.com/software/BeautifulSoup/)
- [readability-lxml](https://github.com/buriy/python-readability)
- [markdownify](https://github.com/matthewwithanm/python-markdownify)

## Disclaimer

This tool is for personal archival purposes. Respect content creators' rights and Substack's terms of service. DON'T STEAL! STEALING IS BAD BAD BAD!!! Getting better utility from Substacks you already support is not. Sharing without permission is the line, don't cross it.
