#!/usr/bin/env python3
"""
Discover all Claude organizations accessible from your Chrome session.

Prints a config.json snippet you can paste into ~/.claude-widget/config.json
to enable multi-account tracking in the widget.

Usage:
    python3 discover_accounts.py

Requires: same prerequisites as fetch_usage.py (Chrome cookies + curl_cffi).
"""
import json
import os
import sys

# Add widget install dir to path so we reuse get_cookies()
INSTALL_DIR = os.path.expanduser("~/.claude-widget")
sys.path.insert(0, INSTALL_DIR)

try:
    from fetch_usage import get_cookies
except ImportError:
    print("Error: ~/.claude-widget/fetch_usage.py not found. Run install.sh first.")
    sys.exit(1)

try:
    from curl_cffi import requests
except ImportError:
    print("Error: curl_cffi not installed. Run: pip3 install curl_cffi")
    sys.exit(1)


def main():
    cookies = get_cookies()
    if "sessionKey" not in cookies:
        print("Error: no Claude session cookie found in Chrome.")
        print("Log into claude.ai in Chrome, then re-run this script.")
        sys.exit(1)

    resp = requests.get(
        "https://claude.ai/api/organizations",
        cookies=cookies, impersonate="chrome", timeout=15,
    )
    if resp.status_code != 200:
        print(f"Error: claude.ai returned HTTP {resp.status_code}")
        sys.exit(1)

    orgs = resp.json()
    if not orgs:
        print("No organizations found.")
        sys.exit(1)

    print(f"\nFound {len(orgs)} organization(s) accessible from this Chrome session:\n")
    for i, org in enumerate(orgs):
        plan = org.get("billable_usage_paid_plan_name") or org.get("rate_limit_tier") or "free"
        print(f"  {i + 1}. {org.get('name', '?')}")
        print(f"     id:   {org.get('uuid')}")
        print(f"     plan: {plan}")
        print()

    # Build config snippet
    accounts = []
    for i, org in enumerate(orgs):
        # Use a friendly short label from the org name
        name = (org.get("name") or "Account").strip()
        # If name looks like an email (...@...), use just the local part
        if "@" in name:
            name = name.split("@")[0].title()
        # If it ends with "Organization" / "Org", trim that
        for suffix in ("'s Organization", "'s Org", " Organization", " Org"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break
        accounts.append({
            "org_id": org.get("uuid"),
            "label": name[:20],
            "primary": i == 0,
        })

    snippet = {
        "accounts": accounts,
        "cache_path": "/tmp/claude_usage_cache.json",
    }

    print("─" * 60)
    print("Suggested ~/.claude-widget/config.json:")
    print("─" * 60)
    print(json.dumps(snippet, indent=4))
    print("─" * 60)
    print()
    print("To apply, save the JSON above to ~/.claude-widget/config.json")
    print("Or write it directly:")
    print()
    print("    python3 discover_accounts.py --save")
    print()

    if "--save" in sys.argv:
        cfg_path = os.path.join(INSTALL_DIR, "config.json")
        with open(cfg_path, "w") as f:
            json.dump(snippet, f, indent=4)
        print(f"✓ Saved to {cfg_path}")


if __name__ == "__main__":
    main()
