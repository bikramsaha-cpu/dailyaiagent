import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

class GoogleSheetLogger:
    def __init__(self, sheet_name, tab_name):
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
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
            date = datetime.strptime(run_time, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y")
            time = datetime.strptime(run_time, "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
        
        sheet.append_row([test_title, status, remarks, browser, phone, date, time])

    def get_summary_counts(self, run_time=None, tab_name=None):
        sheet = self.sheet if tab_name is None else self.sheet.spreadsheet.worksheet(tab_name)
        all_rows = sheet.get_all_values()[1:]  # Skip header

        if not run_time:
            return len([r for r in all_rows if r[1].strip().lower() == "pass"]), \
                   len([r for r in all_rows if r[1].strip().lower() == "fail"]), \
                   len(all_rows)

        # Parse date and time from run_time
        dt = datetime.strptime(run_time, "%Y-%m-%d %H:%M:%S")
        run_date = dt.strftime("%d-%m-%Y")
        run_time_str = dt.strftime("%H:%M:%S")

        filtered_rows = [row for row in all_rows if row[5] == run_date and row[6] == run_time_str]

        passed = sum(1 for row in filtered_rows if row[1].strip().lower() == "pass")
        failed = sum(1 for row in filtered_rows if row[1].strip().lower() == "fail")
        total = len(filtered_rows)
        return passed, failed, total

    def get_latest_run_time(self, tab_name=None):
        """
        Fetch the most recent run timestamp from the sheet.
        Assumes date is in column 6 (index 5) and time in column 7 (index 6).
        """
        sheet = self.sheet if tab_name is None else self.sheet.spreadsheet.worksheet(tab_name)
        all_rows = sheet.get_all_values()[1:]  # Skip header

        if not all_rows:
            return None

        # Parse datetime objects from date/time columns
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

    def get_browser_wise_counts(self, run_time=None, tab_name=None):
        """
        Returns a dict: { 'Chromium': {'Pass': x, 'Fail': y}, ... }
        """
        sheet = self.sheet if tab_name is None else self.sheet.spreadsheet.worksheet(tab_name)
        all_rows = sheet.get_all_values()[1:]  # Skip header

        if run_time:
            dt = datetime.strptime(run_time, "%Y-%m-%d %H:%M:%S")
            run_date = dt.strftime("%d-%m-%Y")
            run_time_str = dt.strftime("%H:%M:%S")
            all_rows = [row for row in all_rows if row[5] == run_date and row[6] == run_time_str]

        browser_counts = {}
        for row in all_rows:
            browser = row[3] if len(row) > 3 else "Unknown"
            status = row[1].strip().capitalize() if len(row) > 1 else "Unknown"
            if browser not in browser_counts:
                browser_counts[browser] = {"Pass": 0, "Fail": 0}
            if status in ["Pass", "Fail"]:
                browser_counts[browser][status] += 1

        return browser_counts
