from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from core.module_registry import load_modules
from core.testlink_generator import (
    TestLinkCaseGenerator,
    TestLinkGeneratorConfig,
    default_output_dir_for_module,
)


def build_parser() -> argparse.ArgumentParser:
    module_choices = [module.id for module in load_modules()]
    parser = argparse.ArgumentParser(description="Generate Playwright tests from a TestLink suite.")
    parser.add_argument("--module", required=True, choices=module_choices, help="Target daily-qa-agent module id.")
    parser.add_argument("--suite-id", required=True, type=int, help="TestLink suite id to fetch.")
    parser.add_argument("--output-dir", help="Optional output directory for generated tests.")
    parser.add_argument("--max-cases", type=int, help="Generate only the first N cases.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing generated files.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s:%(name)s:%(message)s")

    output_dir = Path(args.output_dir).resolve() if args.output_dir else default_output_dir_for_module(args.module)
    config = TestLinkGeneratorConfig(
        suite_id=args.suite_id,
        module_id=args.module,
        output_dir=output_dir,
        overwrite=args.overwrite,
        max_cases=args.max_cases,
    )
    results = TestLinkCaseGenerator(config).run()

    summary = {
        "module": args.module,
        "suite_id": args.suite_id,
        "output_dir": str(output_dir),
        "generated": sum(1 for item in results if item.status == "generated"),
        "skipped": sum(1 for item in results if item.status == "skipped"),
        "failed": sum(1 for item in results if item.status == "failed"),
        "results": [
            {
                "title": item.title,
                "status": item.status,
                "detail": item.detail,
                "output_path": str(item.output_path) if item.output_path else None,
            }
            for item in results
        ],
    }
    print(json.dumps(summary, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
