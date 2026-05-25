import pytest

import substack2md


def test_publication_output_dir_allows_nested_paths_under_base(tmp_path):
    out = substack2md.publication_output_dir(tmp_path, "Newsletters/Example")
    assert out == tmp_path / "Newsletters" / "Example"


@pytest.mark.parametrize(
    "mapping",
    [
        "../escape",
        "../../escape",
        "/tmp/escape",
        ".",
        "pub/../escape",
    ],
)
def test_publication_output_dir_rejects_paths_outside_base(tmp_path, mapping):
    with pytest.raises(substack2md.UnsafeOutputPathError):
        substack2md.publication_output_dir(tmp_path, mapping)


def test_from_md_rejects_publication_mapping_escape(tmp_path):
    src = tmp_path / "raw.md"
    src.write_text("# Some Title\n\nBody.\n", encoding="utf-8")
    base_dir = tmp_path / "archive"

    with pytest.raises(substack2md.UnsafeOutputPathError):
        substack2md.process_from_md(
            src,
            base_dir=base_dir,
            pub_mappings={"examplepub": "../../escape"},
            url="https://examplepub.substack.com/p/hello",
            overwrite=True,
        )

    assert not (tmp_path / "escape").exists()


def test_process_url_rejects_publication_mapping_escape(monkeypatch, tmp_path):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def fetch_html(self, url):
            return """
            <html><head>
              <title>Hello</title>
              <meta name="author" content="A. Writer">
            </head><body>
              <h1>Hello</h1>
              <article><p>Body text here with enough words for extraction
              padding padding padding padding padding padding padding.</p>
              </article>
            </body></html>
            """

    monkeypatch.setattr(substack2md, "CDPClient", FakeClient)

    base_dir = tmp_path / "archive"
    out = substack2md.process_url(
        "https://examplepub.substack.com/p/hello",
        base_dir=base_dir,
        pub_mappings={"examplepub": "../../escape"},
        also_save_html=True,
        overwrite=True,
        cdp_host="x",
        cdp_port=0,
        timeout=1,
        retries=1,
        detect_paywall=False,
    )

    assert out is None
    assert not (tmp_path / "escape").exists()
