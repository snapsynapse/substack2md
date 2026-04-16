"""CLI orchestration for substack2md.

process_url and process_from_md wire the core library pieces into
per-URL pipelines.  main() is the argparse-driven entry point registered
as the ``substack2md`` console script in pyproject.toml.
"""

import argparse
import datetime as dt
import logging
import os
import re
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Functions that tests monkeypatch must be looked up on the package
# module at call time so ``monkeypatch.setattr(substack2md, ...)`` takes
# effect inside process_url / process_from_md.  Importing the parent
# package here (instead of binding the names locally) achieves that.
from ._core import (
    TEASER_WORD_THRESHOLD,
    __version__,
    build_url_to_note_map,
    cleanup_url,
    collapse_blank_lines_in_lists,
    ensure_dir,
    get_publication_name,
    load_config,
    log,
    normalize_tags,
    remove_blank_after_headings,
    rewrite_internal_links,
    sanitize_filename,
    scrub_transcript_lines,
    slugify,
    with_frontmatter,
)


def _substack2md():
    """Return the top-level substack2md package, lazily imported to avoid
    a cycle when cli.py is imported during the package's own init."""
    import substack2md

    return substack2md


def process_url(
    url: str,
    base_dir: Path,
    pub_mappings: dict[str, str],
    also_save_html: bool,
    overwrite: bool,
    cdp_host: str,
    cdp_port: int,
    timeout: int,
    retries: int,
    detect_paywall: bool = False,
) -> Path | None:
    pkg = _substack2md()
    client = pkg.CDPClient(cdp_host, cdp_port, timeout=timeout)
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            html = client.fetch_html(url)
            fields, body_md = pkg.extract_article_fields(url, html)

            # Paywall detection via Substack public API
            if detect_paywall:
                pw_pub = fields["publication"]
                pw_slug = fields["slug"]
                # Custom-domain publications (e.g. stratechery.com) embed
                # the canonical `<sub>.substack.com/p/<slug>` URL in the
                # page.  Prefer that when available so the API call
                # reaches the right host.
                canon_pub, canon_slug = pkg.resolve_substack_canonical(html)
                if canon_pub:
                    pw_pub = canon_pub
                if canon_slug:
                    pw_slug = canon_slug
                pw = pkg.fetch_paywall_status(pw_pub, pw_slug, timeout=timeout)
                fields["is_paid"] = pw["is_paid"]
                fields["audience"] = pw["audience"]

                # If the post is paywalled and the extracted body is suspiciously
                # short, the user probably only captured the teaser.
                if pw["is_paid"] is True:
                    word_count = len(body_md.split())
                    if word_count < TEASER_WORD_THRESHOLD:
                        log.warning(
                            "teaser suspected: %s is paywalled (audience=%s) but "
                            "body is only %d words. You may need a paid subscription "
                            "in the CDP-connected browser to fetch the full text.",
                            url,
                            pw["audience"],
                            word_count,
                        )

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


def process_from_md(
    md_path: Path,
    base_dir: Path,
    pub_mappings: dict[str, str],
    url: str,
    overwrite: bool,
    detect_paywall: bool = False,
    paywall_timeout: float = 10.0,
) -> Path | None:
    raw = md_path.read_text(encoding="utf-8")
    m = re.search(r"^#\s+(.+)$", raw, flags=re.M)
    title = m.group(1).strip() if m else md_path.stem
    body_md = scrub_transcript_lines(raw)
    body_md = collapse_blank_lines_in_lists(body_md)
    body_md = remove_blank_after_headings(body_md)

    parts = urllib.parse.urlsplit(url)
    publication = parts.netloc.split(".")[0] if parts.netloc else "substack"
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

    if detect_paywall:
        pkg = _substack2md()
        pw = pkg.fetch_paywall_status(publication, slug, timeout=paywall_timeout)
        fields["is_paid"] = pw["is_paid"]
        fields["audience"] = pw["audience"]

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
        """,
    )
    ap.add_argument("urls", nargs="*", help="Substack post URLs")
    ap.add_argument("--urls-file", help="Path to a file containing URLs, one per line")
    ap.add_argument(
        "--from-md",
        dest="from_md",
        help="Clean an exported markdown file instead of fetching a URL",
    )
    ap.add_argument("--url", dest="raw_url", help="URL for the raw markdown when using --from-md")
    ap.add_argument(
        "--base-dir",
        help="Vault base directory (default: SUBSTACK2MD_BASE_DIR env or ~/Documents/substack-notes)",
    )
    ap.add_argument("--config", help="Path to config.yaml for publication mappings")
    ap.add_argument(
        "--also-save-html", action="store_true", help="Save sidecar HTML next to the .md"
    )
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    ap.add_argument("--cdp-host", default="127.0.0.1", help="CDP host")
    ap.add_argument("--cdp-port", type=int, default=9222, help="CDP port")
    ap.add_argument("--timeout", type=int, default=45, help="Per-page CDP timeout seconds")
    ap.add_argument("--retries", type=int, default=2, help="Retries per URL on transient failures")
    ap.add_argument("--sleep-ms", type=int, default=150, help="Sleep between URLs to be polite")
    ap.add_argument(
        "--detect-paywall",
        action="store_true",
        help="Query Substack API to add is_paid/audience to frontmatter. "
        "Helps avoid accidentally sharing subscriber-only content.",
    )
    ap.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity for diagnostics (default: INFO)",
    )
    ap.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress per-URL [ok]/[skip] progress lines (errors still shown)",
    )
    ap.add_argument("--version", action="version", version=f"substack2md {__version__}")
    ap.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable URL-completion state file. By default substack2md "
        "records each successfully written URL to a .state file in "
        "the output tree and skips already-completed URLs on the "
        "next run.",
    )
    ap.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Parallel worker threads (default: 1, sequential). "
        "Posts from the same publication are still serialized "
        "to avoid bot heuristics; parallelism is across different "
        "publications only.",
    )
    args = ap.parse_args()

    level = logging.WARNING if args.quiet else getattr(logging, args.log_level)
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    config = load_config(Path(args.config) if args.config else None)
    pub_mappings = config.get("publication_mappings", {})

    if args.base_dir:
        base_dir = Path(os.path.expanduser(args.base_dir))
    else:
        base_dir = Path(os.path.expanduser(config["base_dir"]))

    url_list = list(args.urls)
    if args.urls_file:
        with open(os.path.expanduser(args.urls_file), encoding="utf-8") as f:
            for line in f:
                u = line.strip()
                if u and not u.startswith("#"):
                    url_list.append(u)

    if args.from_md:
        if not args.raw_url:
            print("--url is required with --from-md")
            sys.exit(2)
        process_from_md(
            Path(args.from_md),
            base_dir,
            pub_mappings,
            args.raw_url,
            args.overwrite,
            detect_paywall=args.detect_paywall,
            paywall_timeout=args.timeout,
        )
        return

    if not url_list:
        ap.print_help()
        sys.exit(2)

    state = _substack2md().StateFile(base_dir) if not args.no_resume else None
    if state is not None:
        filtered = [u for u in url_list if not state.contains(u)]
        if len(filtered) < len(url_list):
            log.info(
                "resume: %d of %d URLs already completed; %d remaining",
                len(url_list) - len(filtered),
                len(url_list),
                len(filtered),
            )
        url_list = filtered

    host_locks: dict[str, threading.Lock] = {}
    host_locks_mutex = threading.Lock()

    def host_lock(host: str) -> threading.Lock:
        with host_locks_mutex:
            lock = host_locks.get(host)
            if lock is None:
                lock = threading.Lock()
                host_locks[host] = lock
            return lock

    completed = 0
    completed_lock = threading.Lock()

    pkg = _substack2md()

    def worker(url: str) -> None:
        nonlocal completed
        if "substack.com" not in url:
            log.warning("Not a substack URL: %s", url)
        host = urllib.parse.urlsplit(url).netloc
        with host_lock(host):
            # Look up process_url via the package so tests that
            # monkeypatch substack2md.process_url are honored.
            out = pkg.process_url(
                url,
                base_dir,
                pub_mappings,
                args.also_save_html,
                args.overwrite,
                args.cdp_host,
                args.cdp_port,
                args.timeout,
                args.retries,
                detect_paywall=args.detect_paywall,
            )
            if out is not None and state is not None:
                state.record(url)
            if args.sleep_ms > 0:
                time.sleep(args.sleep_ms / 1000.0)
        with completed_lock:
            completed += 1

    try:
        if args.concurrency <= 1:
            for url in url_list:
                worker(url)
        else:
            with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                futures = [pool.submit(worker, u) for u in url_list]
                for fut in as_completed(futures):
                    try:
                        fut.result()
                    except Exception as exc:
                        log.error("worker crashed: %s", exc)
    except KeyboardInterrupt:
        log.warning(
            "interrupted: %d of %d URLs processed this run; rerun the same command to resume",
            completed,
            len(url_list),
        )
        sys.exit(130)
