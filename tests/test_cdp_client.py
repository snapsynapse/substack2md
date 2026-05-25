import pytest

import substack2md
import substack2md._core as core


def test_cdp_connect_applies_timeout_to_discovery_request(monkeypatch):
    seen = {}

    class Response:
        def json(self):
            return {"webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/test"}

    def fake_get(url, timeout=None):
        seen["url"] = url
        seen["timeout"] = timeout
        return Response()

    def fake_create_connection(url, timeout=None):
        seen["ws_url"] = url
        seen["ws_timeout"] = timeout
        return object()

    monkeypatch.setattr(substack2md.requests, "get", fake_get)
    monkeypatch.setattr(core, "create_connection", fake_create_connection)

    client = substack2md.CDPClient("127.0.0.1", 9222, timeout=12)
    client.connect()

    assert seen["url"] == "http://127.0.0.1:9222/json/version"
    assert seen["timeout"] == 12
    assert seen["ws_timeout"] == 12


def test_fetch_html_closes_target_when_evaluate_fails():
    class FakeClient(substack2md.CDPClient):
        def __init__(self):
            super().__init__(timeout=1)
            self.closed = False

        def send(self, method, params=None, sessionId=None):
            if method == "Target.createTarget":
                return {"targetId": "target-1"}
            if method == "Target.attachToTarget":
                return {"sessionId": "session-1"}
            if method in {"Page.enable", "Page.navigate"}:
                return {}
            if method == "Runtime.evaluate":
                raise RuntimeError("eval failed")
            if method == "Target.closeTarget":
                self.closed = True
                return {}
            raise AssertionError(f"unexpected method {method}")

        def recv_event_until(self, event, sessionId, timeout):
            return {}

    client = FakeClient()
    with pytest.raises(RuntimeError, match="eval failed"):
        client.fetch_html("https://examplepub.substack.com/p/hello")

    assert client.closed is True
