#!/usr/bin/env python3
r"""
substack2md
Convert Substack posts to Markdown using your live browser session (CDP).

Highlights:
- Uses your authenticated Brave/Chrome window. No passwords saved.
- Handles single URLs, newline-separated URL files, and "from raw markdown" cleanup.
- Sequential by design with configurable sleeps to avoid bot heuristics.
- Rewrites links to existing notes as Obsidian wikilinks [[YYYY-MM-DD-slug]].
- Configurable publication name mappings via config file or environment.

Dependencies:
  pip install -r requirements.txt

Brave launch (recommended):
  open -na "Brave Browser" --args \
    --remote-debugging-port=9222 \
    --remote-allow-origins=http://127.0.0.1:9222 \
    --user-data-dir="$HOME/.brave-cdp-profile"

Chrome launch (Apple Silicon safe):
  arch -arm64 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome \
    --remote-debugging-port=9222 \
    --remote-allow-origins=http://127.0.0.1:9222 \
    --user-data-dir="$HOME/.chrome-cdp-profile"

Configuration:
  Set environment variables:
    SUBSTACK2MD_BASE_DIR - Default output directory
    SUBSTACK2MD_CONFIG - Path to config.yaml for publication mappings
  
  Or create config.yaml in the same directory as this script:
    publication_mappings:
      natesnewsletter: Nates_Notes
      daveshap: David_Shapiro

Usage examples:
  # Single URL
  python substack2md.py https://natesnewsletter.substack.com/p/post-slug --base-dir ~/notes

  # Batch from a file of URLs (one per line)
  python substack2md.py --urls-file urls.txt --base-dir ~/notes --sleep-ms 250
  
  # Using environment variable for base directory
  export SUBSTACK2MD_BASE_DIR=~/notes
  python substack2md.py https://daveshap.substack.com/p/post-slug
"""

import argparse
import datetime as dt
import json
import logging
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Dict, Optional, Tuple, List

__version__ = "1.2.0"

log = logging.getLogger("substack2md")

# Body-word count below which a paywalled post is probably just the teaser.
# Tuned to the short end of typical Substack teasers (~200-400 words).
TEASER_WORD_THRESHOLD = 300

# Friendly dependency check so ImportError doesn't look mysterious
_MISSING = []
def _need(mod, pip_name=None):
    try:
        __import__(mod)
    except Exception:
        _MISSING.append(pip_name or mod)

for _mod, _pip in [
    ("websocket", "websocket-client"),
    ("bs4", "beautifulsoup4"),
    ("lxml", "lxml"),
    ("readability", "readability-lxml"),
    ("markdownify", "markdownify"),
    ("yaml", "pyyaml"),
    ("requests", "requests"),
]:
    _need(_mod, _pip)

if _MISSING:
    print("[deps] Missing modules:", ", ".join(_MISSING))
    print("Run:\n  pip install " + " ".join(_MISSING))
    sys.exit(1)

import yaml
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md_convert
from readability import Document
from websocket import create_connection

# --------------------------
# Configuration
# --------------------------

def load_config(config_path: Optional[Path] = None) -> Dict:
    """Load configuration from file or environment."""
    config = {
        "publication_mappings": {},
        "base_dir": os.getenv("SUBSTACK2MD_BASE_DIR", "~/Documents/substack-notes"),
    }
    
    # Try to load config file
    if config_path is None:
        # Check environment variable
        env_config = os.getenv("SUBSTACK2MD_CONFIG")
        if env_config:
            config_path = Path(env_config)
        else:
            # Check for config.yaml in script directory
            script_dir = Path(__file__).parent
            config_path = script_dir / "config.yaml"
    
    if config_path and config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
                if "publication_mappings" in user_config:
                    config["publication_mappings"] = user_config["publication_mappings"]
                if "base_dir" in user_config:
                    config["base_dir"] = user_config["base_dir"]
        except Exception as e:
            log.warning("Could not load config from %s: %s", config_path, e)
    
    return config

def get_publication_name(publication_slug: str, mappings: Dict[str, str]) -> str:
    """
    Get the formatted publication name, using custom mappings if available.
    
    Args:
        publication_slug: The raw publication slug (e.g., 'mysubstack')
        mappings: Dictionary of custom publication name mappings
    
    Returns:
        Formatted publication name suitable for directory names
    """
    if publication_slug in mappings:
        return mappings[publication_slug]
    # Default: Title case with underscores
    return publication_slug.title().replace(" ", "_")

# --------------------------
# Utilities
# --------------------------

def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text

def sanitize_filename(text: str) -> str:
    return text.replace("/", "-").replace("\\", "-")

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def normalize_tags(tags: List[str]) -> List[str]:
    out = []
    for t in tags or []:
        t = str(t).strip().lower()
        t = re.sub(r"\s+", "-", t)
        if t and t not in out:
            out.append(t)
    if "substack" not in out:
        out.insert(0, "substack")
    return out

SUBSTACK_HOST_RE = re.compile(r"https?://([a-z0-9-]+)\.substack\.com/p/([^/?#]+)", re.I)

def resolve_substack_canonical(html: str) -> Tuple[Optional[str], Optional[str]]:
    """Find the canonical `<publication>.substack.com/p/<slug>` URL in a page.

    Substack publications with custom domains (e.g. stratechery.com) still
    embed the canonical Substack URL in `<link rel="canonical">` or
    `<meta property="og:url">`.  Returns ``(publication, slug)`` when found,
    else ``(None, None)``.  The caller can fall back to its original
    derivation if nothing matches.
    """
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return (None, None)

    candidates = []
    link = soup.find("link", attrs={"rel": "canonical"})
    if link and link.get("href"):
        candidates.append(link["href"])
    og = soup.find("meta", attrs={"property": "og:url"})
    if og and og.get("content"):
        candidates.append(og["content"])
    # ld+json may include a Substack URL in "@id" or "mainEntityOfPage"
    ld = parse_ld_json(soup)
    for key in ("@id", "mainEntityOfPage", "url"):
        v = ld.get(key)
        if isinstance(v, str):
            candidates.append(v)
        elif isinstance(v, dict) and isinstance(v.get("@id"), str):
            candidates.append(v["@id"])

    for href in candidates:
        m = SUBSTACK_HOST_RE.search(href)
        if m:
            return (m.group(1).lower(), m.group(2))
    return (None, None)


def fetch_paywall_status(publication: str, slug: str, timeout: float = 10.0) -> Dict:
    """Query Substack's public API for paywall/audience metadata.

    Substack exposes ``/api/v1/posts/{slug}`` on every publication subdomain.
    The response includes *is_paid* (bool) and *audience* (str) which indicate
    whether the post is behind a paywall.  No authentication is required for
    this metadata endpoint.

    Returns a dict with ``is_paid`` and ``audience`` keys.  On any failure the
    values default to ``None`` so that the caller can distinguish "not checked"
    from "checked and free".
    """
    # Substack classifies every post with an `audience` enum.  Authors can
    # rename their subscription *tiers* in the UI (e.g. label a paid tier
    # "Supporters" or "Founders' Circle"), but the API normalizes those to
    # a fixed set of values used by Substack's own gating logic.
    #
    # Known enum values (verified empirically across 9 publications /
    # 120+ posts, plus Substack API documentation):
    #   "everyone"   - public, free to read
    #   "only_free"  - requires any subscription (free OK), not paywalled
    #   "only_paid"  - requires a paid subscription
    #   "founding"   - requires founding-member subscription (paid)
    #
    # If Substack adds new tiers, we DO NOT assume free.  We return
    # (is_paid=None, audience=<raw value>) so downstream workflows can
    # treat the post as "status unknown" instead of silently publishing
    # it as free.  That's the safer default for a flag whose purpose is
    # to avoid accidental redistribution of subscriber-only content.
    known_paid = {"only_paid", "founding"}
    known_free = {"everyone", "only_free"}

    result: Dict = {"is_paid": None, "audience": None}
    api_url = f"https://{publication}.substack.com/api/v1/posts/{slug}"
    try:
        resp = requests.get(api_url, headers={"Accept": "application/json",
                                               "User-Agent": f"substack2md/{__version__}"},
                            timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            audience = data.get("audience")
            if audience is None:
                # 200 OK but no audience field -- can't tell; stay None/None
                # so downstream treats this as "not checked" rather than "free".
                log.warning("paywall: 200 OK but no 'audience' field for %s", api_url)
            elif audience in known_paid:
                result["audience"] = audience
                result["is_paid"] = True
            elif audience in known_free:
                result["audience"] = audience
                result["is_paid"] = False
            else:
                # Unknown enum value: preserve the raw string for debuggability
                # but refuse to guess is_paid.  Log so maintainers can widen
                # the enum sets if Substack adds new tiers.
                result["audience"] = audience
                log.warning("paywall: unknown audience %r for %s; is_paid left as None",
                            audience, api_url)
        else:
            log.warning("paywall: API returned %s for %s", resp.status_code, api_url)
    except Exception as exc:
        log.warning("paywall: could not query %s: %s", api_url, exc)
    return result


def cleanup_url(url: str) -> str:
    if not url:
        return url
    parts = urllib.parse.urlsplit(url)
    # remove all query params by default
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))

TIME_RE = re.compile(r"^\[?\d{1,2}:\d{2}(?::\d{2})?\]?$")
SPEAKER_RE = re.compile(r"^\s*(speaker\s*\d+|host|guest)\s*[:\-]", re.I)

def scrub_transcript_lines(md: str) -> str:
    lines = md.splitlines()
    out = []
    for line in lines:
        s = line.strip()
        if TIME_RE.match(s):
            continue
        if SPEAKER_RE.match(s):
            continue
        line = re.sub(r"^\s*\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*", "", line)
        out.append(line)
    return "\n".join(out)

def remove_blank_after_headings(md: str) -> str:
    # No blank line immediately after a heading
    lines = md.splitlines()
    out = []
    for i, line in enumerate(lines):
        if out and out[-1].lstrip().startswith("#") and line.strip() == "":
            continue
        out.append(line)
    return "\n".join(out)

def collapse_blank_lines_in_lists(md: str) -> str:
    # Remove blank lines between bullets; keep other spacing intact
    lines = md.splitlines()
    out = []
    for i, line in enumerate(lines):
        if line.strip() == "" and i+1 < len(lines):
            nxt = lines[i+1].strip()
            prev = lines[i-1].strip() if i > 0 else ""
            if (nxt.startswith(("-", "*", "\t-","\t*")) and (prev.startswith(("-", "*", "\t-","\t*")) or prev.endswith(":") or prev.startswith("#"))):
                continue
        out.append(line)
    md2 = "\n".join(out)
    md2 = re.sub(r"\n{3,}", "\n\n", md2)
    return md2

def img_to_link(html: str) -> str:
    # Convert images and iframes to plain links; drop headers/footers/asides
    soup = BeautifulSoup(html, "lxml")
    for fig in soup.find_all("figure"):
        cap = fig.find("figcaption")
        caption_text = cap.get_text(" ", strip=True) if cap else ""
        if cap:
            cap.decompose()
        img = fig.find("img")
        if img:
            alt = img.get("alt") or "image"
            src = img.get("src") or ""
            a = soup.new_tag("a", href=src); a.string = alt
            fig.clear(); fig.append(a)
            if caption_text:
                em = soup.new_tag("em"); em.string = f" {caption_text}"
                fig.append(em)
    for img in soup.find_all("img"):
        alt = img.get("alt") or "image"
        src = img.get("src") or ""
        a = soup.new_tag("a", href=src); a.string = alt
        img.replace_with(a)
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src") or ""
        a = soup.new_tag("a", href=src); a.string = src or "embed"
        iframe.replace_with(a)
    for sel in ["header","footer","aside"]:
        for tag in soup.find_all(sel):
            tag.decompose()
    return str(soup)

def html_to_markdown_clean(html: str) -> str:
    html2 = img_to_link(html)
    md = md_convert(html2, strip=["script", "style"], heading_style="ATX")
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip() + "\n"

def parse_ld_json(soup: BeautifulSoup) -> Dict:
    data = {}
    for tag in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            j = json.loads(tag.string or "{}")
            items = j if isinstance(j, list) else [j]
            for item in items:
                if isinstance(item, dict) and item.get("@type") in ("Article","NewsArticle","BlogPosting"):
                    data = item
                    break
        except Exception:
            continue
    return data

def extract_article_fields(url: str, html: str) -> Tuple[Dict, str]:
    soup = BeautifulSoup(html, "lxml")
    ld = parse_ld_json(soup)

    title = (ld.get("headline") if ld else None) or (soup.find("h1").get_text(strip=True) if soup.find("h1") else "")
    subtitle = ""
    sub = soup.find("h3")
    if sub:
        subtitle = sub.get_text(strip=True)

    netloc = urllib.parse.urlsplit(url).netloc
    publication = netloc.split(".")[0] if netloc else "substack"

    author = ""
    if ld:
        a = ld.get("author")
        if isinstance(a, dict):
            author = a.get("name") or ""
        elif isinstance(a, list) and len(a) > 0:
            author = a[0].get("name") if isinstance(a[0], dict) else str(a[0])
        else:
            author = str(a) if a else ""
    if not author:
        meta = soup.find("meta", attrs={"name": "author"})
        if meta:
            author = meta.get("content","")

    date_pub = (ld.get("datePublished") if ld else None) or ""
    date_mod = (ld.get("dateModified") if ld else None) or ""
    retrieved = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    img_url = (ld.get("image") if ld else None) or ""
    if isinstance(img_url, dict):
        img_url = img_url.get("url") or ""
    elif isinstance(img_url, list):
        img_url = img_url[0] if img_url else ""

    # parse ISO dates
    def parse_iso(s):
        if not s:
            return None
        try:
            d = dt.datetime.fromisoformat(s.replace("Z",""))
            return d.date().isoformat()
        except Exception:
            return None

    date_pub = parse_iso(date_pub) or dt.date.today().isoformat()
    date_mod = parse_iso(date_mod)

    slug = slugify(urllib.parse.urlsplit(url).path.split("/")[-1] or title)

    # find article body
    doc = Document(html)
    body_html = doc.summary()
    body_md = html_to_markdown_clean(body_html)

    body_md = scrub_transcript_lines(body_md)
    body_md = collapse_blank_lines_in_lists(body_md)
    body_md = remove_blank_after_headings(body_md)

    # Tag extraction walks three sources, each more authoritative than the
    # last.  We merge rather than pick so a post tagged by the author via
    # both meta keywords and ld+json keeps all of them.
    tags: List[str] = []

    # 1. <meta name="keywords"> -- classic, comma-separated
    meta_kw = soup.find("meta", attrs={"name": "keywords"})
    if meta_kw:
        kw = meta_kw.get("content") or ""
        tags.extend(x.strip() for x in kw.split(",") if x.strip())

    # 2. ld+json "keywords" -- Substack populates this; can be list or string
    if ld:
        kw = ld.get("keywords")
        if isinstance(kw, list):
            tags.extend(str(x).strip() for x in kw if str(x).strip())
        elif isinstance(kw, str):
            tags.extend(x.strip() for x in kw.split(",") if x.strip())

    # 3. ld+json "articleSection" -- Substack's section/category name
    section = ld.get("articleSection") if ld else None
    if isinstance(section, str) and section.strip():
        tags.append(section.strip())
    elif isinstance(section, list):
        tags.extend(str(x).strip() for x in section if str(x).strip())

    tags = normalize_tags(tags)

    video_url = ""
    v = soup.find("video")
    if v:
        src = v.get("src")
        if src:
            video_url = src

    fields = {
        "title": title,
        "subtitle": subtitle,
        "author": author,
        "publication": publication,
        "published": date_pub,
        "updated": date_mod,
        "retrieved": retrieved,
        "url": cleanup_url(url),
        "canonical": cleanup_url(url),
        "slug": slug,
        "image": img_url,
        "tags": tags,
        "video_url": video_url,
    }
    return fields, body_md

# --------------------------
# CDP Client
# --------------------------

class CDPClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 9222, timeout: int = 45):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.ws = None
        self.msg_id = 0

    def connect(self):
        resp = requests.get(f"http://{self.host}:{self.port}/json/version")
        ws_url = resp.json()["webSocketDebuggerUrl"]
        self.ws = create_connection(ws_url, timeout=self.timeout)

    def send(self, method: str, params: Optional[Dict] = None, sessionId: Optional[str] = None):
        if not self.ws:
            self.connect()
        self.msg_id += 1
        msg = {"id": self.msg_id, "method": method, "params": params or {}}
        if sessionId:
            msg["sessionId"] = sessionId
        self.ws.send(json.dumps(msg))
        while True:
            raw = self.ws.recv()
            obj = json.loads(raw)
            if obj.get("id") == self.msg_id:
                if "error" in obj:
                    raise RuntimeError(f"{method} error: {obj['error']}")
                return obj.get("result", {})

    def recv_event_until(self, event: str, sessionId: Optional[str], timeout: int):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                raw = self.ws.recv()
                obj = json.loads(raw)
                if "method" in obj and obj["method"] == event:
                    if sessionId is None or obj.get("sessionId") == sessionId:
                        return obj
            except Exception:
                continue
        raise TimeoutError(f"Timeout waiting for {event}")

    def fetch_html(self, url: str) -> str:
        res = self.send("Target.createTarget", {"url": "about:blank"})
        targetId = res.get("targetId")
        if not targetId:
            raise RuntimeError("Could not create target")
        try:
            res = self.send("Target.attachToTarget", {"targetId": targetId, "flatten": True})
            sessionId = res.get("sessionId")
            if not sessionId:
                raise RuntimeError("Failed to attach to target")
            self.send("Page.enable", sessionId=sessionId)
            self.send("Page.navigate", {"url": url}, sessionId=sessionId)
            try:
                self.recv_event_until("Page.loadEventFired", sessionId=sessionId, timeout=self.timeout)
            except TimeoutError:
                pass
            res = self.send("Runtime.evaluate", {
                "expression": "document.documentElement.outerHTML",
                "returnByValue": True
            }, sessionId=sessionId)
            return res.get("result", {}).get("value", "")
        finally:
            # Always close the Chrome target, even if navigation or eval
            # raised. Leaked targets accumulate during long batches.
            try:
                self.send("Target.closeTarget", {"targetId": targetId})
            except Exception:
                pass

# --------------------------
# Link rewriting against vault
# --------------------------

def build_url_to_note_map(base_dir: Path) -> Dict[str, Path]:
    url_map = {}
    for p in base_dir.rglob("*.md"):
        try:
            with p.open("r", encoding="utf-8") as f:
                head = f.read(4096)
            if head.startswith("---"):
                end = head.find("\n---", 3)
                if end != -1:
                    fm = yaml.safe_load(head[3:end])
                    if isinstance(fm, dict) and fm.get("url"):
                        cleaned = cleanup_url(str(fm["url"]))
                        url_map[cleaned] = p
        except Exception:
            continue
    return url_map

LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\)]+)\)")

def rewrite_internal_links(md: str, url_map: Dict[str, Path]) -> Tuple[str, int, int]:
    internal, external = 0, 0
    def repl(m):
        nonlocal internal, external
        text = m.group(1)
        url = cleanup_url(m.group(2))
        if url in url_map:
            name = url_map[url].stem
            internal += 1
            return f"[[{name}]]"
        else:
            external += 1
            return f"[{text}]({url})"
    md2 = LINK_RE.sub(repl, md)
    return md2, internal, external

# --------------------------
# Frontmatter
# --------------------------

def with_frontmatter(fields: Dict, body_md: str) -> str:
    fm = {
        "title": fields["title"],
        "subtitle": fields["subtitle"] or "",
        "author": fields["author"] or "",
        "publication": fields["publication"],
        "published": fields["published"],
        "updated": fields["updated"],
        "retrieved": fields["retrieved"],
        "url": fields["url"],
        "canonical": fields["canonical"],
        "slug": fields["slug"],
        "tags": fields["tags"],
        "image": fields["image"] or "",
        "video_url": fields.get("video_url","") or "",
        "is_paid": fields.get("is_paid"),
        "audience": fields.get("audience"),
        "links_internal": fields.get("links_internal",0),
        "links_external": fields.get("links_external",0),
        "source": fields.get("source", f"substack2md v{__version__}"),
    }
    fm = {k:v for k,v in fm.items() if v is not None}
    front = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{front}\n---\n\n{body_md}"

# --------------------------
# Main pipeline
# --------------------------

def process_url(url: str, base_dir: Path, pub_mappings: Dict[str, str], 
                also_save_html: bool, overwrite: bool,
                cdp_host: str, cdp_port: int, timeout: int, retries: int,
                detect_paywall: bool = False) -> Optional[Path]:
    client = CDPClient(cdp_host, cdp_port, timeout=timeout)
    last_err = None
    for attempt in range(1, retries+1):
        try:
            html = client.fetch_html(url)
            fields, body_md = extract_article_fields(url, html)

            # Paywall detection via Substack public API
            if detect_paywall:
                pw_pub = fields["publication"]
                pw_slug = fields["slug"]
                # Custom-domain publications (e.g. stratechery.com) embed
                # the canonical `<sub>.substack.com/p/<slug>` URL in the
                # page.  Prefer that when available so the API call
                # reaches the right host.
                canon_pub, canon_slug = resolve_substack_canonical(html)
                if canon_pub:
                    pw_pub = canon_pub
                if canon_slug:
                    pw_slug = canon_slug
                pw = fetch_paywall_status(pw_pub, pw_slug, timeout=timeout)
                fields["is_paid"] = pw["is_paid"]
                fields["audience"] = pw["audience"]

                # If the post is paywalled and the extracted body is suspiciously
                # short, the user probably only captured the teaser.  Readability
                # won't tell you this on its own; pair it with the paywall signal
                # and warn so downstream workflows know the .md is incomplete.
                if pw["is_paid"] is True:
                    word_count = len(body_md.split())
                    if word_count < TEASER_WORD_THRESHOLD:
                        log.warning(
                            "teaser suspected: %s is paywalled (audience=%s) but "
                            "body is only %d words. You may need a paid subscription "
                            "in the CDP-connected browser to fetch the full text.",
                            url, pw["audience"], word_count,
                        )

            # Use configurable publication name mapping
            pub_pretty = get_publication_name(fields["publication"], pub_mappings)
            
            target_dir = base_dir / pub_pretty
            ensure_dir(target_dir)
            fname = f"{fields['published']}-{fields['slug']}.md"
            out_path = target_dir / sanitize_filename(fname)
            if out_path.exists() and not overwrite:
                log.info("skip: exists %s", out_path)
                return None
            url_map = build_url_to_note_map(base_dir)
            body_md, internal, external = rewrite_internal_links(body_md, url_map)
            fields["links_internal"] = internal
            fields["links_external"] = external
            md_full = with_frontmatter(fields, body_md)
            out_path.write_text(md_full, encoding="utf-8")
            log.info("ok: %s -> %s", url, out_path)
            if also_save_html:
                out_path.with_suffix(".html").write_text(html, encoding="utf-8")
            return out_path
        except Exception as e:
            last_err = e
            time.sleep(0.6 * attempt)  # simple backoff
    log.error("fail: %s (%s)", url, last_err)
    return None

def process_from_md(md_path: Path, base_dir: Path, pub_mappings: Dict[str, str],
                    url: str, overwrite: bool,
                    detect_paywall: bool = False,
                    paywall_timeout: float = 10.0) -> Optional[Path]:
    raw = md_path.read_text(encoding="utf-8")
    m = re.search(r"^#\s+(.+)$", raw, flags=re.M)
    title = m.group(1).strip() if m else md_path.stem
    body_md = scrub_transcript_lines(raw)
    body_md = collapse_blank_lines_in_lists(body_md)
    body_md = remove_blank_after_headings(body_md)

    parts = urllib.parse.urlsplit(url)
    publication = (parts.netloc.split(".")[0] if parts.netloc else "substack")
    slug = slugify(parts.path.split("/")[-1] or title)
    today = dt.date.today().isoformat()

    fields = {
        "title": title,
        "subtitle": "",
        "author": "",
        "publication": publication,
        "published": today,
        "updated": None,
        "retrieved": today,
        "url": cleanup_url(url),
        "canonical": cleanup_url(url),
        "slug": slug,
        "image": "",
        "tags": normalize_tags([]),
        "video_url": "",
        "links_internal": 0,
        "links_external": 0,
        "source": f"substack2md v{__version__}",
    }

    # Paywall detection works the same way as on the live path: query the
    # Substack public API by (publication, slug) derived from the URL.
    # Useful when backfilling is_paid/audience across an existing archive.
    if detect_paywall:
        pw = fetch_paywall_status(publication, slug, timeout=paywall_timeout)
        fields["is_paid"] = pw["is_paid"]
        fields["audience"] = pw["audience"]

    # Use configurable publication name mapping
    pub_pretty = get_publication_name(publication, pub_mappings)
    
    target_dir = base_dir / pub_pretty
    ensure_dir(target_dir)

    fname = f"{fields['published']}-{fields['slug']}.md"
    out_path = target_dir / sanitize_filename(fname)

    if out_path.exists() and not overwrite:
        log.info("skip: exists %s", out_path)
        return None

    md_full = with_frontmatter(fields, body_md)
    out_path.write_text(md_full, encoding="utf-8")
    log.info("ok: %s -> %s", url, out_path)
    return out_path

def main():
    ap = argparse.ArgumentParser(
        description="Convert Substack posts to Markdown using your logged-in Brave/Chrome session via CDP.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment variables:
  SUBSTACK2MD_BASE_DIR    Default base directory for output
  SUBSTACK2MD_CONFIG      Path to config.yaml file
        """
    )
    ap.add_argument("urls", nargs="*", help="Substack post URLs")
    ap.add_argument("--urls-file", help="Path to a file containing URLs, one per line")
    ap.add_argument("--from-md", dest="from_md", help="Clean an exported markdown file instead of fetching a URL")
    ap.add_argument("--url", dest="raw_url", help="URL for the raw markdown when using --from-md")
    ap.add_argument("--base-dir", help="Vault base directory (default: SUBSTACK2MD_BASE_DIR env or ~/Documents/substack-notes)")
    ap.add_argument("--config", help="Path to config.yaml for publication mappings")
    ap.add_argument("--also-save-html", action="store_true", help="Save sidecar HTML next to the .md")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    ap.add_argument("--cdp-host", default="127.0.0.1", help="CDP host")
    ap.add_argument("--cdp-port", type=int, default=9222, help="CDP port")
    ap.add_argument("--timeout", type=int, default=45, help="Per-page CDP timeout seconds")
    ap.add_argument("--retries", type=int, default=2, help="Retries per URL on transient failures")
    ap.add_argument("--sleep-ms", type=int, default=150, help="Sleep between URLs to be polite")
    ap.add_argument("--detect-paywall", action="store_true",
                    help="Query Substack API to add is_paid/audience to frontmatter. "
                         "Helps avoid accidentally sharing subscriber-only content.")
    ap.add_argument("--log-level", default="INFO",
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                    help="Logging verbosity for diagnostics (default: INFO)")
    ap.add_argument("--quiet", "-q", action="store_true",
                    help="Suppress per-URL [ok]/[skip] progress lines (errors still shown)")
    ap.add_argument("--version", action="version", version=f"substack2md {__version__}")
    args = ap.parse_args()

    # --quiet elevates the threshold to WARNING so per-URL progress (INFO)
    # is hidden; errors still surface.  --log-level DEBUG reveals the chatty
    # internals (ld+json parses, CDP frames, etc.).
    level = logging.WARNING if args.quiet else getattr(logging, args.log_level)
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    # Load configuration
    config = load_config(Path(args.config) if args.config else None)
    pub_mappings = config.get("publication_mappings", {})
    
    # Determine base directory
    if args.base_dir:
        base_dir = Path(os.path.expanduser(args.base_dir))
    else:
        base_dir = Path(os.path.expanduser(config["base_dir"]))

    # Collect URLs
    url_list = list(args.urls)
    if args.urls_file:
        with open(os.path.expanduser(args.urls_file), "r", encoding="utf-8") as f:
            for line in f:
                u = line.strip()
                if u and not u.startswith("#"):
                    url_list.append(u)

    if args.from_md:
        if not args.raw_url:
            print("--url is required with --from-md")
            sys.exit(2)
        process_from_md(Path(args.from_md), base_dir, pub_mappings,
                        args.raw_url, args.overwrite,
                        detect_paywall=args.detect_paywall,
                        paywall_timeout=args.timeout)
        return

    if not url_list:
        ap.print_help()
        sys.exit(2)

    for i, url in enumerate(url_list, 1):
        if "substack.com" not in url:
            log.warning("Not a substack URL: %s", url)
        process_url(url, base_dir, pub_mappings, args.also_save_html, args.overwrite, 
                   args.cdp_host, args.cdp_port, args.timeout, args.retries,
                   detect_paywall=args.detect_paywall)
        if i < len(url_list) and args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000.0)

if __name__ == "__main__":
    main()
