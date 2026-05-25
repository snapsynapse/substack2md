import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / ".well-known" / "assistant-guide.txt"
ROOT_GUIDE = ROOT / "assistant-guide.txt"
PAGES_GUIDE = ROOT / "docs" / ".well-known" / "assistant-guide.txt"
MANIFEST = ROOT / "assistant-guide.manifest.json"
PAGES_MANIFEST = ROOT / "docs" / "assistant-guide.manifest.json"


def _metadata(text: str) -> dict[str, str]:
    start = text.index("[assistant-guide-metadata]\n") + len("[assistant-guide-metadata]\n")
    end = text.index("[/assistant-guide-metadata]")
    out = {}
    for line in text[start:end].splitlines():
        key, value = line.split(": ", 1)
        out[key] = value
    return out


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


def test_assistant_guide_required_metadata_and_manifest_link():
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
        "manifest-url",
    }
    assert required <= set(metadata)
    assert metadata["profile"] == "human-verifiable-assistant-guide"
    assert metadata["profile-version"] == "0.3.0"
    assert metadata["canonical-url"] == "https://substack2md.space/.well-known/assistant-guide.txt"
    assert metadata["manifest-url"] == "https://substack2md.space/assistant-guide.manifest.json"
    assert metadata["recommended-verifier"] == "https://guidecheck.org/verify"


def test_assistant_guide_manifest_matches_bytes():
    data = GUIDE.read_bytes()
    manifest = json.loads(MANIFEST.read_text(encoding="ascii"))

    assert manifest["guide-path"] == ".well-known/assistant-guide.txt"
    assert manifest["guide-bytes"] == len(data)
    assert manifest["guide-sha256"] == hashlib.sha256(data).hexdigest()
    assert manifest["profile"] == "human-verifiable-assistant-guide"
    assert manifest["profile-version"] == "0.3.0"
    assert manifest["immutable-release-url"].startswith("https://")


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
