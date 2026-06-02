import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from datetime import datetime

def send_summary_email(passed, failed, total, sheet_url, tab_name, browser_results):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from datetime import datetime

    sender_email = "techalerts@indiamart.com"
    receiver_email = "shobhna.verma@indiamart.com,bikram.saha@indiamart.com,shukla.alok@indiamart.com,sunny.sachdeva@indiamart.com"
    # receiver_email = "guduru.abhiram@indiamart.com,shobhna.verma@indiamart.com,bikram.saha@indiamart.com,shukla.alok@indiamart.com,mytester@indiamart.com,harshitg@indiamart.com,samarth@indiamart.com"

    subject = f"📊{tab_name} - Automation Report - {datetime.now().strftime('%d-%b-%Y %H:%M')}"
    
        # Generate browser-wise summary HTML
    browser_summary_html = """
        <h3>🧪 Browser-wise Breakdown</h3>
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
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
                <td>{counts['Pass']}</td>
                <td>{counts['Fail']}</td>
                <td>{total_browser}</td>
            </tr>
            """
    browser_summary_html += "</table><br>"

    # Create the body with summary and sheet link
    body = f"""
    <h2>📝 Test Summary: <u>{tab_name}</u> Tab</h2>
    <p><b>✅ Passed:</b> {passed}</p>
    <p><b>❌ Failed:</b> {failed}</p>
    <p><b>📊 Total:</b> {total}</p>
    <br>
    {browser_summary_html}
    <p>📄 View full results in Google Sheet: <a href="{sheet_url}">{sheet_url}</a></p>
    """

    # Create email
    message = MIMEMultipart()
    message["From"] = formataddr(("QA Automation Reports", sender_email))
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "html"))

    # Send email
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, os.getenv("AUTOMATION_SMTP_PASSWORD", ""))  # Use env-based app password
            server.send_message(message)
            print("✅ Summary email sent successfully.")
    except Exception as e:
        print("❌ Failed to send summary email:", str(e))
    
