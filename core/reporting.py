from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from core.settings import REPORTS_DIR


def write_html_report(summary: dict[str, Any], filename: str | None = None) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / (filename or f"{summary['suite_name'].lower()}_{timestamp}.html")
    browser_rows = ""
    for browser, counts in summary.get("browser_breakdown", {}).items():
        total = counts.get("Pass", 0) + counts.get("Fail", 0)
        browser_rows += (
            f"<tr><td>{browser}</td><td>{counts.get('Pass', 0)}</td>"
            f"<td>{counts.get('Fail', 0)}</td><td>{total}</td></tr>"
        )

    report_path.write_text(
        f"""
        <html>
          <head>
            <style>
              body {{ font-family: Arial, sans-serif; margin: 24px; }}
              table {{ border-collapse: collapse; width: 100%; max-width: 900px; }}
              th, td {{ border: 1px solid #ccc; padding: 8px 10px; text-align: center; }}
              th {{ background: #1f2937; color: white; }}
            </style>
          </head>
          <body>
            <h2>{summary['suite_name']} - {summary['module_name']}</h2>
            <p><b>Status:</b> {summary['status']}</p>
            <p><b>Passed:</b> {summary['passed']} | <b>Failed:</b> {summary['failed']} | <b>Total:</b> {summary['total']}</p>
            <p><b>Started:</b> {summary['started_at']} | <b>Finished:</b> {summary['finished_at']}</p>
            <h3>Browser Breakdown</h3>
            <table>
              <tr><th>Browser</th><th>Passed</th><th>Failed</th><th>Total</th></tr>
              {browser_rows or '<tr><td colspan="4">No browser data</td></tr>'}
            </table>
          </body>
        </html>
        """,
        encoding="utf-8",
    )
    return report_path

