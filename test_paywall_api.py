"""Quick test: verify Substack public API returns paywall metadata."""
import requests
import json

test_cases = [
    ("daveshap", "the-merits-of-doing-things-the-hard"),
    ("natesnewsletter", "i-surveyed-100-ai-tools-that-launched"),
]

for pub, slug in test_cases:
    url = f"https://{pub}.substack.com/api/v1/posts/{slug}"
    try:
        r = requests.get(url, headers={"Accept": "application/json", "User-Agent": "substack2md"}, timeout=10)
        print(f"\n{pub}/{slug}: HTTP {r.status_code}")
        if r.status_code == 200:
            d = r.json()
            audience = d.get("audience")
            title = d.get("title", "???")
            post_type = d.get("type")
            print(f"  title: {title}")
            print(f"  audience: {audience}")
            print(f"  type: {post_type}")
            print(f"  is_paid (our logic): {audience == 'only_paid'}")
        else:
            print(f"  response: {r.text[:300]}")
    except Exception as e:
        print(f"  error: {e}")

# Also test fetch_paywall_status directly
print("\n--- Testing fetch_paywall_status() ---")
import sys
sys.path.insert(0, ".")
from substack2md import fetch_paywall_status

for pub, slug in test_cases:
    result = fetch_paywall_status(pub, slug)
    print(f"{pub}/{slug}: {result}")

print("\nDone.")
