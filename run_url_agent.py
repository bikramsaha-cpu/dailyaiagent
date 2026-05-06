from __future__ import annotations

import argparse
import json
import sys

from core.url_agent import URLAuditAgent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the URL-only AI audit agent.")
    parser.add_argument("--url", required=True, help="Target URL to inspect.")
    parser.add_argument("--headless", action="store_true", help="Run Chromium headless.")
    parser.add_argument("--slow-mo", type=int, default=100, dest="slow_mo", help="Slow motion in milliseconds.")
    parser.add_argument("--visual-guard", action="store_true", help="Run the visual guard checks during the audit.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = URLAuditAgent().run(
        args.url,
        headless=args.headless,
        slow_mo=args.slow_mo,
        visual_guard=args.visual_guard,
    )
    print(json.dumps(result, indent=2))
    # A visual or behavioral failure is still a successful audit response.
    # Reserve non-zero exits for runner/runtime crashes, not page findings.
    return 0


if __name__ == "__main__":
    sys.exit(main())
