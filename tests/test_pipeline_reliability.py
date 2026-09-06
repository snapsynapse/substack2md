"""Archive recovery and command-line outcome contracts, without a browser."""

import sys
from pathlib import Path

import pytest

import substack2md as package
from substack2md import cli

URL = "https://pub.substack.com/p/original-slug"
HTML = (
    "<html><body><h1>Actual title</h1><article><p>"
    + "Readable sentence. " * 60
    + "</p></article></body></html>"
)


@pytest.fixture
def browser(monkeypatch):
    clients = []

    class Browser:
        def __init__(self, *args, **kwargs):
            self.closed = False
            clients.append(self)

        def fetch_html(self, url):
            return HTML

        def close(self):
            self.closed = True

    monkeypatch.setattr(package, "CDPClient", Browser)
    return clients


def convert(root, **kwargs):
    options = dict(
        also_save_html=False,
        overwrite=False,
        cdp_host="localhost",
        cdp_port=9222,
        timeout=1,
        retries=1,
        detailed=True,
    )
    options.update(kwargs)
    return cli.process_url(URL, root, {}, **options)


def run(monkeypatch, root, *flags):
    monkeypatch.setattr(
        sys, "argv", ["substack2md", URL, "--base-dir", str(root), "--sleep-ms", "0", *flags]
    )
    return cli.main()


def test_written_skipped_and_failure_are_distinct(tmp_path, browser, monkeypatch):
    assert convert(tmp_path).status == "written"
    assert convert(tmp_path).status == "skipped"
    monkeypatch.setattr(
        cli, "_write_artifacts", lambda *args: (_ for _ in ()).throw(OSError("disk full"))
    )
    assert convert(tmp_path, overwrite=True).status == "failed"
    assert all(client.closed for client in browser)


def test_missing_sidecar_is_repaired_without_replacing_markdown(tmp_path, browser):
    result = convert(tmp_path)
    result.path.write_text(result.path.read_text() + "\nLocal annotation.\n")
    repaired = convert(tmp_path, also_save_html=True)
    assert repaired.status == "written"
    assert repaired.path.read_text().endswith("Local annotation.\n")
    assert repaired.path.with_suffix(".html").read_text() == HTML


def test_staging_failure_preserves_existing_artifacts(tmp_path, monkeypatch):
    note = tmp_path / "note.md"
    sidecar = tmp_path / "note.html"
    note.write_text("old note")
    sidecar.write_text("old html")
    real_fsync = cli.os.fsync
    calls = 0

    def fail_second(fd):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("disk full")
        real_fsync(fd)

    monkeypatch.setattr(cli.os, "fsync", fail_second)
    with pytest.raises(OSError, match="disk full"):
        cli._write_artifacts({sidecar: "new html", note: "new note"})
    assert note.read_text() == "old note"
    assert sidecar.read_text() == "old html"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["note.html", "note.md"]


def test_overwrite_bypasses_state_and_missing_note_recovers(tmp_path, browser, monkeypatch):
    assert run(monkeypatch, tmp_path) == 0
    assert len(browser) == 1
    assert run(monkeypatch, tmp_path) == 0
    assert len(browser) == 1
    assert run(monkeypatch, tmp_path, "--overwrite") == 0
    assert len(browser) == 2
    next(tmp_path.rglob("*.md")).unlink()
    assert run(monkeypatch, tmp_path) == 0
    assert len(browser) == 3
    assert len(list(tmp_path.rglob("*.md"))) == 1


def test_batch_failure_returns_nonzero_and_does_not_record(tmp_path, monkeypatch):
    monkeypatch.setattr(
        package,
        "process_url",
        lambda *args, **kwargs: cli.ConversionResult("failed", error="unavailable"),
    )
    assert run(monkeypatch, tmp_path) == 1
    assert not package.StateFile(tmp_path).contains(URL)


def test_archive_index_is_built_once_per_batch(tmp_path, browser, monkeypatch):
    real_index = cli.build_url_to_note_map
    calls = []

    def count(root):
        calls.append(root)
        return real_index(root)

    monkeypatch.setattr(cli, "build_url_to_note_map", count)
    assert run(monkeypatch, tmp_path, "https://pub.substack.com/p/second") == 0
    assert len(calls) == 1


@pytest.mark.parametrize(
    "flags",
    [
        ("--timeout", "0"),
        ("--retries", "0"),
        ("--concurrency", "-1"),
        ("--sleep-ms", "-1"),
        ("--cdp-port", "65536"),
    ],
)
def test_invalid_numeric_options_fail_before_browser(tmp_path, browser, monkeypatch, flags):
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, tmp_path, *flags)
    assert exc.value.code == 2
    assert not browser


def test_from_md_trailing_slash_uses_url_slug(tmp_path):
    source = tmp_path / "input.md"
    source.write_text("# Different title\n\nBody text.\n")
    result = cli.process_from_md(source, tmp_path / "out", {}, URL + "/", False)
    assert result.name.endswith("-original-slug.md")


def test_legacy_return_contract(tmp_path, browser):
    first = convert(tmp_path, detailed=False)
    assert isinstance(first, Path)
    assert convert(tmp_path, detailed=False) is None


def test_replacement_failure_marks_pair_incomplete_and_rerun_repairs(
    tmp_path, browser, monkeypatch
):
    first = convert(tmp_path, also_save_html=True)
    first.path.write_text(first.path.read_text() + "\nold edit\n")
    real_replace = cli.os.replace

    def fail_markdown(source, destination):
        if destination == first.path:
            raise OSError("simulated replacement failure")
        return real_replace(source, destination)

    with monkeypatch.context() as scoped:
        scoped.setattr(cli.os, "replace", fail_markdown)
        assert convert(tmp_path, overwrite=True, also_save_html=True).status == "failed"
    assert cli._pending_path(first.path).is_file()
    # Even with both old files and a completion record, the next run must retry.
    package.StateFile(tmp_path).record(URL, first.path)
    assert run(monkeypatch, tmp_path) == 0
    assert not cli._pending_path(first.path).exists()
    assert "old edit" not in first.path.read_text()
    assert first.path.with_suffix(".html").read_text() == HTML


def test_directory_at_note_path_is_failure(tmp_path, browser):
    result = convert(tmp_path)
    result.path.unlink()
    result.path.mkdir()
    assert convert(tmp_path).status == "failed"


def test_from_md_does_not_clear_incomplete_html_capture(tmp_path):
    source = tmp_path / "input.md"
    source.write_text("# Example\n\nBody.\n")
    note = cli.process_from_md(source, tmp_path / "out", {}, URL, False)
    marker = cli._pending_path(note)
    marker.write_text(cli.json.dumps([note.with_suffix(".html").name, note.name]))
    with pytest.raises(ValueError, match="Incomplete HTML capture"):
        cli.process_from_md(source, tmp_path / "out", {}, URL, True)
    assert marker.exists()
