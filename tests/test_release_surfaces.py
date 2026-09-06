"""Keep release metadata and discoverable local website paths coherent."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from substack2md._version import __version__

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "docs"


def test_release_version_and_revision_agree_across_surfaces():
    html = BeautifulSoup((SITE / "index.html").read_text(), "lxml")
    data = json.loads(html.find("script", type="application/ld+json").string)
    assert data["softwareVersion"] == __version__
    assert html.select_one(".version").get_text(strip=True) == f"v{__version__}"
    assert f"version {__version__}" in (ROOT / "README.md").read_text()
    assert f"version {__version__}" in (SITE / "llms.txt").read_text()
    assert f"## [{__version__}]" in (ROOT / "CHANGELOG.md").read_text()
    sitemap = ET.parse(SITE / "sitemap.xml")
    lastmod = sitemap.find(".//{*}lastmod").text
    assert data["dateModified"] == lastmod
    assert html.find("meta", property="article:modified_time")["content"].startswith(lastmod)
    assert html.find("link", rel="canonical")["href"] == "https://substack2md.space/"


def test_local_website_links_and_assets_exist():
    for page in (SITE / "index.html", SITE / "404.html"):
        html = BeautifulSoup(page.read_text(), "lxml")
        for node in html.select("[href], [src]"):
            value = node.get("href", node.get("src"))
            url = urlsplit(value)
            if url.scheme or url.netloc:
                continue
            target = (
                SITE / url.path.lstrip("/") if url.path.startswith("/") else page.parent / url.path
            )
            if not url.path:
                target = page
            if target.is_dir():
                target = target / "index.html"
            assert target.is_file(), f"{page.name}: missing {value}"
            if url.fragment and target.suffix == ".html":
                target_html = BeautifulSoup(target.read_text(), "lxml")
                assert target_html.find(id=url.fragment), f"missing anchor: {value}"


def test_agent_summary_links_are_explicit():
    text = (SITE / "llms.txt").read_text()
    assert "https://substack2md.space/.well-known/assistant-guide.txt" in text
    assert "https://substack2md.space/.well-known/assistant-guide-manifest.txt" in text
    assert "https://github.com/snapsynapse/substack2md/blob/main/README.md" in text
