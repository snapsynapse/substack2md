"""
Tag extraction merges three sources:
  1. <meta name="keywords"> (comma-separated)
  2. ld+json "keywords" (list or comma string)
  3. ld+json "articleSection" (string or list)

Always normalized: lowercase, dash-separated, deduplicated, "substack"
prepended.  These tests pin each source independently and confirm the
merge works when multiple are present.
"""
import substack2md


URL = "https://examplepub.substack.com/p/hello"
BODY_PADDING = "<p>" + ("word " * 80) + "</p>"


def _html(head: str) -> str:
    return f"""
    <html><head>
      <title>Hello</title>
      {head}
    </head><body>
      <h1>Hello</h1>
      <article>{BODY_PADDING}</article>
    </body></html>
    """


def test_meta_keywords_only():
    html = _html('<meta name="keywords" content="ai, automation, productivity">')
    fields, _ = substack2md.extract_article_fields(URL, html)
    assert "ai" in fields["tags"]
    assert "automation" in fields["tags"]
    assert "productivity" in fields["tags"]
    assert "substack" in fields["tags"]


def test_ld_json_keywords_list():
    html = _html("""
      <script type="application/ld+json">
      {"@type":"Article","headline":"x",
       "keywords":["Agents","Tool Use","Context Engineering"]}
      </script>
    """)
    fields, _ = substack2md.extract_article_fields(URL, html)
    # Normalized: lowercased, spaces -> dashes
    assert "agents" in fields["tags"]
    assert "tool-use" in fields["tags"]
    assert "context-engineering" in fields["tags"]


def test_ld_json_keywords_string():
    html = _html("""
      <script type="application/ld+json">
      {"@type":"NewsArticle","headline":"x","keywords":"newsletter, essay"}
      </script>
    """)
    fields, _ = substack2md.extract_article_fields(URL, html)
    assert "newsletter" in fields["tags"]
    assert "essay" in fields["tags"]


def test_ld_json_article_section_string():
    html = _html("""
      <script type="application/ld+json">
      {"@type":"BlogPosting","headline":"x","articleSection":"Deep Dives"}
      </script>
    """)
    fields, _ = substack2md.extract_article_fields(URL, html)
    assert "deep-dives" in fields["tags"]


def test_ld_json_article_section_list():
    html = _html("""
      <script type="application/ld+json">
      {"@type":"Article","headline":"x","articleSection":["Technology","AI"]}
      </script>
    """)
    fields, _ = substack2md.extract_article_fields(URL, html)
    assert "technology" in fields["tags"]
    assert "ai" in fields["tags"]


def test_sources_merge_without_duplicates():
    """A tag appearing in two sources should appear once in the output."""
    html = _html("""
      <meta name="keywords" content="ai, newsletter">
      <script type="application/ld+json">
      {"@type":"Article","headline":"x",
       "keywords":["ai","essays"],
       "articleSection":"Newsletter"}
      </script>
    """)
    fields, _ = substack2md.extract_article_fields(URL, html)
    tags = fields["tags"]
    # "ai" appears in both meta and ld+json -- should dedupe
    assert tags.count("ai") == 1
    # "newsletter" appears in meta and as articleSection
    assert tags.count("newsletter") == 1
    assert "essays" in tags


def test_no_tag_sources_still_yields_substack():
    """Regression: empty tag sources still get the default "substack" tag."""
    html = _html("")
    fields, _ = substack2md.extract_article_fields(URL, html)
    assert fields["tags"] == ["substack"]
