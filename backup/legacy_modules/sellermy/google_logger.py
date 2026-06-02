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
