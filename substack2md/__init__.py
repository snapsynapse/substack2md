"""substack2md

Convert Substack posts to clean, Obsidian-friendly Markdown using an
authenticated Chrome/Brave session via CDP.

Public API is flat for backward compatibility: ``import substack2md``
still gives you every function and class the flat-file version exposed.
"""

# re-export the upstream requests module so tests that do
# ``monkeypatch.setattr(substack2md.requests, ...)`` still work.
from ._core import (
    LINK_RE,
    SPEAKER_RE,
    STATE_FILENAME,
    SUBSTACK_HOST_RE,
    TEASER_WORD_THRESHOLD,
    TIME_RE,
    # CDP
    CDPClient,
    # resume state
    StateFile,
    __version__,
    # link rewriting
    build_url_to_note_map,
    cleanup_url,
    collapse_blank_lines_in_lists,
    ensure_dir,
    # article extraction
    extract_article_fields,
    fetch_paywall_status,
    get_publication_name,
    html_to_markdown_clean,
    # HTML -> markdown
    img_to_link,
    # config
    load_config,
    log,
    normalize_tags,
    parse_ld_json,
    remove_blank_after_headings,
    requests,  # noqa: F401
    # paywall
    resolve_substack_canonical,
    rewrite_internal_links,
    sanitize_filename,
    # transcript / markdown cleanup
    scrub_transcript_lines,
    # utilities
    slugify,
    # frontmatter
    with_frontmatter,
)
from .cli import main, process_from_md, process_url

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
