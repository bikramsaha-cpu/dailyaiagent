import os
import sys
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import gc

# ----------------------- Accept Run Start/End from run_all.py ----------------------- #
if len(sys.argv) >= 3:
    run_start_time = datetime.strptime(sys.argv[1], "%Y-%m-%d %H:%M:%S")
    run_end_time = datetime.strptime(sys.argv[2], "%Y-%m-%d %H:%M:%S")
    print(f"ℹ Generating PDF for run between {run_start_time} → {run_end_time}")
else:
    run_start_time = datetime.now().replace(hour=0, minute=0, second=0)
    run_end_time = datetime.now()
    print("⚠ No timestamps provided, using today's date")

# ----------------------- Google Sheet Setup ----------------------- #
SHEET_NAME = "Buyer Automation"
WORKSHEET_NAME = "Buyermy"

scope = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]

current_dir = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(current_dir, "credentials.json")
session_dir = "/var/log/web_tester_logs/"
os.makedirs(session_dir, exist_ok=True)

if not os.path.exists(cred_path):
    raise FileNotFoundError(f"❌ Credentials file not found in {current_dir}")

creds = ServiceAccountCredentials.from_json_keyfile_name(cred_path, scope)
client = gspread.authorize(creds)

SPREADSHEET_ID = "1t_kEjtyZQ_xcOqJ3v5_apcyCEmi8V6wi5w1KjXNEyqg"
sheet = client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
data = sheet.get_all_records()

# ----------------------- Filter Only Current Run ----------------------- #
filtered_data = []
for row in data:
    date_str = str(row.get("Date", "")).strip()
    time_str = str(row.get("Time", "")).strip()
    if not date_str or not time_str:
        continue

    dt_str = f"{date_str} {time_str}"
    try:
        dt = datetime.strptime(dt_str, "%d-%m-%Y %H:%M:%S")
    except:
        continue

    if run_start_time <= dt <= run_end_time:
        filtered_data.append(row)

print(f"ℹ Rows matched for current run: {len(filtered_data)}")

# ----------------------- PDF Report Generation ----------------------- #
pdf_file = os.path.join(session_dir, "buyer-report.pdf")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="Wrap", alignment=TA_LEFT, wordWrap='CJK'))

elements = []

# Title
elements.append(Paragraph("Automation Test Report - Buyermy", styles['Title']))
elements.append(Spacer(1, 12))

# Summary Table
total_pass = sum(1 for row in filtered_data if row["Status"].lower() == "pass")
total_fail = sum(1 for row in filtered_data if row["Status"].lower() == "fail")
summary_data = [["Total Pass", "Total Fail"], [str(total_pass), str(total_fail)]]

summary_table = Table(summary_data, colWidths=[200, 200])
summary_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2196F3")),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 12),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
]))
elements.append(summary_table)
elements.append(Spacer(1, 20))

# Group rows by Test Case -> Browser
grouped = {}
for row in filtered_data:
    test_title = row["Test Title"]
    status = row["Status"]
    remarks = row.get("Remarks", "")
    browser = row.get("Browser", "")
    phone = row.get("Phone", "")
    date = row.get("Date", "")
    time = row.get("Time", "")

    case_name, _, step_name = test_title.partition("->")
    case_name = case_name.strip()
    step_name = step_name.strip() if step_name else case_name

    key = f"{case_name} ({browser})|{phone}"
    grouped.setdefault(key, []).append((
        Paragraph(step_name, styles['Wrap']),
        status,
        Paragraph(remarks, styles['Wrap']),
        f"{date} {time}".strip()
    ))

# Build tables per Test Case + Browser
for case_with_phone, steps in grouped.items():
    if "|" in case_with_phone:
        case, _ = case_with_phone.split("|", 1)
    else:
        case = case_with_phone

    remarks_exist = any(r.text for _, _, r, _ in steps if isinstance(r, Paragraph))
    heading_text = f"<b>{case}</b>"
    elements.append(Paragraph(heading_text, styles['Heading2']))
    elements.append(Spacer(1, 6))

    if remarks_exist:
        table_data = [["Step", "Status", "Remarks", "Date & Time"]]
    else:
        table_data = [["Step", "Status", "Date & Time"]]

    for step, status, remarks, datetime_str in steps:
        if remarks_exist:
            table_data.append([step, status, remarks, datetime_str])
        else:
            table_data.append([step, status, datetime_str])

    col_widths = [200, 70]
    if remarks_exist:
        col_widths += [150, 120]
    else:
        col_widths += [150]

    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4CAF50")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ]))

    for i in range(1, len(table_data)):
        if table_data[i][1].lower() == "pass":
            table.setStyle([('TEXTCOLOR', (1, i), (1, i), colors.green)])
        elif table_data[i][1].lower() == "fail":
            table.setStyle([('TEXTCOLOR', (1, i), (1, i), colors.red)])
            if remarks_exist:
                table.setStyle([('TEXTCOLOR', (2, i), (2, i), colors.red)])

    elements.append(table)
    elements.append(Spacer(1, 18))

# Save PDF
with open(pdf_file, "wb") as f:
    doc = SimpleDocTemplate(f, pagesize=A4)
    doc.build(elements)

print(f"✅ PDF report generated locally: {pdf_file}")

# Upload to Google Drive
drive_service = build('drive', 'v3', credentials=creds)
FOLDER_ID = "1tOLUhlH6ibyJUBO5rTUC1ZDSBBexYwwm"

file_metadata = {
    'name': os.path.basename(pdf_file),
    'parents': [FOLDER_ID]
}
media = MediaFileUpload(pdf_file, mimetype='application/pdf', resumable=True)

uploaded_file = drive_service.files().create(
    body=file_metadata,
    media_body=media,
    supportsAllDrives=True,
    fields='id'
).execute()

file_id = uploaded_file.get('id')
pdf_url = f"https://drive.google.com/file/d/{file_id}/view"
print(f"PDF uploaded to Google Drive: {pdf_url}")

# Delete local PDF
try:
    gc.collect()
    os.remove(pdf_file)
    print("🗑️ Local PDF deleted after upload")
except Exception as e:
    print(f"⚠ Could not delete local file: {e}")
