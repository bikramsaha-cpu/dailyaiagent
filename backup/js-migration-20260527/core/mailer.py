from __future__ import annotations

import html
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from core.settings import SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_RECIPIENTS, SMTP_USER


def send_summary_email(passed, failed, total, sheet_url, tab_name, browser_results, tab_summaries=None, recipients=None):
    sender_email = SMTP_USER or "techalerts@indiamart.com"
    receiver_email = ",".join(recipients or SMTP_RECIPIENTS or [])
    if not receiver_email:
        print("Summary email skipped: no recipients configured.")
        return
    if not SMTP_PASSWORD:
        print("Summary email skipped: no SMTP password configured.")
        return

    subject = f"Automation Report - {tab_name} - {datetime.now().strftime('%d-%b-%Y %H:%M')}"
    styles = """
        <style>
            body { font-family: Arial, sans-serif; color: #333; }
            h2 { color: #2F4F4F; }
            .summary-card {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                background: #f9f9f9;
                margin-bottom: 20px;
                width: fit-content;
            }
            .summary-card p { margin: 5px 0; font-size: 16px; }
            .passed { color: green; font-weight: bold; }
            .failed { color: red; font-weight: bold; }
            table {
                border-collapse: collapse;
                margin-top: 10px;
                width: 60%;
            }
            th, td {
                border: 1px solid #ccc;
                padding: 8px 12px;
                text-align: center;
            }
            th {
                background-color: #2F4F4F;
                color: white;
            }
            tr:nth-child(even) { background-color: #f2f2f2; }
        </style>
    """

    tab_summary_html = ""
    if tab_summaries:
        tab_summary_html = """
            <h3>Per-Tab Breakdown</h3>
            <table>
                <tr>
                    <th>Tab Name</th>
                    <th>Passed</th>
                    <th>Failed</th>
                    <th>Total</th>
                </tr>
        """
        for t_name, counts in tab_summaries.items():
            tab_summary_html += f"""
                <tr>
                    <td>{t_name}</td>
                    <td class="passed">{counts[0]}</td>
                    <td class="failed">{counts[1]}</td>
                    <td>{counts[2]}</td>
                </tr>
            """
        tab_summary_html += "</table><br>"

    browser_summary_html = """
        <h3>Browser-wise Breakdown</h3>
        <table>
            <tr>
                <th>Browser</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Total</th>
            </tr>
    """
    for browser, counts in browser_results.items():
        total_browser = counts["Pass"] + counts["Fail"]
        browser_summary_html += f"""
            <tr>
                <td>{browser.capitalize()}</td>
                <td class="passed">{counts['Pass']}</td>
                <td class="failed">{counts['Fail']}</td>
                <td>{total_browser}</td>
            </tr>
        """
    browser_summary_html += "</table><br>"

    body = f"""
        <html>
        <head>{styles}</head>
        <body>
            <h2>Test Summary: <u>{tab_name}</u></h2>
            <div class="summary-card">
                <p><b>Passed:</b> <span class="passed">{passed}</span></p>
                <p><b>Failed:</b> <span class="failed">{failed}</span></p>
                <p><b>Total:</b> {total}</p>
            </div>
            {tab_summary_html}
            {browser_summary_html}
            <p><b>Full Results:</b> <a href="{sheet_url}">{sheet_url}</a></p>
        </body>
        </html>
    """

    message = MIMEMultipart()
    message["From"] = formataddr(("QA Automation Reports", sender_email))
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(sender_email, SMTP_PASSWORD)
        server.send_message(message)
    print("Summary email sent successfully.")


def send_run_report_email(summary: dict, recipients=None):
    sender_email = SMTP_USER or "techalerts@indiamart.com"
    receiver_email = ",".join(recipients or SMTP_RECIPIENTS or [])
    if not receiver_email:
        print("Run report email skipped: no recipients configured.")
        return
    if not SMTP_PASSWORD:
        print("Run report email skipped: no SMTP password configured.")
        return

    suite_name = summary.get("suite_name", "Automation")
    module_name = summary.get("module_name", "Run")
    status = summary.get("status", "-")
    report_path = summary.get("report_path", "")
    started_at = summary.get("started_at", "-")
    finished_at = summary.get("finished_at", "-")
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    total = summary.get("total", 0)
    browser_results = summary.get("browser_breakdown", {}) or {}

    subject = f"E2E Agent Report - {suite_name}/{module_name} - {datetime.now().strftime('%d-%b-%Y %H:%M')}"
    styles = """
        <style>
            body { font-family: Arial, sans-serif; color: #334155; }
            h2 { color: #0f172a; }
            .summary-card {
                border: 1px solid #dbe3ee;
                border-radius: 10px;
                padding: 16px;
                background: #f8fafc;
                margin-bottom: 20px;
                width: fit-content;
            }
            .summary-card p { margin: 6px 0; font-size: 15px; }
            .passed { color: #15803d; font-weight: bold; }
            .failed { color: #dc2626; font-weight: bold; }
            .status { font-weight: bold; }
            table {
                border-collapse: collapse;
                margin-top: 10px;
                width: 70%;
            }
            th, td {
                border: 1px solid #cbd5e1;
                padding: 8px 12px;
                text-align: center;
            }
            th {
                background-color: #0f172a;
                color: white;
            }
            tr:nth-child(even) { background-color: #f8fafc; }
            code {
                background: #e2e8f0;
                padding: 2px 4px;
                border-radius: 4px;
            }
        </style>
    """

    browser_summary_html = """
        <h3>Browser-wise Breakdown</h3>
        <table>
            <tr>
                <th>Browser</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Total</th>
            </tr>
    """
    for browser, counts in browser_results.items():
        total_browser = counts.get("Pass", 0) + counts.get("Fail", 0)
        browser_summary_html += f"""
            <tr>
                <td>{browser.capitalize()}</td>
                <td class="passed">{counts.get('Pass', 0)}</td>
                <td class="failed">{counts.get('Fail', 0)}</td>
                <td>{total_browser}</td>
            </tr>
        """
    browser_summary_html += "</table><br>"

    report_html = f"<p><b>HTML Report:</b> <code>{report_path or 'Not available'}</code></p>"
    body = f"""
        <html>
        <head>{styles}</head>
        <body>
            <h2>E2E Agent Run: <u>{suite_name} / {module_name}</u></h2>
            <div class="summary-card">
                <p><b>Status:</b> <span class="status">{status}</span></p>
                <p><b>Passed:</b> <span class="passed">{passed}</span></p>
                <p><b>Failed:</b> <span class="failed">{failed}</span></p>
                <p><b>Total:</b> {total}</p>
                <p><b>Started:</b> {started_at}</p>
                <p><b>Finished:</b> {finished_at}</p>
            </div>
            {browser_summary_html}
            {report_html}
        </body>
        </html>
    """

    message = MIMEMultipart()
    message["From"] = formataddr(("QA Automation Reports", sender_email))
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(sender_email, SMTP_PASSWORD)
        server.send_message(message)
    print("Run report email sent successfully.")


def send_filtered_sheet_report_email(
    *,
    module_label: str,
    sheet_name: str,
    tab_name: str,
    records: list[dict[str, str]],
    filters: dict[str, str],
    recipients: list[str] | None = None,
) -> dict[str, object]:
    sender_email = SMTP_USER or "techalerts@indiamart.com"
    resolved_recipients = [email.strip() for email in (recipients or SMTP_RECIPIENTS or []) if email.strip()]
    if not resolved_recipients:
        raise ValueError("No email recipients configured. Add SMTP recipients in Workspace Settings first.")
    if not SMTP_PASSWORD:
        raise ValueError("SMTP password is not configured on the backend machine.")

    total = len(records)
    passed = sum(1 for row in records if (row.get("Status", "").strip().lower() == "pass"))
    failed = sum(1 for row in records if (row.get("Status", "").strip().lower() == "fail"))
    pass_rate = round((passed / total) * 100, 1) if total else 0.0
    failed_records = [row for row in records if row.get("Status", "").strip().lower() == "fail"]
    selected_date = filters.get("Start Date", "Any")
    end_date = filters.get("End Date", "Any")
    if selected_date in {"", "Any"} and end_date not in {"", "Any"}:
        selected_date = end_date
    elif end_date not in {"", "Any"} and end_date != selected_date:
        selected_date = f"{selected_date} to {end_date}"

    fail_table_rows = "".join(
        """
        <tr>
            <td>{title}</td>
            <td>{remarks}</td>
            <td>{browser}</td>
            <td>{phone}</td>
            <td>{date}</td>
            <td>{time}</td>
        </tr>
        """.format(
            title=html.escape(str(record.get("Test Title", "-") or "-")),
            remarks=html.escape(str(record.get("Remarks", "-") or "-")),
            browser=html.escape(str(record.get("Browser", "-") or "-")),
            phone=html.escape(str(record.get("Phone", "-") or "-")),
            date=html.escape(str(record.get("Date", "-") or "-")),
            time=html.escape(str(record.get("Time", "-") or "-")),
        )
        for record in failed_records
    )

    styles = """
        <style>
            body { font-family: Arial, sans-serif; color: #334155; padding: 20px; }
            h2 { color: #0f172a; margin-bottom: 6px; }
            .meta { color: #64748b; margin-bottom: 18px; }
            .summary-grid { display: flex; gap: 12px; flex-wrap: wrap; margin: 18px 0; }
            .summary-card {
                border: 1px solid #dbe3ee;
                border-radius: 12px;
                padding: 14px 16px;
                min-width: 140px;
                background: #f8fafc;
            }
            .summary-card .label {
                color: #64748b;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.08em;
            }
            .summary-card .value {
                color: #0f172a;
                font-size: 24px;
                font-weight: 700;
                margin-top: 8px;
            }
            .date-card {
                margin: 18px 0;
                border: 1px solid #dbe3ee;
                border-radius: 12px;
                background: #f8fafc;
                padding: 14px 16px;
                width: fit-content;
            }
            .date-card .label {
                color: #64748b;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.08em;
            }
            .date-card .value {
                color: #0f172a;
                font-size: 18px;
                font-weight: 700;
                margin-top: 6px;
            }
            .fail-table {
                border-collapse: collapse;
                width: 100%;
            }
            .fail-table td, .fail-table th {
                border: 1px solid #dbe3ee;
                padding: 8px 10px;
                text-align: left;
                vertical-align: top;
            }
            .fail-table th {
                background: #0f172a;
                color: white;
            }
            .fail-table tr:nth-child(even) { background: #f8fafc; }
            .fail-title { color: #b91c1c; margin-top: 22px; }
            .clean-note {
                margin-top: 22px;
                padding: 14px 16px;
                border-radius: 12px;
                background: #ecfdf5;
                border: 1px solid #bbf7d0;
                color: #166534;
                font-weight: 600;
            }
        </style>
    """

    body = f"""
        <html>
        <head>{styles}</head>
        <body>
            <h2>Daily Smoke Testing Report</h2>
            <div class="meta">Sheet: {html.escape(sheet_name)} | Generated at {datetime.now().strftime('%d-%b-%Y %H:%M')}</div>
            <div class="meta">Module: {html.escape(module_label)} | Tab: {html.escape(tab_name)}</div>

            <div class="summary-grid">
                <div class="summary-card"><div class="label">Filtered Total</div><div class="value">{total}</div></div>
                <div class="summary-card"><div class="label">Filtered Passed</div><div class="value" style="color:#15803d;">{passed}</div></div>
                <div class="summary-card"><div class="label">Filtered Failed</div><div class="value" style="color:#dc2626;">{failed}</div></div>
                <div class="summary-card"><div class="label">Filtered Pass Rate</div><div class="value" style="color:#1d4ed8;">{pass_rate}%</div></div>
            </div>

            <div class="date-card">
                <div class="label">Selected Date</div>
                <div class="value">{html.escape(selected_date or 'Any')}</div>
            </div>

            {
                f'''
                <h3 class="fail-title">Failed Cases with Remarks</h3>
                <table class="fail-table">
                    <thead>
                        <tr>
                            <th>Test Title</th>
                            <th>Remarks</th>
                            <th>Browser</th>
                            <th>Phone</th>
                            <th>Date</th>
                            <th>Time</th>
                        </tr>
                    </thead>
                    <tbody>{fail_table_rows}</tbody>
                </table>
                '''
                if failed_records
                else '<div class="clean-note">No failed cases found in the selected filtered data.</div>'
            }
        </body>
        </html>
    """

    message = MIMEMultipart()
    message["From"] = formataddr(("QA Automation Reports", sender_email))
    message["To"] = ",".join(resolved_recipients)
    message["Subject"] = f"Daily Smoke Testing Report - {datetime.now().strftime('%d-%b-%Y')}"
    message.attach(MIMEText(body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(sender_email, SMTP_PASSWORD)
        server.send_message(message)

    return {
        "sent": True,
        "recipients": resolved_recipients,
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
    }
