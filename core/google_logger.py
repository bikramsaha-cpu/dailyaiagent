from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# The environment in this workspace points proxies at 127.0.0.1:9, which breaks Google auth.
# Clear proxy vars so service-account requests can reach Google directly.
for _proxy_var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(_proxy_var, None)

import gspread
from google.oauth2.service_account import Credentials

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


class GoogleSheetLogger:
    def __init__(self, sheet_name: str, tab_name: str):
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = self._load_credentials(scope)
        client = gspread.authorize(creds)
        self.sheet = client.open(sheet_name).worksheet(tab_name)
        self.tab_name = tab_name
        print("GoogleSheetLogger initialized successfully")

    @staticmethod
    def _load_credentials(scope):
        env_json = os.getenv("AUTOMATION_GOOGLE_CREDENTIALS_JSON", "").strip()
        if env_json:
            try:
                payload = json.loads(env_json)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "AUTOMATION_GOOGLE_CREDENTIALS_JSON is set but is not valid JSON."
                ) from exc
            return Credentials.from_service_account_info(payload, scopes=scope)

        candidate_paths = []
        env_path = os.getenv("AUTOMATION_GOOGLE_CREDENTIALS", "").strip()
        if env_path:
            candidate_paths.append(Path(env_path))
        candidate_paths.extend(
            [
                Path(__file__).resolve().parent / "credentials.json",
                ROOT_DIR / "PBR" / "credentials.json",
                ROOT_DIR / "enq" / "credentials.json",
                ROOT_DIR / "credentials.json",
            ]
        )
        creds_path = next((path for path in candidate_paths if path.exists()), None)
        if creds_path is None:
            raise FileNotFoundError(
                "Could not find Google credentials. Set AUTOMATION_GOOGLE_CREDENTIALS_JSON, "
                "set AUTOMATION_GOOGLE_CREDENTIALS to a credentials file path, or place a "
                "credentials.json file in core/, PBR/, enq/, or the repository root."
            )
        return Credentials.from_service_account_file(creds_path, scopes=scope)

    def log_status(self, test_title, status, remarks="", browser="Chromium", phone="Unknown", run_time=None, tab_name=None):
        sheet = self.sheet if tab_name is None else self.sheet.spreadsheet.worksheet(tab_name)
        if run_time is None:
            now = datetime.now()
            date = now.strftime("%d-%m-%Y")
            time = now.strftime("%H:%M:%S")
        else:
            dt = datetime.strptime(run_time, "%Y-%m-%d %H:%M:%S")
            date = dt.strftime("%d-%m-%Y")
            time = dt.strftime("%H:%M:%S")
        sheet.append_row([test_title, status, remarks, browser, phone, date, time])

    def _filter_rows_by_range(self, all_rows, start_time=None, end_time=None):
        if not start_time and not end_time:
            return all_rows
        filtered = []
        for row in all_rows:
            try:
                dt_str = f"{row[5]} {row[6]}"
                row_dt = datetime.strptime(dt_str, "%d-%m-%Y %H:%M:%S")
                if (not start_time or row_dt >= start_time) and (not end_time or row_dt <= end_time):
                    filtered.append(row)
            except (ValueError, IndexError):
                continue
        return filtered

    def get_summary_counts(self, run_time=None, start_time=None, end_time=None, tab_name=None):
        sheet = self.sheet if tab_name is None else self.sheet.spreadsheet.worksheet(tab_name)
        all_rows = sheet.get_all_values()[1:]
        if run_time:
            dt = datetime.strptime(run_time, "%Y-%m-%d %H:%M:%S")
            start_time = dt
            end_time = dt
        if start_time or end_time:
            all_rows = self._filter_rows_by_range(all_rows, start_time, end_time)
        passed = sum(1 for r in all_rows if len(r) > 1 and r[1].strip().lower() == "pass")
        failed = sum(1 for r in all_rows if len(r) > 1 and r[1].strip().lower() == "fail")
        total = len(all_rows)
        return passed, failed, total

    def get_browser_wise_counts(self, run_time=None, start_time=None, end_time=None, tab_name=None):
        sheet = self.sheet if tab_name is None else self.sheet.spreadsheet.worksheet(tab_name)
        all_rows = sheet.get_all_values()[1:]
        if run_time:
            dt = datetime.strptime(run_time, "%Y-%m-%d %H:%M:%S")
            start_time = dt
            end_time = dt
        if start_time or end_time:
            all_rows = self._filter_rows_by_range(all_rows, start_time, end_time)
        browser_counts = {}
        for row in all_rows:
            browser = row[3] if len(row) > 3 else "Unknown"
            status = row[1].strip().capitalize() if len(row) > 1 else "Unknown"
            browser_counts.setdefault(browser, {"Pass": 0, "Fail": 0})
            if status in ["Pass", "Fail"]:
                browser_counts[browser][status] += 1
        return browser_counts

    def get_latest_run_time(self, tab_name=None):
        sheet = self.sheet if tab_name is None else self.sheet.spreadsheet.worksheet(tab_name)
        all_rows = sheet.get_all_values()[1:]
        run_times = []
        for row in all_rows:
            try:
                dt_str = f"{row[5]} {row[6]}"
                run_times.append(datetime.strptime(dt_str, "%d-%m-%Y %H:%M:%S"))
            except (ValueError, IndexError):
                continue
        return max(run_times).strftime("%Y-%m-%d %H:%M:%S") if run_times else None

    def get_earliest_run_time(self, tab_name=None):
        sheet = self.sheet if tab_name is None else self.sheet.spreadsheet.worksheet(tab_name)
        all_rows = sheet.get_all_values()[1:]
        run_times = []
        for row in all_rows:
            try:
                dt_str = f"{row[5]} {row[6]}"
                run_times.append(datetime.strptime(dt_str, "%d-%m-%Y %H:%M:%S"))
            except (ValueError, IndexError):
                continue
        return min(run_times).strftime("%Y-%m-%d %H:%M:%S") if run_times else None

    def list_tab_names(self) -> list[str]:
        return [worksheet.title for worksheet in self.sheet.spreadsheet.worksheets()]

    def read_rows(self, tab_name: str | None = None, include_header: bool = False) -> list[list[str]]:
        sheet = self.sheet if tab_name is None else self.sheet.spreadsheet.worksheet(tab_name)
        rows = sheet.get_all_values()
        return rows if include_header else rows[1:]

    def read_records(self, tab_name: str | None = None) -> list[dict[str, str]]:
        rows = self.read_rows(tab_name=tab_name, include_header=True)
        if not rows:
            return []
        header = rows[0]
        records = []
        for row in rows[1:]:
            record = {header[i]: row[i] if i < len(row) else "" for i in range(len(header))}
            records.append(record)
        return records

    def filter_records(
        self,
        *,
        tab_name: str | None = None,
        status: str | None = None,
        browser: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, str]]:
        records = self.read_records(tab_name=tab_name)
        status_values = self._normalize_filter_values(status)
        browser_values = self._normalize_filter_values(browser)
        search = (search or "").strip().lower() or None
        start_dt = self._parse_sheet_date(start_date) if start_date else None
        end_dt = self._parse_sheet_date(end_date) if end_date else None

        filtered = []
        for record in records:
            record_status = record.get("Status", "").strip().lower()
            record_browser = record.get("Browser", "").strip().lower()
            record_date = self._parse_sheet_date(record.get("Date", "").strip()) if record.get("Date") else None
            haystack = " ".join(record.values()).lower()

            if status_values and record_status not in status_values:
                continue
            if browser_values and record_browser not in browser_values:
                continue
            if start_dt and record_date and record_date < start_dt:
                continue
            if end_dt and record_date and record_date > end_dt:
                continue
            if search and search not in haystack:
                continue
            filtered.append(record)

        return filtered

    @staticmethod
    def _parse_sheet_date(value: str | None):
        if not value:
            return None
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    @staticmethod
    def _normalize_filter_values(value):
        if not value:
            return []
        if isinstance(value, (list, tuple, set)):
            values = value
        else:
            values = [item.strip() for item in str(value).split(",")]
        return [item.lower() for item in values if item]
