"""
Evals for with_frontmatter() interaction with the new paywall fields.

Merge-blocking questions:

  F1. Backward compatibility: a call with no is_paid/audience keys (the
      pre-PR shape) must still produce identical frontmatter.  The PR
      currently uses fields.get("is_paid") which is None when absent, and
      with_frontmatter filters None values -- so backward compat SHOULD
      hold.  Test pins it.

  F2. Forward behavior:
      - is_paid True  -> key present, value True
      - is_paid False -> key present, value False (False is not None,
        must survive the None-filter)
      - is_paid None  -> key absent

  F3. YAML emits real booleans, not the strings "True"/"False".  Obsidian
      and downstream YAML consumers rely on this.

  F4. Output is still valid YAML frontmatter that round-trips via
      yaml.safe_load.
"""

import pytest
import yaml

import substack2md


def _base_fields(**overrides):
    f = {
        "title": "Hello World",
        "subtitle": "",
        "author": "A. Writer",
        "publication": "examplepub",
        "published": "2026-04-16",
        "updated": None,
        "retrieved": "2026-04-16T00:00:00Z",
        "url": "https://examplepub.substack.com/p/hello",
        "canonical": "https://examplepub.substack.com/p/hello",
        "slug": "hello",
        "image": "",
        "tags": ["substack"],
        "video_url": "",
        "links_internal": 0,
        "links_external": 0,
        "source": "substack2md v1.1.0",
    }
    f.update(overrides)
    return f


def _parse_frontmatter(doc: str) -> dict:
    assert doc.startswith("---\n"), "Output must start with YAML frontmatter"
    end = doc.find("\n---\n", 4)
    assert end != -1, "Missing closing --- for frontmatter"
    return yaml.safe_load(doc[4:end])


# --- F1: backward compat --------------------------------------------------


def test_no_paywall_fields_means_no_paywall_keys_in_output():
    fields = _base_fields()  # no is_paid / audience at all
    out = substack2md.with_frontmatter(fields, "body\n")
    fm = _parse_frontmatter(out)
    assert "is_paid" not in fm
    assert "audience" not in fm


# --- F2: forward behavior --------------------------------------------------


def test_is_paid_true_appears_in_frontmatter():
    fields = _base_fields(is_paid=True, audience="only_paid")
    out = substack2md.with_frontmatter(fields, "body\n")
    fm = _parse_frontmatter(out)
    assert fm["is_paid"] is True
    assert fm["audience"] == "only_paid"


def test_is_paid_false_survives_none_filter():
    """
    Regression guard: with_frontmatter strips None but NOT False.
    If someone changes the filter to `if v` they'd drop False silently.
    """
    fields = _base_fields(is_paid=False, audience="everyone")
    out = substack2md.with_frontmatter(fields, "body\n")
    fm = _parse_frontmatter(out)
    assert fm["is_paid"] is False
    assert fm["audience"] == "everyone"


def test_none_values_are_filtered():
    fields = _base_fields(is_paid=None, audience=None)
    out = substack2md.with_frontmatter(fields, "body\n")
    fm = _parse_frontmatter(out)
    assert "is_paid" not in fm
    assert "audience" not in fm


# --- F3: YAML bool not string ---------------------------------------------


def test_is_paid_serialized_as_yaml_bool():
    fields = _base_fields(is_paid=True, audience="only_paid")
    out = substack2md.with_frontmatter(fields, "body\n")
    # Match "is_paid: true" (lowercase yaml boolean), not "is_paid: True"
    assert "is_paid: true" in out
    assert "is_paid: True" not in out


# --- F4: body preserved ----------------------------------------------------


def test_body_is_appended_after_frontmatter():
    fields = _base_fields(is_paid=False, audience="everyone")
    body = "# Heading\n\nSome text.\n"
    out = substack2md.with_frontmatter(fields, body)
    assert out.endswith(body)
