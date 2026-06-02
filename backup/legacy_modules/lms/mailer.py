import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime

def send_summary_email(passed, failed, total, sheet_url, tab_name, browser_results, tab_summaries=None):
    sender_email = "techalerts@indiamart.com"
    # receiver_email = "shukla.alok@indiamart.com,sunny.sachdeva@indiamart.com,viplow.srivastava@indiamart.com,saurabh.rai02@indiamart.com, patil.shubham1@indiamart.com, yash.jaiswal@indiamart.com,gaurang.manchanda@indiamart.com,shobhna.verma@indiamart.com,bikram.saha@indiamart.com"
    receiver_email = "bikram.saha@indiamart.com,shukla.alok@indiamart.com,sunny.sachdeva@indiamart.com"

    subject = f"📊 {tab_name} - Automation Report - {datetime.now().strftime('%d-%b-%Y %H:%M')}"

    # --- Style definitions ---
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

    # Per-tab breakdown table (optional)
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

    # Browser-wise breakdown
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

    # Email body
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
            <p>📄 <b>Full Results:</b> <a href="{sheet_url}">{sheet_url}</a></p>
        </body>
        </html>
    """

    # Create email
    message = MIMEMultipart()
    message["From"] = formataddr(("QA Automation Reports", sender_email))
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, os.getenv("AUTOMATION_SMTP_PASSWORD", ""))  # Secure via environment variable
            server.send_message(message)
            print("✅ Summary email sent successfully.")
    except Exception as e:
        print("❌ Failed to send summary email:", str(e))
