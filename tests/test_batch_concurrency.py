"""Exercise actual CLI workers and interruption with bounded thread rendezvous."""

import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit

import substack2md
from substack2md import cli


def configure(monkeypatch, tmp_path, urls, concurrency):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "substack2md",
            *urls,
            "--base-dir",
            str(tmp_path),
            "--concurrency",
            str(concurrency),
            "--sleep-ms",
            "0",
        ],
    )


def test_hosts_overlap_but_same_host_is_serialized(monkeypatch, tmp_path):
    urls = [
        "https://a.substack.com/p/first",
        "https://b.substack.com/p/first",
        "https://A.substack.com:443/p/second",
        "https://b.substack.com/p/second",
    ]
    configure(monkeypatch, tmp_path, urls, 4)
    rendezvous = threading.Barrier(2, timeout=5)
    lock = threading.Lock()
    active = {}
    maximum = {}

    def capture(url, *args, **kwargs):
        host = urlsplit(url).hostname.lower()
        with lock:
            active[host] = active.get(host, 0) + 1
            maximum[host] = max(maximum.get(host, 0), active[host])
        rendezvous.wait()
        with lock:
            active[host] -= 1
        path = tmp_path / f"{host}-{urlsplit(url).path.rsplit('/', 1)[1]}.md"
        path.write_text("captured")
        return path

    monkeypatch.setattr(substack2md, "process_url", capture)
    assert cli.main() == 0
    assert maximum == {"a.substack.com": 1, "b.substack.com": 1}
    state = substack2md.StateFile(tmp_path)
    assert all(state.contains(url) for url in urls)


def test_interrupt_cancels_queued_and_host_waiting_work(monkeypatch, tmp_path):
    urls = [f"https://a.substack.com/p/post-{number}" for number in range(8)]
    configure(monkeypatch, tmp_path, urls, 2)
    started = threading.Event()
    release = threading.Event()
    calls = []

    def capture(url, *args, **kwargs):
        calls.append(url)
        started.set()
        assert release.wait(5), "executor never initiated interruption shutdown"
        path = tmp_path / "completed.md"
        path.write_text("captured before shutdown")
        return path

    class ReleasingExecutor(ThreadPoolExecutor):
        def shutdown(self, wait=True, *, cancel_futures=False):
            release.set()
            return super().shutdown(wait=wait, cancel_futures=cancel_futures)

    def interrupted(futures):
        assert started.wait(5), "first worker never started"
        raise KeyboardInterrupt

    monkeypatch.setattr(substack2md, "process_url", capture)
    monkeypatch.setattr(cli, "ThreadPoolExecutor", ReleasingExecutor)
    monkeypatch.setattr(cli, "as_completed", interrupted)
    assert cli.main() == 130
    assert calls == urls[:1]
    state = substack2md.StateFile(tmp_path)
    assert state.contains(urls[0])
    assert not any(state.contains(url) for url in urls[1:])
