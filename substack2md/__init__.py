"""substack2md

Convert Substack posts to clean, Obsidian-friendly Markdown using an
authenticated Chrome/Brave session via CDP.

Public API is flat for backward compatibility: ``import substack2md``
still gives you every function and class the flat-file version exposed.
"""
from ._core import (
    __version__,
    log,
    TEASER_WORD_THRESHOLD,
    STATE_FILENAME,
    SUBSTACK_HOST_RE,
    LINK_RE,
    TIME_RE,
    SPEAKER_RE,
    # config
    load_config,
    get_publication_name,
    # utilities
    slugify,
    sanitize_filename,
    ensure_dir,
    normalize_tags,
    cleanup_url,
    # transcript / markdown cleanup
    scrub_transcript_lines,
    remove_blank_after_headings,
    collapse_blank_lines_in_lists,
    # HTML -> markdown
    img_to_link,
    html_to_markdown_clean,
    parse_ld_json,
    # paywall
    resolve_substack_canonical,
    fetch_paywall_status,
    # article extraction
    extract_article_fields,
    # CDP
    CDPClient,
    # link rewriting
    build_url_to_note_map,
    rewrite_internal_links,
    # frontmatter
    with_frontmatter,
    # resume state
    StateFile,
)
from .cli import process_url, process_from_md, main

# re-export the upstream requests module so tests that do
# ``monkeypatch.setattr(substack2md.requests, ...)`` still work.
from ._core import requests  # noqa: F401

__all__ = [
    "__version__",
    "log",
    "TEASER_WORD_THRESHOLD",
    "STATE_FILENAME",
    "SUBSTACK_HOST_RE",
    "LINK_RE",
    "TIME_RE",
    "SPEAKER_RE",
    "load_config",
    "get_publication_name",
    "slugify",
    "sanitize_filename",
    "ensure_dir",
    "normalize_tags",
    "cleanup_url",
    "scrub_transcript_lines",
    "remove_blank_after_headings",
    "collapse_blank_lines_in_lists",
    "img_to_link",
    "html_to_markdown_clean",
    "parse_ld_json",
    "resolve_substack_canonical",
    "fetch_paywall_status",
    "extract_article_fields",
    "CDPClient",
    "build_url_to_note_map",
    "rewrite_internal_links",
    "with_frontmatter",
    "StateFile",
    "process_url",
    "process_from_md",
    "main",
    "requests",
]
