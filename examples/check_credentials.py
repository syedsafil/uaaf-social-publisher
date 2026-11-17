"""
UAAF Credentials Health Checker
===============================
Quickly checks your .env configuration for all 5 social platforms.

Usage:
    python -m examples.check_credentials
"""

import sys
from pathlib import Path

# Add project root and python_agents to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python_agents"))
sys.path.insert(0, str(ROOT))

from config import Config
from examples.publish_clip import check_platform_credentials, ALL_PLATFORMS


def main():
    print("=" * 65)
    print("UAAF SOCIAL PLATFORMS CREDENTIALS AUDIT")
    print("=" * 65)

    ready_count = 0
    for p in ALL_PLATFORMS:
        res = check_platform_credentials(p)
        status = "[CONFIGURED]" if res["configured"] else "[NOT SET]"
        if res["configured"]:
            ready_count += 1
        print(f"\n* {p.upper()}: {status}")
        print(f"  Status: {res['details']}")
        if not res["configured"]:
            print(f"  Setup:  {res['setup_hint']}")

    print("\n" + "=" * 65)
    print(f"Audit Summary: {ready_count}/{len(ALL_PLATFORMS)} platforms configured.")
    if ready_count == 0:
        print("Tip: Copy .env.example to .env and configure your desired channels.")
    print("=" * 65)


if __name__ == "__main__":
    main()
