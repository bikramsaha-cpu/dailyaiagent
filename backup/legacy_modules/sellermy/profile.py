import time
from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=False, slow_mo=100)
    context = browser.new_context()
    page = context.new_page()

    # Step 1: Open URL
    page.goto("https://seller.indiamart.com/", timeout=60000)

    # Step 2: Enter Mobile Number
    page.wait_for_selector("input#mobNo", timeout=20000)
    page.fill("input#mobNo", "9971305703")

    # Step 3: Click on "Start Selling"
    page.click("button.login_btn")

    # Step 4: Click on "Sign in with Password"
    page.get_by_text("Sign in with Password").nth(1).click(force=True)

    # Step 5: Enter Password and Login
    page.fill("input#usr_password", "12345678")
    page.click("input#signWP")

    # Step 6: Wait for page load
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except:
        print("⚠️ networkidle timeout ignored")
    print("✅ Login successful")

    # Step 7: Close SMAS popup (if shown)
    try:
        popup_ok = page.wait_for_selector("#notify-confirm", timeout=7000)
        if popup_ok.is_visible():
            popup_ok.click()
            print("✅ SMAS popup closed")
    except:
        print("ℹ️ SMAS popup not shown")

    # Step 8: Go to Profile page
    page.goto("https://seller.indiamart.com/companyprofile/manageprofile", timeout=60000)
    print("✅ Navigated to Profile page")
    time.sleep(2)

    # Step 9: Additional Details tab
    try:
        print("⌛ Waiting for 'Additional Details' tab...")
        tab = page.wait_for_selector("a.a-tab[href*='tab=businessprofile']", timeout=10000)
        page.evaluate("el => el.click()", tab)
        print("✅ 'Additional Details' tab clicked")
    except Exception as e:
        print(f"❌ Failed: {e}")
    time.sleep(2)

    # Step 10: CEO Name Toggle
    try:
        ceo_input = page.locator("#ceo_name_b")
        is_disabled = ceo_input.get_attribute("disabled")
        if is_disabled:
            print("❌ CEO Name not editable.")
        else:
            current_name = ceo_input.input_value().strip()
            if current_name == "Alok Shukla":
                ceo_input.fill("Alok K Shukla")
            elif current_name == "Alok K Shukla":
                ceo_input.fill("Alok Shukla")
            print(f"✅ CEO Name toggled from '{current_name}'")
            page.keyboard.press("Tab")
    except Exception as e:
        print(f"❌ CEO Name error: {e}")

    # Step 11: Trust Profile tab
    try:
        print("⌛ Trust Profile tab...")
        trust_tab = page.locator("a.a-tab[href*='tab=trustprofile']")
        trust_tab.wait_for(state="visible", timeout=8000)
        page.evaluate("el => el.click()", trust_tab)
        print("✅ Trust tab clicked")
        page.wait_for_selector("text=Build Your Trust Profile", timeout=15000)
        print("✅ Trust content loaded")
    except Exception as e:
        print(f"⚠️ Trust tab failed: {e}")
        try:
            page.goto("https://seller.indiamart.com/companyprofile/manageprofile#tab=trustprofile", timeout=60000)
            page.wait_for_selector("text=Build Your Trust Profile", timeout=15000)
            print("✅ Trust tab fallback load success")
        except Exception as e2:
            print(f"❌ Trust tab fallback failed: {e2}")

    print("➡️ Proceeding to next tab after Trust Profile...")
    time.sleep(2)

    # Step 12: Website Pages
    try:
        print("⌛ Website Pages tab...")
        website_tab = page.locator("a.a-tab[href*='tab=websitepages']")
        website_tab.wait_for(state="visible", timeout=10000)
        page.evaluate("el => el.click()", website_tab)
        print("✅ Website Pages tab clicked")
        page.wait_for_selector("text=HOME PAGE", timeout=10000)
    except:
        page.goto("https://seller.indiamart.com/companyprofile/manageprofile#tab=websitepages", timeout=60000)
        page.wait_for_selector("text=HOME PAGE", timeout=15000)
    time.sleep(2)

    # Step 13: Ratings & Review
    try:
        print("⌛ Ratings & Review tab...")
        page.goto("https://seller.indiamart.com/companyprofile/manageprofile#tab=ratings", timeout=60000)
        page.wait_for_selector("text=Ratings", timeout=15000)
        print("✅ Ratings & Review content loaded")
    except Exception as e:
        print(f"❌ Ratings tab failed: {e}")
    time.sleep(2)

    # Step 14: Share Catalog
    try:
        print("⌛ Share Catalog tab...")
        page.goto("https://seller.indiamart.com/companyprofile/manageprofile#tab=personalizedurl", timeout=60000)
        page.wait_for_selector("text=Share your Catalog", timeout=15000)
        print("✅ Share Catalog content loaded")
    except Exception as e:
        print(f"❌ Share Catalog failed: {e}")
    time.sleep(2)

    # Step 15: Performance Reports
    try:
        print("⌛ Performance Reports tab...")
        page.goto("https://seller.indiamart.com/companyprofile/manageprofile#tab=reports", timeout=60000)
        page.wait_for_selector("text=Performance Reports", timeout=15000)
        print("✅ Performance Reports loaded")
    except Exception as e:
        print(f"❌ Performance Reports failed: {e}")
    time.sleep(2)

       # Step 16: Videos tab
    try:
        print("⌛ Navigating to Videos tab...")
        video_tab = page.locator("a.a-tab[href*='tab=video']")
        video_tab.wait_for(state="visible", timeout=10000)
        video_tab.click(force=True)
        print("✅ Videos tab clicked")
        time.sleep(2)

        # Wait for heading
        page.wait_for_selector("h3.select-account-title:has-text('Select your social media account')", timeout=15000)
        print("✅ Heading 'Select your social media account' found")

        # Click on Instagram
        insta_btn = page.locator("span.social-connect-btn__label", has_text="Instagram").locator("..")
        insta_btn.click(force=True)
        print("✅ Clicked on Instagram")
        page.wait_for_url("**instagram.com**", timeout=10000)
        print("✅ Instagram redirection successful")

        # Go back
        page.go_back()
        page.wait_for_selector("span.social-connect-btn__label", has_text="YouTube", timeout=10000)

        # Click on YouTube
        yt_btn = page.locator("span.social-connect-btn__label", has_text="YouTube").locator("..")
        yt_btn.click(force=True)
        print("✅ Clicked on YouTube")
        page.wait_for_url("**youtube.com**", timeout=10000)
        print("✅ YouTube redirection successful")

    except Exception as e:
        print(f"❌ Social media redirection validation failed: {e}")

with sync_playwright() as playwright:
    run(playwright)