"""Regression checks for the final release's local trust boundaries."""

import sys

import pytest
import responses

import substack2md
from substack2md import _core as core


@responses.activate
def test_paywall_request_ignores_netrc_proxies_and_redirects(monkeypatch, tmp_path):
    credentials = tmp_path / "netrc"
    credentials.write_text("machine pub.substack.com login private password secret\n")
    monkeypatch.setenv("NETRC", str(credentials))
    monkeypatch.setenv("HTTPS_PROXY", "https://proxy.invalid:443")
    url = "https://pub.substack.com/api/v1/posts/post"
    responses.add(responses.GET, url, status=302, headers={"Location": "https://other.invalid/"})
    result = core.fetch_paywall_status("pub", "post")
    assert result == {"is_paid": None, "audience": None}
    assert len(responses.calls) == 1
    request = responses.calls[0].request
    assert "Authorization" not in request.headers
    assert "Cookie" not in request.headers


@pytest.mark.parametrize(
    "url",
    [
        "http://pub.substack.com/p/post",
        "https://127.0.0.1/p/post",
        "https://127.0.0.1./p/post",
        "https://0x7f.0.0.1/p/post",
        "https://host.internal/p/post",
        "https://user:secret@pub.substack.com/p/post",
        "https://:secret@pub.substack.com/p/post",
        "https://@pub.substack.com/p/post",
        "https://[::1]/p/post",
        "https://pub.substack.com/api/v1/posts/post",
        "https://pub.substack.com:9222/p/post",
        "https://pub.substack.com/p/post\nforged log",
    ],
)
def test_post_admission_rejects_unsafe_input(url):
    with pytest.raises(ValueError):
        core.validate_post_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://pub.substack.com/p/post?token=private#part",
        "https://custom-domain.example.com/2026/post",
    ],
)
def test_custom_publication_paths_remain_supported(url):
    core.validate_post_url(url)


def test_html_size_limit_applies_to_library_entrypoint(monkeypatch):
    monkeypatch.setattr(core, "MAX_HTML_BYTES", 32)
    with pytest.raises(ValueError, match="limit"):
        core.extract_article_fields("https://pub.substack.com/p/post", "x" * 33)


def test_navigation_bounds_html_before_cdp_return():
    client = core.CDPClient()
    expressions = []

    def send(method, params=None, sessionId=None):
        if method == "Runtime.evaluate":
            expressions.append(params["expression"])
            return {"result": {"value": None}}
        return {"targetId": "t", "sessionId": "s"}

    client.send = send
    client.recv_event_until = lambda *args, **kwargs: {}
    with pytest.raises(RuntimeError):
        client.fetch_html("https://pub.substack.com/p/post")
    assert str(core.MAX_HTML_BYTES) in expressions[0]
    assert "TextEncoder" in expressions[0]


def test_failed_capture_logs_do_not_repeat_private_url(monkeypatch, tmp_path, caplog):
    url = "https://pub.substack.com/p/private-title?token=credential"

    class Browser:
        def __init__(self, *args, **kwargs):
            pass

        def fetch_html(self, requested):
            raise RuntimeError("remote failure: " + requested)

    monkeypatch.setattr(substack2md, "CDPClient", Browser)
    assert substack2md.process_url(url, tmp_path, {}, False, False, "127.0.0.1", 9222, 1, 1) is None
    assert "private-title" not in caplog.text
    assert "credential" not in caplog.text
    assert "RuntimeError" in caplog.text


def test_excessive_concurrency_rejected_before_browser(monkeypatch, tmp_path):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "substack2md",
            "--concurrency",
            "9",
            "--base-dir",
            str(tmp_path),
            "https://pub.substack.com/p/post",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        substack2md.main()
    assert exc.value.code == 2


def test_ipv6_loopback_cdp_discovery_uses_bracketed_authority(monkeypatch):
    requests = []

    class Response:
        def json(self):
            return {"webSocketDebuggerUrl": "ws://[::1]:9222/devtools/browser/test"}

    def get(url, **kwargs):
        requests.append(url)
        return Response()

    monkeypatch.setattr(core.requests, "get", get)
    monkeypatch.setattr(core, "create_connection", lambda *args, **kwargs: object())
    core.CDPClient(host="::1").connect()
    assert requests == ["http://[::1]:9222/json/version"]
