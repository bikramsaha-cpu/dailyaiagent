import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime

def send_summary_email(
    passed, failed, total, sheet_url, tab_name,
    browser_results, tab_summaries=None, failed_cases=None,
    pdf_drive_url=None
):
    """
    Send an HTML summary email with:
    - Browser and tab-wise breakdown
    - Download PDF CTA
    - Friendly failed test case formatting
    """
    sender_email = "techalerts@indiamart.com"
    receiver_email = "sumit.gore@indiamart.com,bikram.saha@indiamart.com,sunny.sachdeva@indiamart"
    # receiver_email = "monarch.hasija@indiamart.com,kumar.himanshu1@indiamart.com,sunny.sachdeva@indiamart.com,shikha.garg@indiamart.com,shreenath.asati@indiamart.com,buyermy@indiamart.com,shobhna.verma@indiamart.com,bikram.saha@indiamart.com"
    subject = f"📊 {tab_name} - Automation Report - {datetime.now().strftime('%d-%b-%Y %H:%M')}"

    # --- CSS Styles ---
    styles = """
        <style>
            body { font-family: Arial, sans-serif; color: #333; }
            h2 { color: #2F4F4F; }
            h3 { color: #1E90FF; margin-top: 25px; }
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
                width: 95%;
            }
            th, td {
                border: 1px solid #ccc;
                padding: 6px 10px;
                text-align: left;
                font-size: 14px;
            }
            th {
                background-color: #2F4F4F;
                color: white;
            }
            tr:nth-child(even) { background-color: #f2f2f2; }
            .cta-button {
                display: inline-block;
                padding: 12px 20px;
                font-size: 16px;
                font-weight: bold;
                color: #fff;
                background-color: #FF5722; /* brighter orange for CTA */
                text-decoration: none;
                border-radius: 8px;
                margin-top: 10px;
            }
            .cta-button:hover {
                background-color: #E64A19;
            }
            .test-case-heading {
                font-size: 18px;
                font-weight: bold;
                color: #333;
                margin: 15px 0 5px 0;
            }
            .test-case-subheading {
                font-size: 14px;
                color: #666;
                margin-bottom: 10px;
            }
        </style>
    """

    # --- Tab Summary ---
    tab_summary_html = ""
    if tab_summaries:
        tab_summary_html = """
            <h3>📄 Per-Tab Breakdown</h3>
            <table>
                <tr>
                    <th>Tab Name</th>
                    <th>✅ Passed</th>
                    <th>❌ Failed</th>
                    <th>📊 Total</th>
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

    # --- Browser Summary ---
    browser_summary_html = """
        <h3>🧪 Browser-wise Breakdown</h3>
        <table>
            <tr>
                <th>Browser</th>
                <th>✅ Passed</th>
                <th>❌ Failed</th>
                <th>📊 Total</th>
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


    # --- Failed Cases ---
    failed_cases_html = ""
    if failed_cases and len(failed_cases) > 0:
        failed_cases_html = "<h3>❌ Failed Test Scenarios</h3>"
        
        for case in failed_cases:
            scenario_name = case.get("test_title", "")
            # split test_title by '->' if exists
            if "->" in scenario_name:
                test_scenario, step_name = scenario_name.split("->", 1)
                test_scenario = test_scenario.strip()
                step_name = step_name.strip()
            else:
                test_scenario = scenario_name
                step_name = ""

            # Add scenario as heading above table
            failed_cases_html += f"""
                <div style="font-weight:bold; margin-top:15px;">[Test Scenario: {test_scenario}]</div>
                <table>
                    <tr>
                        <th>Step</th>
                        <th>Status</th>
                        <th>Remarks</th>
                        <th>Browser</th>
                    </tr>
                    <tr>
                        <td>{step_name}</td>
                        <td class="failed">{case.get("status","")}</td>
                        <td>{case.get("remarks","-")}</td>
                        <td>{case.get("browser","")}</td>
                    </tr>
                </table><br>
            """



    # --- Download PDF CTA ---
    download_pdf_html = ""
    if pdf_drive_url:
        download_pdf_html = f"""
            
            <a href="{pdf_drive_url}" class="cta-button" target="_blank" style="color:white;">Download PDF Report</a>
            <br><br>
        """

    # --- Email Body ---
    body = f"""
        <html>
        <head>{styles}</head>
        <body>
            <h2>📝 Test Summary: <u>{tab_name}</u></h2>
            <div class="summary-card">
                <p><b>✅ Passed:</b> <span class="passed">{passed}</span></p>
                <p><b>❌ Failed:</b> <span class="failed">{failed}</span></p>
                <p><b>📊 Total:</b> {total}</p>
            </div>
            {tab_summary_html}
            {browser_summary_html}
            {failed_cases_html}
            {download_pdf_html}
            <p>📄 <b>Full Sheet Results:</b> <a href="{sheet_url}">{sheet_url}</a></p>
        </body>
        </html>
    """

    # --- Build & Send Email ---
    message = MIMEMultipart("mixed")
    message["From"] = formataddr(("QA Automation Reports", sender_email))
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, os.getenv("AUTOMATION_SMTP_PASSWORD", ""))  # Replace with env-based app password
            server.send_message(message)
            print("✅ Summary email sent successfully with CTA.")
    except Exception as e:
        print("❌ Failed to send summary email:", str(e))
