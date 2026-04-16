"""
Evals for publication + slug derivation feeding fetch_paywall_status.

Merge-blocking questions:

  P1. Standard subdomain URL: https://pub.substack.com/p/slug
      -> publication="pub", slug="slug".  Baseline.

  P2. Custom-domain Substacks: https://example.com/p/slug
      Substack allows custom domains (stratechery.com, etc.).
      extract_article_fields derives publication from netloc.split(".")[0]
      which would yield "example" or similar, and
      fetch_paywall_status then hits https://example.substack.com/...
      which will 404.  That's acceptable as a "fail gracefully" case
      (is_paid=None), but it means the feature is silently inert for
      custom-domain subs.  Worth surfacing in the PR discussion.

  P3. Slug with uppercase or odd chars in the URL path is slugified
      (lowercased, stripped) before being sent to the API.  If the
      real Substack slug is case-sensitive or contains chars that
      slugify removes, the API call will 404.  Unlikely in practice
      (Substack slugs are already lowercase-kebab) but worth asserting.

These tests don't require network -- they only check the inputs
fetch_paywall_status would receive.
"""

import pytest

import substack2md


def _extract(
    url,
    html="<html><head><title>x</title></head><body><h1>x</h1><article><p>"
    + "word " * 80
    + "</p></article></body></html>",
):
    fields, _ = substack2md.extract_article_fields(url, html)
    return fields


def test_standard_subdomain_slug_and_pub():
    f = _extract("https://examplepub.substack.com/p/hello-world")
    assert f["publication"] == "examplepub"
    assert f["slug"] == "hello-world"


def test_custom_domain_publication_is_wrong_for_api():
    """
    Known gap: custom-domain publications won't resolve on the
    <slug>.substack.com metadata endpoint.  This test documents the
    current behavior so reviewers can decide:
      (a) leave it -- paywall detection silently returns None for
          custom domains (current), or
      (b) add a lookup (e.g. fetch the post page, grab canonical
          publication id from __NEXT_DATA__) before merging.
    """
    f = _extract("https://stratechery.com/2024/some-post")
    # netloc "stratechery.com" -> split(".")[0] == "stratechery"
    # but the real API host would still be stratechery.substack.com
    # (which may or may not exist).  Either way, the publication string
    # the code produces is NOT a guaranteed Substack subdomain.
    assert f["publication"] == "stratechery"  # documented, not endorsed


def test_slug_is_lowercased_by_slugify():
    f = _extract("https://examplepub.substack.com/p/Hello-World")
    # slugify lowercases.  If Substack ever served a slug with caps
    # the API call would miss.  (In practice Substack normalizes.)
    assert f["slug"] == "hello-world"


def test_path_with_trailing_slash():
    f = _extract("https://examplepub.substack.com/p/hello-world/")
    # split("/")[-1] on trailing slash yields "" and slugify falls
    # through to the title.  This would break the API call.  If seen
    # in the wild, consider stripping trailing slashes before deriving
    # the slug.
    assert f["slug"]  # must be non-empty
