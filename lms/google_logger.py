import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime


class GoogleSheetLogger:
    def __init__(self, sheet_name, tab_name):
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
            creds = Credentials.from_service_account_file(creds_path, scopes=scope)
            client = gspread.authorize(creds)
            self.sheet = client.open(sheet_name).worksheet(tab_name)
            self.tab_name = tab_name
            print("✅ GoogleSheetLogger initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize GoogleSheetLogger: {e}")
            raise

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
        """Internal helper to filter rows by datetime range."""
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
        all_rows = sheet.get_all_values()[1:]  # Skip header

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
        """
        Returns a dict: { 'Chromium': {'Pass': x, 'Fail': y}, ... }
        """
        sheet = self.sheet if tab_name is None else self.sheet.spreadsheet.worksheet(tab_name)
        all_rows = sheet.get_all_values()[1:]  # Skip header

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
            if browser not in browser_counts:
                browser_counts[browser] = {"Pass": 0, "Fail": 0}
            if status in ["Pass", "Fail"]:
                browser_counts[browser][status] += 1

        return browser_counts

    def get_latest_run_time(self, tab_name=None):
        """Fetch the most recent run timestamp from the sheet."""
        sheet = self.sheet if tab_name is None else self.sheet.spreadsheet.worksheet(tab_name)
        all_rows = sheet.get_all_values()[1:]  # Skip header

        run_times = []
        for row in all_rows:
            try:
                dt_str = f"{row[5]} {row[6]}"
                dt = datetime.strptime(dt_str, "%d-%m-%Y %H:%M:%S")
                run_times.append(dt)
            except (ValueError, IndexError):
                continue

        if not run_times:
            return None
        latest_dt = max(run_times)
        return latest_dt.strftime("%Y-%m-%d %H:%M:%S")

    def get_earliest_run_time(self, tab_name=None):
        """Fetch the earliest run timestamp from the sheet."""
        sheet = self.sheet if tab_name is None else self.sheet.spreadsheet.worksheet(tab_name)
        all_rows = sheet.get_all_values()[1:]  # Skip header

        run_times = []
        for row in all_rows:
            try:
                dt_str = f"{row[5]} {row[6]}"
                dt = datetime.strptime(dt_str, "%d-%m-%Y %H:%M:%S")
                run_times.append(dt)
            except (ValueError, IndexError):
                continue

        if not run_times:
            return None
        earliest_dt = min(run_times)
        return earliest_dt.strftime("%Y-%m-%d %H:%M:%S")
