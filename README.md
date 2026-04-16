# substack2md

Convert Substack posts to clean, Obsidian-friendly Markdown using your authenticated browser session.

## Why This Exists

Substack doesn't let you bulk-export your reading list or subscriptions in a useful format. This tool:
- Uses your logged-in browser via Chrome DevTools Protocol (CDP)
- Preserves frontmatter metadata
- Converts images/embeds to links (Obsidian-friendly)
- Rewrites cross-references as wikilinks `[[YYYY-MM-DD-slug]]`
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

```bash
# Clone the repo
git clone https://github.com/snapsynapse/substack2md.git
cd substack2md

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### 1. Launch Your Browser with Remote Debugging

**Brave (Recommended):**
```bash
open -na "Brave Browser" --args \
  --remote-debugging-port=9222 \
  --remote-allow-origins=http://127.0.0.1:9222 \
  --user-data-dir="$HOME/.brave-cdp-profile"
```

**Chrome (Apple Silicon):**
```bash
arch -arm64 /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --remote-allow-origins=http://127.0.0.1:9222 \
  --user-data-dir="$HOME/.chrome-cdp-profile"
```

**Chrome (Intel):**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --remote-allow-origins=http://127.0.0.1:9222 \
  --user-data-dir="$HOME/.chrome-cdp-profile"
```

### 2. Log Into Substack

In the browser window that just opened, navigate to Substack and log in normally.

### 3. Convert Posts

**Single URL:**
```bash
python substack2md.py https://natesnewsletter.substack.com/p/latest-post
```

**Multiple URLs from file:**
```bash
python substack2md.py --urls-file my-reading-list.txt
```

**Specify output directory:**
```bash
python substack2md.py https://daveshap.substack.com/p/post-slug --base-dir ~/my-notes
```

## Configuration

### Environment Variables

```bash
# Set default base directory
export SUBSTACK2MD_BASE_DIR=~/Documents/substack-notes

# Set config file location
export SUBSTACK2MD_CONFIG=~/.config/substack2md/config.yaml
```

### Config File

Create `config.yaml` in the script directory or specify with `--config`:

```yaml
# Base directory for markdown output
base_dir: ~/Documents/substack-notes

# Map publication slugs to custom directory names
publication_mappings:
  signalsandsubtractions: Signals_And_Subtractions
  natesnewsletter: Nates_Notes
  daveshap: David_Shapiro
```

See `config.yaml.example` for a template.

## Usage Examples

```bash
# Single post with custom output directory
python substack2md.py https://pub.substack.com/p/slug --base-dir ~/vault

# Batch processing with slower delays (be nice to servers)
python substack2md.py --urls-file urls.txt --sleep-ms 500

# Save HTML alongside markdown (for debugging)
python substack2md.py URL --also-save-html

# Overwrite existing files
python substack2md.py URL --overwrite

# Process from existing markdown export (cleanup only)
python substack2md.py --from-md export.md --url https://pub.substack.com/p/slug

# Tag posts with paywall status (respects creators' rights)
python substack2md.py --urls-file urls.txt --detect-paywall
```

## URL File Format

Create a text file with one URL per line:

```
https://signalsandsubtractions.substack.com/p/the-trust-gap
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

Each file includes YAML frontmatter:

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
source: "substack2md v1.2.0"
---

Content starts here...
```

## Paywall Detection

When `--detect-paywall` is passed, substack2md queries Substack's public API to determine whether each post is free or subscriber-only. This adds two fields to the YAML frontmatter:

- **`is_paid`** (`true`/`false`/`null`) — whether the post requires a paid subscription
- **`audience`** — the raw Substack audience enum; known values:
  - `everyone` — public, free to read
  - `only_free` — requires a free subscription (not paywalled)
  - `only_paid` — requires a paid subscription
  - `founding` — requires founding-member subscription (paid)

If Substack returns an unrecognized audience value (a new tier), `audience` is preserved verbatim and `is_paid` is set to `null` so downstream workflows treat the post as "status unknown" rather than silently classifying it as free. On API failure (non-200, timeout, non-JSON) both fields are `null` and the pipeline continues.

This is opt-in and requires no additional authentication; the metadata endpoint is public.

**Why this matters:** If you have a paid subscription, CDP will fetch the full content of subscriber-only posts. The paywall metadata lets you build guardrails in your own workflows to avoid accidentally sharing or redistributing content that creators intended for paying subscribers only. Respect the creators whose work you value enough to pay for.

## Troubleshooting

### "No CDP connection"
- Make sure your browser launched with `--remote-debugging-port=9222`
- Check that no other process is using port 9222
- Try closing all Chrome/Brave windows and launching again

### "Missing modules" error
```bash
pip install -r requirements.txt
```

### URLs not being converted to wikilinks
- The tool only converts links to posts you've already downloaded
- Run a second pass to catch cross-references

### Rate limiting / bot detection
- Increase `--sleep-ms` (default: 150ms)
- Use smaller batches
- Substack shouldn't rate-limit authenticated sessions, but YMMV

## Advanced Options

```bash
python substack2md.py --help
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
  --timeout SECONDS        Page load timeout (default: 45)
  --retries N              Retry failed URLs N times (default: 2)
  --sleep-ms MS            Delay between requests (default: 150)
  --detect-paywall         Add is_paid/audience to frontmatter via Substack API
```

## Contributing

Pull requests welcome! Areas for improvement:
- Support for other platforms (Medium, Ghost, etc.)
- Better error handling
- Progress bars for batch processing
- Parallel processing option
- Export to other formats

## License

MIT License - see LICENSE file for details.

## Credits

Built with:
- [websocket-client](https://github.com/websocket-client/websocket-client)
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)
- [readability-lxml](https://github.com/buriy/python-readability)
- [markdownify](https://github.com/matthewwithanm/python-markdownify)

## Disclaimer

This tool is for personal archival purposes. Respect content creators' rights and Substack's terms of service. DON'T STEAL! STEALING IS BAD BAD BAD!!! Getting better utility from Substacks you already support is not. Sharing without permission is the line, don't cross it.
