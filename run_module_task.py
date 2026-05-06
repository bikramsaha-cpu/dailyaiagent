from __future__ import annotations

import argparse
import json
import os
import sys

from core.runner import ModuleRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a module and emit JSON summary.")
    parser.add_argument("--module-id", required=True, dest="module_id", help="Module id to execute.")
    parser.add_argument("--tests", action="append", default=None, help="Optional relative test file paths to run.")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run the underlying browser in headed mode when the module honors environment-based browser settings.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.headed:
      os.environ["AUTOMATION_BMC_HEADLESS"] = "0"
    result = ModuleRunner().run_module(args.module_id, selected_tests=args.tests or None)
    print(json.dumps(result, indent=2))
    return 1 if result.get("status") == "Fail" else 0


if __name__ == "__main__":
    sys.exit(main())
