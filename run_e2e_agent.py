from __future__ import annotations

import argparse
import json
import sys

from core.e2e_agent import E2EAgentRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a declarative Playwright E2E agent flow.")
    parser.add_argument(
        "--flow",
        required=True,
        help="Path to the JSON flow file.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = E2EAgentRunner().run_flow_file(args.flow)
    print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "Pass" else 1


if __name__ == "__main__":
    sys.exit(main())
