import time
from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=False, slow_mo=100)
    context = browser.new_context()
    page = context.new_page()

    # Step 1: Open URL
    page.goto("https://seller.indiamart.com/", timeout=60000)

    # Step 2: Login
    page.wait_for_selector("input#mobNo", timeout=20000)
    page.fill("input#mobNo", "9971305703")
    page.click("button.login_btn")
    page.get_by_text("Sign in with Password").nth(1).click(force=True)
    page.fill("input#usr_password", "12345678")
    page.click("input#signWP")

    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except:
        print("⚠️ networkidle timeout ignored")
    print("✅ Login successful")

    # Step 3: Close SMAS popup
    try:
        popup_ok = page.wait_for_selector("#notify-confirm", timeout=7000)
        if popup_ok.is_visible():
            popup_ok.click()
            print("✅ SMAS popup closed")
    except:
        print("ℹ️ SMAS popup not shown")

    # Step 4: Notification Settings (toggle twice + OTP popup close)
    try:
        print("⌛ Opening Notification Settings...")
        page.click("span.settings >> xpath=..")
        page.wait_for_selector("text=Notification Settings", timeout=10000)

        checkbox_selector = "input#\\35 0"
        page.wait_for_selector(checkbox_selector, timeout=7000)
        page.eval_on_selector(checkbox_selector, "el => el.scrollIntoView({behavior: 'smooth', block: 'center'})")
        time.sleep(1)
        page.click(checkbox_selector, force=True)
        time.sleep(1)
        page.click(checkbox_selector, force=True)

        try:
            otp_popup = page.wait_for_selector("text=For Security, Please Identify Yourself", timeout=5000)
            if otp_popup.is_visible():
                page.click("button.popup-close.popup-toggle-otp")
                print("✅ OTP popup closed")
        except:
            print("ℹ️ OTP popup not shown")
    except Exception as e:
        print(f"❌ Notification Settings issue: {e}")

    # Step 5: Account Settings (email sync toggle + OTP close)
    try:
        print("⌛ Navigating to Account Settings tab...")
        page.click("a.a-tab[href*='#tab=accountsettings']", force=True)
        page.wait_for_selector("text=Sync your E-mail with IndiaMART Lead Manager", timeout=10000)
        toggle_label = "label.switch-control[for='62']"
        page.click(toggle_label, force=True)

        try:
            otp_popup2 = page.wait_for_selector("text=For Security, Please Identify Yourself", timeout=5000)
            if otp_popup2.is_visible():
                page.click("button.popup-close.popup-toggle-otp")
                print("✅ OTP popup closed")
        except:
            print("ℹ️ OTP popup not shown")
    except Exception as e:
        print(f"❌ Account Settings error: {e}")

    # Step 6: PNS Call Settings (toggle twice)
    try:
        print("⌛ Navigating to PNS Call Settings...")
        page.goto("https://seller.indiamart.com/misc/privacysettings/#tab=pnssettings", timeout=15000)
        page.wait_for_selector("text=+91-9971305703(Primary)", timeout=7000)
        toggle = "label.switch-radio-control[for='ofdefault3']"
        page.click(toggle)
        time.sleep(0.8)
        page.click(toggle)
        print("✅ PNS switch toggled twice")
    except Exception as e:
        print(f"❌ PNS settings issue: {e}")

    # Step 7: BuyLead Preferences (Unnao city add)
    try:
        print("⌛ Navigating to BuyLead Preferences...")
        page.goto("https://seller.indiamart.com/misc/privacysettings/#tab=locationpreferences", timeout=15000)
        page.wait_for_selector("text=Not Preferred Locations", timeout=10000)

        # Remove 'Unnao' if already exists
        try:
            page.click("li[id^='73857'] span.cursorpointer", force=True)
            print("✅ Unnao removed")
            time.sleep(1.5)
            page.click("button.btn.btn-primary", timeout=4000)  # Restore
            print("✅ Restore clicked")
            time.sleep(1.5)
            page.click("button.popup-close.popup-toggle-verify")  # Close restore popup
        except:
            print("ℹ️ No existing 'Unnao' to remove")

        # Type 'Unn' slowly and select dropdown
        input_box = page.wait_for_selector("input#city_others1", timeout=7000)
        input_box.fill("")
        page.evaluate("window.scrollBy(0, 150)")
        time.sleep(1)

        for char in "Unn":
            input_box.type(char)
            time.sleep(0.4)

        suggestion = page.wait_for_selector("a.ui-corner-all", timeout=5000)
        suggestion.hover()
        time.sleep(1)
        suggestion.click()
        print("✅ Unnao selected from dropdown")

        page.click("span.LC_input-txt")
        print("✅ Add button clicked")
        page.evaluate("window.scrollBy(0, -300)")
        time.sleep(2)

    except Exception as e:
        print(f"❌ BuyLead Preferences issue: {e}")

    # Final Cleanup
    finally:
        print("⏳ Closing browser after short pause...")
        time.sleep(2)
        context.close()
        browser.close()
        print("✅ Final script executed successfully.")

# Run the script
with sync_playwright() as playwright:
    run(playwright)
