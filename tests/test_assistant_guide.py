import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / ".well-known" / "assistant-guide.txt"
ROOT_GUIDE = ROOT / "assistant-guide.txt"
PAGES_GUIDE = ROOT / "docs" / ".well-known" / "assistant-guide.txt"
MANIFEST = ROOT / "assistant-guide-manifest.txt"
PAGES_MANIFEST = ROOT / "docs" / ".well-known" / "assistant-guide-manifest.txt"
PAGES_HEADERS = ROOT / "docs" / "_headers"
IMMUTABLE_RELEASE_URL = "https://github.com/snapsynapse/substack2md/releases/tag/v3.0.0"


def _metadata(text: str) -> dict[str, str]:
    start = text.index("[assistant-guide-metadata]\n") + len("[assistant-guide-metadata]\n")
    end = text.index("[/assistant-guide-metadata]")
    out = {}
    for line in text[start:end].splitlines():
        key, value = line.split(": ", 1)
        out[key] = value
    return out


def _key_values(text: str) -> dict[str, str]:
    out = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line:
            assert ": " in line, f"manifest line {line_number} is malformed"
            key, value = line.split(": ", 1)
            assert key not in out, f"manifest key {key!r} is duplicated"
            assert key and value, f"manifest line {line_number} has an empty key or value"
            out[key] = value
    return out


def _validate_manifest(text: str, guide_data: bytes) -> dict[str, str]:
    manifest = _key_values(text)
    required = {
        "guide-path",
        "guide-version",
        "guide-sha256",
        "guide-bytes",
        "immutable-release-url",
        "profile",
        "profile-version",
        "canonical-url",
        "repository-url",
    }
    assert required <= set(manifest)
    metadata = _metadata(guide_data.decode("ascii"))
    assert manifest["guide-path"] == "/.well-known/assistant-guide.txt"
    assert manifest["guide-version"] == metadata["guide-version"]
    assert manifest["guide-sha256"] == hashlib.sha256(guide_data).hexdigest()
    assert int(manifest["guide-bytes"]) == len(guide_data)
    assert manifest["immutable-release-url"] == IMMUTABLE_RELEASE_URL
    assert manifest["profile"] == metadata["profile"]
    assert manifest["profile-version"] == metadata["profile-version"]
    assert manifest["canonical-url"] == metadata["canonical-url"]
    assert manifest["repository-url"] == metadata["repository-url"]
    return manifest


def _action_blocks(text: str) -> list[dict[str, str]]:
    blocks = []
    offset = 0
    while True:
        start = text.find("[action]\n", offset)
        if start == -1:
            return blocks
        start += len("[action]\n")
        end = text.index("[/action]", start)
        block = {}
        for line in text[start:end].splitlines():
            if line:
                key, value = line.split(": ", 1)
                block[key] = value
        blocks.append(block)
        offset = end + len("[/action]")


def test_assistant_guide_byte_profile():
    data = GUIDE.read_bytes()
    assert len(data) <= 8192
    assert all(byte == 0x0A or 0x20 <= byte <= 0x7E for byte in data)
    assert b"\r" not in data
    assert b"\t" not in data

    lines = data.splitlines()
    assert len(lines) <= 400
    assert max(len(line) for line in lines) <= 120


def test_root_assistant_guide_copy_is_byte_identical():
    assert ROOT_GUIDE.read_bytes() == GUIDE.read_bytes()
    assert PAGES_GUIDE.read_bytes() == GUIDE.read_bytes()
    assert PAGES_MANIFEST.read_bytes() == MANIFEST.read_bytes()


def test_assistant_guide_required_metadata():
    text = GUIDE.read_text(encoding="ascii")
    metadata = _metadata(text)
    required = {
        "identifier",
        "profile",
        "profile-version",
        "guide-version",
        "applies-to",
        "canonical-url",
        "repository-url",
        "last-reviewed",
    }
    assert required <= set(metadata)
    assert metadata["profile"] == "human-verifiable-assistant-guide"
    assert metadata["profile-version"] == "0.3.0"
    assert metadata["canonical-url"] == "https://substack2md.space/.well-known/assistant-guide.txt"
    assert "manifest-url" not in metadata
    assert metadata["recommended-verifier"] == "https://guidecheck.org/verify"


def test_assistant_guide_manifest_matches_bytes():
    data = GUIDE.read_bytes()
    _validate_manifest(MANIFEST.read_text(encoding="ascii"), data)


@pytest.mark.parametrize(
    "invalid_manifest",
    [
        lambda text: text.replace(f"immutable-release-url: {IMMUTABLE_RELEASE_URL}\n", ""),
        lambda text: text.replace("/v3.0.0\n", "/v2.1.2\n"),
        lambda text: text.replace("immutable-release-url: ", "immutable-release-url="),
        lambda text: text + f"immutable-release-url: {IMMUTABLE_RELEASE_URL}\n",
    ],
    ids=["missing", "stale", "malformed", "duplicate"],
)
def test_assistant_guide_manifest_rejects_invalid_immutable_release_url(invalid_manifest):
    manifest = MANIFEST.read_text(encoding="ascii")
    with pytest.raises(AssertionError):
        _validate_manifest(invalid_manifest(manifest), GUIDE.read_bytes())


def test_assistant_guide_static_header_policy():
    headers = PAGES_HEADERS.read_text(encoding="ascii")

    assert "/.well-known/assistant-guide.txt" in headers
    assert "/.well-known/assistant-guide-manifest.txt" in headers
    assert "Content-Type: text/plain; charset=utf-8" in headers
    assert "X-Content-Type-Options: nosniff" in headers
    assert "Strict-Transport-Security: max-age=31536000; includeSubDomains" in headers


def test_assistant_guide_actions_have_required_approval_gates():
    text = GUIDE.read_text(encoding="ascii")
    actions = _action_blocks(text)
    assert actions
    risky = {
        "privileged",
        "destructive",
        "persistence-changing",
        "data-accessing",
        "code-executing",
    }

    for action in actions:
        assert {"id", "class", "approval", "command", "runner", "cwd"} <= set(action)
        classes = {item.strip() for item in action["class"].split(",")}
        if classes & risky:
            assert action["approval"] == "required"
        if "networked" in classes:
            assert action["approval"] == "required"
            assert "egress" in action
