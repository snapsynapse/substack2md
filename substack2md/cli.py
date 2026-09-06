"""CLI orchestration for substack2md.

process_url and process_from_md wire the core library pieces into
per-URL pipelines.  main() is the argparse-driven entry point registered
as the ``substack2md`` console script in pyproject.toml.
"""

import argparse
import datetime as dt
import json
import logging
import os
import re
import sys
import tempfile
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

# Functions that tests monkeypatch must be looked up on the package
# module at call time so ``monkeypatch.setattr(substack2md, ...)`` takes
# effect inside process_url / process_from_md.  Importing the parent
# package here (instead of binding the names locally) achieves that.
from ._core import (
    TEASER_WORD_THRESHOLD,
    UnsafeOutputPathError,
    __version__,
    build_url_to_note_map,
    cleanup_url,
    collapse_blank_lines_in_lists,
    ensure_dir,
    get_publication_name,
    load_config,
    log,
    normalize_tags,
    publication_output_dir,
    remove_blank_after_headings,
    rewrite_internal_links,
    sanitize_filename,
    scrub_transcript_lines,
    url_slug,
    with_frontmatter,
)


def _substack2md():
    """Return the top-level substack2md package, lazily imported to avoid
    a cycle when cli.py is imported during the package's own init."""
    import substack2md

    return substack2md


@dataclass(frozen=True)
class ConversionResult:
    """Detailed pipeline outcome; legacy callers still receive Path or None."""

    status: str
    path: Path | None = None
    error: str | None = None


def _pending_path(note: Path) -> Path:
    return note.with_name(f".{note.name}.pending")


def _write_artifacts(artifacts: dict[Path, str]) -> None:
    """Stage writes and leave a recovery marker until all replacements succeed.

    Each replacement is atomic. The marker makes an interrupted multi-file
    capture retryable, including when old files already exist at both paths.
    """
    staged = []
    note = next(reversed(artifacts)).with_suffix(".md")
    marker = _pending_path(note)
    try:
        for path, content in artifacts.items():
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                staged.append((temporary, path))
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        # Replace the marker rather than following a preexisting symlink.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=note.parent,
            prefix=f".{note.name}.marker.",
            delete=False,
        ) as handle:
            marker_temp = Path(handle.name)
            staged.append((marker_temp, marker))
            json.dump([path.name for path in artifacts], handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(marker_temp, marker)
        for temporary, path in staged[:-1]:
            os.replace(temporary, path)
        marker.unlink()
    finally:
        for temporary, _ in staged:
            temporary.unlink(missing_ok=True)


def _legacy_result(result: ConversionResult, detailed: bool):
    return result if detailed else (result.path if result.status == "written" else None)


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
    *,
    detailed: bool = False,
    url_map: dict[str, Path] | None = None,
) -> Path | None | ConversionResult:
    pkg = _substack2md()
    last_err = None
    for attempt in range(1, retries + 1):
        client = pkg.CDPClient(cdp_host, cdp_port, timeout=timeout)
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

            target_dir = publication_output_dir(base_dir, pub_pretty)
            ensure_dir(target_dir)
            fname = f"{fields['published']}-{fields['slug']}.md"
            out_path = target_dir / sanitize_filename(fname)
            if out_path.is_symlink() or (out_path.exists() and not out_path.is_file()):
                raise UnsafeOutputPathError(f"output is not a regular archive file: {out_path}")
            pending = _pending_path(out_path)
            if pending.is_symlink():
                raise UnsafeOutputPathError(f"recovery marker is a symlink: {pending}")
            recovering = pending.exists()
            if recovering:
                try:
                    requested = json.loads(pending.read_text(encoding="utf-8"))
                    also_save_html = (
                        also_save_html or out_path.with_suffix(".html").name in requested
                    )
                except (OSError, ValueError, TypeError):
                    # A damaged marker is incomplete work, never successful state.
                    also_save_html = True
            if out_path.exists() and not overwrite and not recovering:
                sidecar = out_path.with_suffix(".html")
                if also_save_html and not sidecar.is_file():
                    _write_artifacts({sidecar: html})
                    return _legacy_result(ConversionResult("written", out_path), detailed)
                log.info("skip: exists %s", out_path)
                return _legacy_result(ConversionResult("skipped", out_path), detailed)
            index = build_url_to_note_map(base_dir) if url_map is None else url_map
            body_md, internal, external = rewrite_internal_links(body_md, index, base_dir=base_dir)
            fields["links_internal"] = internal
            fields["links_external"] = external
            md_full = with_frontmatter(fields, body_md)
            artifacts = {}
            if also_save_html:
                artifacts[out_path.with_suffix(".html")] = html
            artifacts[out_path] = md_full
            _write_artifacts(artifacts)
            log.info("ok: %s -> %s", url, out_path)
            return _legacy_result(ConversionResult("written", out_path), detailed)
        except UnsafeOutputPathError as e:
            log.error("fail: %s (%s)", url, e)
            return _legacy_result(ConversionResult("failed", error=str(e)), detailed)
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.6 * attempt)
        finally:
            close = getattr(client, "close", None)
            if close:
                try:
                    close()
                except Exception as exc:
                    log.warning("CDP connection cleanup failed: %s", exc)
    log.error("fail: %s (%s)", url, last_err)
    return _legacy_result(ConversionResult("failed", error=str(last_err)), detailed)


def process_from_md(
    md_path: Path,
    base_dir: Path,
    pub_mappings: dict[str, str],
    url: str,
    overwrite: bool,
    detect_paywall: bool = False,
    paywall_timeout: float = 10.0,
    *,
    detailed: bool = False,
) -> Path | None | ConversionResult:
    raw = md_path.read_text(encoding="utf-8")
    m = re.search(r"^#\s+(.+)$", raw, flags=re.M)
    title = m.group(1).strip() if m else md_path.stem
    body_md = scrub_transcript_lines(raw)
    body_md = collapse_blank_lines_in_lists(body_md)
    body_md = remove_blank_after_headings(body_md)

    parts = urllib.parse.urlsplit(url)
    publication = parts.netloc.split(".")[0] if parts.netloc else "substack"
    slug = url_slug(url, title)
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

    target_dir = publication_output_dir(base_dir, pub_pretty)
    ensure_dir(target_dir)

    fname = f"{fields['published']}-{fields['slug']}.md"
    out_path = target_dir / sanitize_filename(fname)

    if out_path.is_symlink() or (out_path.exists() and not out_path.is_file()):
        raise UnsafeOutputPathError(f"output is not a regular archive file: {out_path}")
    pending = _pending_path(out_path)
    if pending.is_symlink():
        raise UnsafeOutputPathError(f"recovery marker is a symlink: {pending}")
    if pending.exists():
        try:
            requested = json.loads(pending.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError("Damaged recovery marker; rerun the original URL capture") from exc
        if out_path.with_suffix(".html").name in requested:
            raise ValueError("Incomplete HTML capture; rerun the original URL capture to recover")
    if out_path.exists() and not overwrite and not pending.exists():
        log.info("skip: exists %s", out_path)
        return _legacy_result(ConversionResult("skipped", out_path), detailed)

    md_full = with_frontmatter(fields, body_md)
    _write_artifacts({out_path: md_full})
    log.info("ok: %s -> %s", url, out_path)
    return _legacy_result(ConversionResult("written", out_path), detailed)


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
    ap.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Maximum attempts per URL, including the first (default: 2)",
    )
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
    args = ap.parse_intermixed_args()

    level = logging.WARNING if args.quiet else getattr(logging, args.log_level)
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    for name in ("timeout", "retries", "concurrency"):
        if getattr(args, name) < 1:
            ap.error(f"--{name} must be at least 1")
    if args.sleep_ms < 0:
        ap.error("--sleep-ms must be nonnegative")
    if not 1 <= args.cdp_port <= 65535:
        ap.error("--cdp-port must be between 1 and 65535")
    try:
        config = load_config(Path(args.config) if args.config else None)
    except (OSError, ValueError) as exc:
        ap.error(str(exc))
    pub_mappings = config.get("publication_mappings", {})

    if args.base_dir:
        base_dir = Path(os.path.expanduser(args.base_dir))
    else:
        base_dir = Path(os.path.expanduser(config["base_dir"]))

    url_list = list(args.urls)
    if args.urls_file:
        try:
            with open(os.path.expanduser(args.urls_file), encoding="utf-8") as f:
                url_list.extend(
                    line.strip() for line in f if line.strip() and not line.lstrip().startswith("#")
                )
        except OSError as exc:
            ap.error(str(exc))

    if args.from_md:
        if not args.raw_url:
            ap.error("--url is required with --from-md")
        if url_list:
            ap.error("--from-md cannot be combined with URL inputs")
        try:
            result = process_from_md(
                Path(args.from_md).expanduser(),
                base_dir,
                pub_mappings,
                args.raw_url,
                args.overwrite,
                detect_paywall=args.detect_paywall,
                paywall_timeout=args.timeout,
                detailed=True,
            )
        except (OSError, ValueError) as exc:
            log.error("failed: %s", exc)
            return 1
        log.warning(
            "summary: %d written, %d skipped, 0 failed",
            result.status == "written",
            result.status == "skipped",
        )
        return 0

    if not url_list:
        ap.print_help()
        return 2
    for url in url_list:
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname or parts.username:
            ap.error(f"expected an HTTP(S) post URL: {url}")

    # Deduplicate before scheduling; aliases with tracking parameters share work.
    url_list = list({cleanup_url(url): url for url in url_list}.values())
    pkg = _substack2md()
    state = pkg.StateFile(base_dir) if not args.no_resume else None
    index = build_url_to_note_map(base_dir)
    counts = {"written": 0, "skipped": 0, "failed": 0}
    if state is not None and not args.overwrite:
        pending = []
        for url in url_list:
            path = index.get(cleanup_url(url))
            complete = path is not None and path.is_file() and not _pending_path(path).exists()
            if complete and args.also_save_html:
                complete = path.with_suffix(".html").is_file()
            if state.contains(url) and complete:
                counts["skipped"] += 1
            else:
                pending.append(url)
        url_list = pending

    host_locks = {urllib.parse.urlsplit(url).hostname.lower(): threading.Lock() for url in url_list}
    result_lock = threading.Lock()
    stop = threading.Event()

    def worker(url: str) -> None:
        host = urllib.parse.urlsplit(url).hostname.lower()
        with host_locks[host]:
            if stop.is_set():
                return
            with result_lock:
                snapshot = dict(index)
            try:
                result = pkg.process_url(
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
                    detailed=True,
                    url_map=snapshot,
                )
                # Preserve compatibility with external replacements of process_url.
                if not isinstance(result, ConversionResult):
                    result = (
                        ConversionResult("written", result)
                        if result
                        else ConversionResult("failed")
                    )
                if result.path is not None:
                    if state is not None:
                        state.record(url, result.path)
                    with result_lock:
                        index[cleanup_url(url)] = result.path
            except Exception as exc:
                log.error("fail: %s (%s)", url, exc)
                result = ConversionResult("failed", error=str(exc))
            with result_lock:
                counts[result.status] += 1
            stop.wait(args.sleep_ms / 1000.0)

    pool = None
    try:
        if args.concurrency == 1:
            for url in url_list:
                worker(url)
        else:
            pool = ThreadPoolExecutor(max_workers=args.concurrency)
            futures = [pool.submit(worker, url) for url in url_list]
            for future in as_completed(futures):
                future.result()
    except KeyboardInterrupt:
        stop.set()
        if pool is not None:
            pool.shutdown(wait=True, cancel_futures=True)
            pool = None
        log.warning("interrupted: rerun the same command to resume")
        return 130
    finally:
        if pool is not None:
            pool.shutdown(wait=True)
        log.warning(
            "summary: %d written, %d skipped, %d failed",
            counts["written"],
            counts["skipped"],
            counts["failed"],
        )
    return 1 if counts["failed"] else 0
