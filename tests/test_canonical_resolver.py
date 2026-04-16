"""
Tests for resolve_substack_canonical() — the helper that lets paywall
detection work on custom-domain publications (e.g. stratechery.com) by
finding the `<pub>.substack.com/p/<slug>` URL embedded in the page.
"""
import substack2md


def test_resolves_from_link_rel_canonical():
    html = """
    <html><head>
      <link rel="canonical" href="https://mypub.substack.com/p/hello-world">
    </head><body>x</body></html>
    """
    pub, slug = substack2md.resolve_substack_canonical(html)
    assert pub == "mypub"
    assert slug == "hello-world"


def test_resolves_from_og_url():
    html = """
    <html><head>
      <meta property="og:url" content="https://stratechery.substack.com/p/some-post-2024">
    </head><body>x</body></html>
    """
    pub, slug = substack2md.resolve_substack_canonical(html)
    assert pub == "stratechery"
    assert slug == "some-post-2024"


def test_resolves_from_ld_json_main_entity():
    html = """
    <html><head>
      <script type="application/ld+json">
      {"@type":"NewsArticle","mainEntityOfPage":{"@id":"https://example.substack.com/p/foo"}}
      </script>
    </head><body>x</body></html>
    """
    pub, slug = substack2md.resolve_substack_canonical(html)
    assert pub == "example"
    assert slug == "foo"


def test_returns_none_when_no_substack_url_present():
    html = """
    <html><head>
      <link rel="canonical" href="https://medium.com/@user/some-article">
    </head><body>x</body></html>
    """
    pub, slug = substack2md.resolve_substack_canonical(html)
    assert pub is None
    assert slug is None


def test_returns_none_on_malformed_html():
    # BeautifulSoup is tolerant so this is mostly to pin the "no raise" contract.
    pub, slug = substack2md.resolve_substack_canonical("<<<not really html>>>")
    assert pub is None
    assert slug is None


def test_mixed_case_subdomain_lowercased():
    html = '<link rel="canonical" href="https://MyPub.Substack.com/p/Post-Slug">'
    pub, slug = substack2md.resolve_substack_canonical(html)
    assert pub == "mypub"
    # slug case preserved -- matches Substack's own URL casing, which is
    # already lowercase in practice but we don't force it.
    assert slug == "Post-Slug"
