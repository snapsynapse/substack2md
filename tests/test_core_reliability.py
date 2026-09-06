"""Offline regression tests for archive integrity and CDP message ordering."""

import json
from pathlib import Path

import pytest

from substack2md import _core as core


def test_transcript_preserves_speech_and_fenced_code():
    source = "Host: Keep this.\n[01:23] Guest: Keep that.\nSpeaker 2:\n01:24\n```text\nHost: literal\n01:25\n```"
    assert (
        core.scrub_transcript_lines(source)
        == "Keep this.\nKeep that.\n```text\nHost: literal\n01:25\n```"
    )


def test_external_links_are_unchanged_and_internal_labels_and_fragments_survive():
    source = "[Search](https://example.com/search?q=python#results) [Read](https://pub.substack.com/p/post?utm_source=email#section)"
    result, internal, external = core.rewrite_internal_links(
        source, {"https://pub.substack.com/p/post": Path("post.md")}
    )
    assert result == "[Search](https://example.com/search?q=python#results) [[post#section|Read]]"
    assert (internal, external) == (1, 1)


def test_short_article_and_trailing_slash_are_valid():
    fields, body = core.extract_article_fields(
        "https://pub.substack.com/p/original-slug/",
        "<html><h1>A brief announcement</h1><article><p>We open tomorrow.</p></article></html>",
    )
    assert fields["slug"] == "original-slug"
    assert "We open tomorrow." in body


@pytest.mark.parametrize(
    "html",
    [
        "",
        "<html><h1>Access denied</h1><p>Please log in</p></html>",
        '<html><title>Sign in</title><input type="password"></html>',
    ],
)
def test_invalid_capture_is_rejected(html):
    with pytest.raises(ValueError):
        core.extract_article_fields("https://pub.substack.com/p/post", html)


def test_state_associated_output_must_exist_after_reload(tmp_path):
    url = "https://pub.substack.com/p/post"
    output = tmp_path / "post.md"
    output.write_text("article")
    core.StateFile(tmp_path).record(url, output)
    assert core.StateFile(tmp_path).contains(url)
    output.unlink()
    assert not core.StateFile(tmp_path).contains(url)


def test_legacy_state_can_gain_output_association(tmp_path):
    url = "https://pub.substack.com/p/post"
    state = core.StateFile(tmp_path)
    state.record(url)
    assert state.contains(url)
    state.record(url, tmp_path / "missing.md")
    assert not core.StateFile(tmp_path).contains(url)


@pytest.mark.parametrize(
    "config", ["[]", "base_dir: 12", "publication_mappings: []", "publication_mappings: {pub: 4}"]
)
def test_invalid_configuration_fails_explicitly(tmp_path, config):
    path = tmp_path / "config.yaml"
    path.write_text(config)
    with pytest.raises(ValueError):
        core.load_config(path)


def test_missing_explicit_config_fails(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        core.load_config(tmp_path / "missing.yaml")


class Socket:
    def __init__(self, messages):
        self.messages = iter(messages)
        self.timeouts = []
        self.closed = False

    def send(self, message):
        pass

    def settimeout(self, timeout):
        self.timeouts.append(timeout)

    def recv(self):
        return json.dumps(next(self.messages))

    def close(self):
        self.closed = True


def test_cdp_buffers_events_by_session_while_waiting_for_command():
    event = {"method": "Page.loadEventFired", "sessionId": "correct"}
    client = core.CDPClient(timeout=10)
    client.ws = Socket(
        [{"method": "Page.loadEventFired", "sessionId": "other"}, event, {"id": 1, "result": {}}]
    )
    client.send("Page.navigate")
    assert client.recv_event_until("Page.loadEventFired", "correct", 10) == event
    assert len(client._events) == 1
    socket = client.ws
    client.close()
    assert socket.closed
    assert client.ws is None


def test_cdp_unrelated_messages_cannot_extend_deadline(monkeypatch):
    clock = iter([0, 1, 11])
    monkeypatch.setattr(core.time, "monotonic", lambda: next(clock))
    client = core.CDPClient(timeout=10)
    client.ws = Socket([{"method": "unrelated"}])
    with pytest.raises(TimeoutError):
        client.send("Page.navigate")
    assert client.ws.timeouts == [9]


@pytest.mark.parametrize(
    "navigate,evaluate,error",
    [
        ({"errorText": "net::ERR_FAILED"}, {}, "Navigation failed"),
        ({}, {"exceptionDetails": {"text": "exception"}}, "evaluation failed"),
        ({}, {"result": {"value": ""}}, "no document"),
    ],
)
def test_cdp_rejects_bad_navigation_or_evaluation(navigate, evaluate, error):
    client = core.CDPClient()
    calls = []

    def send(method, params=None, sessionId=None):
        calls.append(method)
        return {
            "Target.createTarget": {"targetId": "target"},
            "Target.attachToTarget": {"sessionId": "session"},
            "Page.navigate": navigate,
            "Runtime.evaluate": evaluate,
        }.get(method, {})

    client.send = send
    client.recv_event_until = lambda *args, **kwargs: {}
    with pytest.raises(RuntimeError, match=error):
        client.fetch_html("https://pub.substack.com/p/post")
    assert calls[-1] == "Target.closeTarget"


def test_wikilinks_use_archive_relative_paths_and_leave_code_literal(tmp_path):
    note = tmp_path / "Publication" / "post.md"
    url = "https://pub.substack.com/p/post"
    link = f"[A label]({url})"
    source = f"{link}\n```markdown\n{link}\n```\n`{link}`\n"
    result, internal, external = core.rewrite_internal_links(source, {url: note}, base_dir=tmp_path)
    assert result == f"[[Publication/post|A label]]\n```markdown\n{link}\n```\n`{link}`\n"
    assert (internal, external) == (1, 0)


def test_load_timeout_is_not_accepted_as_capture_success():
    client = core.CDPClient()
    calls = []

    def send(method, params=None, sessionId=None):
        calls.append(method)
        return {
            "Target.createTarget": {"targetId": "target"},
            "Target.attachToTarget": {"sessionId": "session"},
        }.get(method, {})

    def timeout(*args, **kwargs):
        raise TimeoutError("load timed out")

    client.send = send
    client.recv_event_until = timeout
    with pytest.raises(TimeoutError):
        client.fetch_html("https://pub.substack.com/p/post")
    assert "Runtime.evaluate" not in calls
    assert calls[-1] == "Target.closeTarget"


@pytest.mark.parametrize("name", ["login.html", "access-denied.html"])
def test_rejected_page_fixtures(name):
    html = (Path(__file__).parent / "fixtures" / name).read_text()
    with pytest.raises(ValueError, match="valid article"):
        core.extract_article_fields("https://pub.substack.com/p/post", html)


def test_synthetic_article_fixture_extracts_metadata_and_functional_link():
    html = (Path(__file__).parent / "fixtures" / "short-article.html").read_text()
    fields, body = core.extract_article_fields("https://pub.substack.com/p/announcement/", html)
    assert fields["author"] == "Example Author"
    assert fields["published"] == "2026-09-05"
    assert fields["slug"] == "announcement"
    assert "https://example.com/search?q=hours#results" in body
    assert "We open tomorrow." in body


def test_article_metadata_prevents_false_rejection_of_error_like_headline():
    html = '<html><h1>Access denied</h1><script type="application/ld+json">{"@type":"Article","headline":"Access denied"}</script><article><p>A story about locked doors.</p></article></html>'
    fields, body = core.extract_article_fields("https://pub.substack.com/p/doors", html)
    assert fields["title"] == "Access denied"
    assert "A story about locked doors." in body


def test_state_symlink_cannot_modify_external_file(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    external = tmp_path / "sentinel"
    external.write_text("unchanged\n")
    (archive / core.STATE_FILENAME).symlink_to(external)
    state = core.StateFile(archive)
    state.record("https://pub.substack.com/p/post", archive / "post.md")
    assert external.read_text() == "unchanged\n"
    assert not state.contains("https://pub.substack.com/p/post")


def test_archive_index_excludes_external_note_symlink(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    external = tmp_path / "external.md"
    external.write_text("---\nurl: https://pub.substack.com/p/private\n---\nprivate")
    (archive / "linked.md").symlink_to(external)
    assert core.build_url_to_note_map(archive) == {}


def test_initial_blank_load_event_cannot_complete_requested_navigation():
    client = core.CDPClient()
    client._events.append({"method": "Page.loadEventFired", "sessionId": "session"})
    calls = []

    def send(method, params=None, sessionId=None):
        calls.append(method)
        return {
            "Target.createTarget": {"targetId": "target"},
            "Target.attachToTarget": {"sessionId": "session"},
        }.get(method, {})

    def wait(event, sessionId, timeout):
        assert not client._events
        raise TimeoutError("actual navigation has not loaded")

    client.send = send
    client.recv_event_until = wait
    with pytest.raises(TimeoutError):
        client.fetch_html("https://pub.substack.com/p/post")
    assert "Runtime.evaluate" not in calls
