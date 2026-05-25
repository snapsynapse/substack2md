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
