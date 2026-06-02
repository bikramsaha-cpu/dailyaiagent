from playwright.sync_api import sync_playwright, TimeoutError
from google_logger import GoogleSheetLogger
from datetime import datetime
from collections import defaultdict
import random

MOBILE_NUMBER = "9643193481"
BROWSERS = ["chromium", "firefox"]
browser_results = defaultdict(lambda: {"Pass": 0, "Fail": 0})
session_file_path = "/var/log/web_tester_logs/seller_bllogin.json"

def select_radio_option_by_label(page, option_text):
    page.wait_for_selector("label.rdo_btn", timeout=15000)
    labels = page.query_selector_all("label.rdo_btn")
    for label in labels:
        text = label.inner_text().strip()
        if option_text.lower() in text.lower():
            try:
                label.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                label.click()
                print(f"âœ… Selected location: {option_text}")
                return
            except Exception as e:
                print(f"âŒ Failed to click label: {e}")
    print(f"âŒ Option '{option_text}' not found.")

def select_order_value(page, order_value_label):
    print(f"ðŸ” Looking for order value: {order_value_label}")
    try:
        toggle_arrow = page.locator("li[title='Above 50,000'] .arwMenu")
        if toggle_arrow.is_visible():
            toggle_arrow.click()
            page.wait_for_timeout(1000)
    except:
        pass

    radio_locator = page.locator(f"li[title='{order_value_label}'] input[type='radio']")
    if radio_locator.count() == 0:
        print(f"âŒ No radio button found with title '{order_value_label}'")
        return

    try:
        radio_locator.first.evaluate("e => e.click()")
        print(f"âœ… Selected order value: {order_value_label}")
    except Exception as e:
        print(f"âŒ Failed to select order value: {e}")

def select_lead_type(page, lead_type_label):
    print(f"ðŸ” Looking for lead type: {lead_type_label}")
    try:
        arrow = page.locator("li[title='Business'] .arwMenu")
        if arrow.is_visible():
            arrow.click()
            page.wait_for_timeout(1000)
    except:
        pass

    checkbox_input = page.locator(f"li[title*='{lead_type_label}'] input[type='checkbox']")
    if checkbox_input.count() == 0:
        print(f"âŒ Could not find checkbox for lead type: {lead_type_label}")
        return

    try:
        checkbox_input.first.evaluate("e => e.click()")
        print(f"âœ… Selected lead type: {lead_type_label}")
    except Exception as e:
        print(f"âŒ Failed to select lead type: {e}")

def main():
    sheet_logger = None
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tab_name = "Sellerbl - Recent"

    try:
        sheet_logger = GoogleSheetLogger("Seller My Automation", tab_name)
        print("âœ… GoogleSheetLogger initialized successfully")
    except Exception as e:
        print("âš ï¸ Google Sheet logging is disabled due to initialization failure.")
        sheet_logger = None

    selected_option = "India"
    selected_order_value = "Above 1 Lakh"
    lead_type_option = "GST"

    with sync_playwright() as playwright:
        for browser_name in BROWSERS:
            print(f"\nðŸ§ª Running automation on: {browser_name}")
            try:
                browser = getattr(playwright, browser_name).launch(headless=False, slow_mo=400)
                context = browser.new_context(storage_state=session_file_path)
                page = context.new_page()

                def log_step(test_title, status, remarks):
                    full_title = f"[{browser_name}] {test_title}"
                    if sheet_logger:
                        sheet_logger.log_status(
                            full_title,
                            status,
                            remarks,
                            browser_name,
                            MOBILE_NUMBER,
                            run_time
                        )
                    browser_results[browser_name][status] += 1
                    if status == "Pass":
                        print(f"âœ… {full_title}")
                    else:
                        print(f"âŒ {full_title} - {remarks}")
                        screenshot_name = f"{browser_name}_{test_title.replace(' ', '_')}.png"
                        page.screenshot(path=screenshot_name)

                
                    # Step 1: Navigate to Seller IndiaMart
                    #page.goto("https://seller.indiamart.com/")
                    # After OTP success and dashboard loaded
                    # After OTP success and dashboard loaded
                     # Step 1: Navigate to Buyer Dashboard
                # Step 1: Navigate to Buyer Dashboard
                try:
                    page.goto("https://buyer.indiamart.com")
                    page.wait_for_timeout(2000)
                    log_step("Navigate to Buyer Dashboard Header Section ", "Pass", "Logged in using saved session")
                except Exception as e:
                    log_step("Navigate to Buyer Dashboard", "Fail", str(e))

                
            
            
                try:
                    page.click("//*[@id='sellTool']")
                    page.wait_for_timeout(2000)
                    
                    log_step("Header Section", "Pass", "Flow completed successfully")
                except Exception as e:
                    log_step("Header Section", "Fail", str(e))

              


                try:
                    # Step 2: Go to Recent BuyLeads
                        page.wait_for_selector('a:has(#recentBuyLead)', timeout=10000)
                        page.click('a:has(#recentBuyLead)')
                        log_step("Navigate to Recent BuyLeads", "Pass", "Successfully navigated to Recent BuyLeads")
                except Exception as e:
                        log_step("Navigate to Recent BuyLeads", "Fail", str(e))
                        return False

                    # Step 3: Apply Filters
                try:

                        # Click on "More Filters"
                        more_filters_btn = page.locator("#vw_svd_fltr_btn_id")  # Adjust selector if needed
                        more_filters_btn.click()
                        page.wait_for_timeout(1000)  # wait for panel to open

                        # Count saved filters
                        saved_filters = page.locator("#indexed_DB_saved_filter_all li")  # List items in saved filters section
                        filter_count = saved_filters.count()

                        if filter_count >= 5:
                            print(f"âš  Found {filter_count} saved filters. Deleting extras...")
                            
                            # Loop until fewer than 5 remain
                            while saved_filters.count() >= 5:
                                first_filter = saved_filters.nth(0)

                                # Click the pencil (edit) icon
                                edit_icon = first_filter.locator(".recommtltp")
                                edit_icon.wait_for(state="visible", timeout=5000)  # waits for THIS locator to be visible
                                edit_icon.click()

                                # Click delete button in popup (adjust selector as needed)
                                delete_btn = page.locator("span[onclick*='delete_indexedDB_data']")
                                delete_btn.click()
                                page.wait_for_timeout(1000)

                                # Update count
                                saved_filters = page.locator("#saved_filter_sec li")

                            cross_btn=page.locator("span[onclick*='closed_View_saved_fltr();']")
                            cross_btn.click()
                            print("âœ… Reduced saved filters to below 5.")
                        else:
                            cross_btn=page.locator("span[onclick*='closed_View_saved_fltr();']")
                            cross_btn.click()
                            print(f"â„¹ Only {filter_count} filters found. No deletion needed.")

                        select_radio_option_by_label(page, selected_option)
                        select_order_value(page, selected_order_value)
                        select_lead_type(page, lead_type_option)
                        log_step("Apply Filters", "Pass", "Filters applied successfully")
                except Exception as e:
                        log_step("Apply Filters", "Fail", str(e))
                        continue                

                    # Step 4: Save Filter
                try:
                         #page.wait_for_selector("#save_filter_btn", timeout=5000)
                        #page.click("#save_filter_btn")
                        save_filter_btn = page.locator("#save_filter_btn")
                        save_filter_btn.wait_for(state="visible", timeout=5000)
                        save_filter_btn.click(force=True)
                        log_step("Click Save Filter", "Pass", "Clicked Save Filter button")
                        
                        page.wait_for_selector("#filter_name", timeout=5000)
                        filter_name = f"A_Filter_{random.randint(1000, 9999)}"
                        page.fill("#filter_name", filter_name)
                        log_step("Enter Filter Name", "Pass", f"Entered filter name: {filter_name}")
                        
                        page.wait_for_selector("#save_indexed_DB_btn_id", timeout=5000)
                        page.click("#save_indexed_DB_btn_id")
                        log_step("Save Filter", "Pass", "Filter saved successfully")
                except Exception as e:
                        log_step("Save Filter", "Fail", str(e))
                        continue


                    # Step 5: View Saved Filters
                try:
                        page.wait_for_selector("#vw_svd_fltr_btn_id", timeout=5000)
                        page.click("#vw_svd_fltr_btn_id")
                        log_step("Open More Filters", "Pass", "Opened More Filters")
                        
                        page.wait_for_timeout(1000)
                        if page.is_visible("span.SLC_cp"):
                            page.click("span.SLC_cp")
                            log_step("Close More Filters", "Pass", "Closed More Filters")
                except Exception as e:
                        log_step("View Saved Filters", "Fail", str(e))
                        continue

                    # Step 6: View Similar Leads
                try:
                        page.wait_for_selector(".icon_name_cls", timeout=15000)
                        page.click(".icon_name_cls")
                        log_step("View Similar Leads", "Pass", "Clicked View Similar")
                except Exception as e:
                        log_step("View Similar Leads", "Fail", str(e))
                        continue

                    # Step 7: Return to Recent BuyLeads
                try:
                        page.locator("div.tabs-header a:has-text('Recent')").click()
                        # page.click("text=Recent Leads")
                        log_step("Navigate to Recent BuyLeads", "Pass", "Successfully navigated to Recent BuyLeads")
                except Exception as e:
                        log_step("Navigate to Recent BuyLeads", "Fail", str(e))
                        return False
                    
                     
                     # Step 8: Shortlist a Lead
                try:
                        page.wait_for_timeout(2000)

                        # Try finding non-shortlisted leads until one is clickable
                        max_scroll_attempts = 5
                        shortlisted = False

                        for _ in range(max_scroll_attempts):
                            not_shortlisted_cards = page.locator("span[id^='markFav']")

                            count = not_shortlisted_cards.count()
                            if count > 0:
                                for i in range(count):
                                    shortlist_control = not_shortlisted_cards.nth(i)

                                    # Ensure it's visible before clicking
                                    if shortlist_control.is_visible():
                                        shortlist_control.scroll_into_view_if_needed()
                                        page.wait_for_timeout(1000)

                                        shortlist_control.click()
                                        log_step("Shortlist Lead", "Pass", "Lead shortlisted")

                                        # Extract offer_id
                                        offer_id_locator = shortlist_control.locator(
                                            "xpath=ancestor::div[3]//input[@name='ofrid']"
                                        )
                                        offer_id = offer_id_locator.get_attribute("value")

                                        if offer_id:
                                            log_step("Extract Offer ID", "Pass", f"Extracted offer_id: {offer_id}")
                                        else:
                                            log_step("Extract Offer ID", "Fail", "Failed to extract offer_id")

                                        shortlisted = True
                                        break

                            if shortlisted:
                                break

                            # Scroll down to load more leads
                            page.mouse.wheel(0, 800)
                            page.wait_for_timeout(2000)

                        if not shortlisted:
                            log_step("Shortlist Lead", "Fail", "No non-shortlisted leads found after scrolling.")

                except Exception as e:
                        log_step("Shortlist Lead", "Fail", str(e))
                        continue


                    # Step 9: View Shortlisted Leads
                try:
                        page.wait_for_selector("li > a:has-text('Shortlisted')", timeout=15000)
                        page.click("li > a:has-text('Shortlisted')")
                        page.wait_for_timeout(3000)
                        log_step("View Shortlisted Leads", "Pass", "Clicked Shortlisted tab")
                        
                        child_divs = page.query_selector_all('.ShortlistedP .ShortList_wrapper')
                        id_values = [div.get_attribute('id') for div in child_divs if div.get_attribute('id')]
                        if id_values:
                            log_step("Get Shortlisted IDs", "Pass", f"Extracted IDs: {', '.join(id_values)}")
                        else:
                            log_step("Get Shortlisted IDs", "Fail", "No IDs found")
                            
                        if offer_id:
                            matched_ids = [id for id in id_values if offer_id in id]
                            if matched_ids:
                                log_step("Match Offer ID", "Pass", f"Matched offer_id in {matched_ids}")
                            else:
                                log_step("Match Offer ID", "Fail", "No match found")
                except Exception as e:
                        log_step("View Shortlisted Leads", "Fail", str(e))
                        continue

                    # Step 10: Deshortlist Lead
                try:
                        page.click("a:has-text('BuyLeads')")
                        page.wait_for_timeout(2000)

                        max_scroll_attempts = 5
                        deshortlisted = False

                        for _ in range(max_scroll_attempts):
                            shortlisted_cards = page.locator("span[id^='removeFav']")

                            count = shortlisted_cards.count()
                            if count > 0:
                                for i in range(count):
                                    deshortlist_control = shortlisted_cards.nth(i)

                                    if deshortlist_control.is_visible():
                                        deshortlist_control.scroll_into_view_if_needed()
                                        page.wait_for_timeout(1000)

                                        deshortlist_control.click()
                                        log_step("Deshortlist Lead", "Pass", "Lead deshortlisted")

                                        # Extract offer_id
                                        offer_id_locator = deshortlist_control.locator(
                                            "xpath=ancestor::div[3]//input[@name='ofrid']"
                                        )
                                        offer_id = offer_id_locator.get_attribute("value")

                                        if offer_id:
                                            log_step("Extract Offer ID", "Pass", f"Extracted offer_id: {offer_id}")
                                        else:
                                            log_step("Extract Offer ID", "Fail", "Failed to extract offer_id")

                                        deshortlisted = True
                                        break

                            if deshortlisted:
                                break

                            # Scroll to load more shortlisted leads
                            page.mouse.wheel(0, 800)
                            page.wait_for_timeout(2000)

                        if not deshortlisted:
                            log_step("Deshortlist Lead", "Fail", "No shortlisted leads found after scrolling.")

                except Exception as e:
                        log_step("Deshortlist Lead", "Fail", str(e))
                        continue


                    #  # Step 14: Return to Recent BuyLeads
                    # try:
                    #     page.locator("div.tabs-header a:has-text('Recent')").click()
                    #     # page.click("text=Recent Leads")
                    #     log_step("Navigate to Recent BuyLeads", "Pass", "Successfully navigated to Recent BuyLeads")
                    # except Exception as e:
                    #     log_step("Navigate to Recent BuyLeads", "Fail", str(e))
                    #     return False

                    # Step 11: Hide and Unhide Lead
                try:
                        hide_button = page.locator("#hidebl1")
                        card = hide_button.locator("xpath=ancestor::div[contains(@class, 'lstNwLft')]")
                        title_element = card.locator(".lstNwLftCnt h2")
                        hide_button.click()
                        log_step("Hide Lead", "Pass", "Lead hidden")
                        page.wait_for_timeout(2000)

                        page.click("a:has-text('More Leads')")
                        log_step("Click More Leads", "Pass", "Clicked More Leads")

                        page.wait_for_selector("div.MrLdsB_tggl:has-text('Hidden Leads')", timeout=5000)
                        page.click("div.MrLdsB_tggl:has-text('Hidden Leads')")
                        log_step("View Hidden Leads", "Pass", "Switched to Hidden Leads")

                        page.wait_for_selector("div.BuyLdC_UnHide", timeout=5000)
                        unhide_btn = page.locator("div.BuyLdC_UnHide span").first
                        unhide_btn.scroll_into_view_if_needed()
                        unhide_btn.click()
                        log_step("Unhide Lead", "Pass", "Lead unhidden")
                except Exception as e:
                        log_step("Hide/Unhide Lead", "Fail", str(e))
                        continue

                    # Step 12: View Enriched Lead
                try:
                        page.click("a:has-text('BuyLeads')")
                        page.wait_for_selector("span[data-info='bl_enrich']", timeout=10000)
                        page.click("span[data-info='bl_enrich']")
                        page.wait_for_timeout(2000)
                        page.click("span.zoomDialogClose")
                        log_step("View Enriched Lead", "Pass", "Viewed and closed image")
                except Exception as e:
                        log_step("View Enriched Lead", "Fail", str(e))
                        continue

                    # Step 13: Contact Buyer
                try:
                        page.wait_for_selector("div.btnCBN[title='Click to view Buyer details']", timeout=10000)
                        page.click("div.btnCBN[title='Click to view Buyer details']")
                        log_step("Contact Buyer", "Pass", "Clicked Contact Buyer")
                        page.wait_for_timeout(2000)
                except Exception as e:
                        log_step("Contact Buyer", "Fail", str(e))
                        continue

                    # Step 14: Purchase Lead (if not already purchased)
                try:
                        is_visible = page.is_visible("div.bl_quote_form")
                        if is_visible:
                            log_step("Purchase Lead", "Pass", "Quote form opened (already purchased)")
                            
                            try:
                                suggestion_card = page.locator("div[id^='sugg_catalog_']").first
                                if suggestion_card.is_visible():
                                    suggestion_card.click()
                                    log_step("Select Suggested Product", "Pass", "Clicked suggested product")
                                else:
                                    log_step("Select Suggested Product", "Fail", "Suggested product not visible")
                            except Exception as e:
                                log_step("Select Suggested Product", "Fail", str(e))

                            try:
                                page.wait_for_selector("#pwa_redirect", timeout=10000)
                                page.click("#pwa_redirect")
                                log_step("View Your Reply", "Pass", "Clicked View Your Reply")
                            except Exception as e:
                                log_step("View Your Reply", "Fail", str(e))

                            try:
                                page.wait_for_selector("#leftnav_dash_link", timeout=10000)
                                page.click("#leftnav_dash_link")
                                log_step("Navigate to LMS", "Pass", "Landed on LMS")
                            except Exception as e:
                                log_step("Navigate to LMS", "Fail", str(e))
                        else:
                            try:
                                page.wait_for_selector("button.buy-btn:has-text('Buy Now')", timeout=10000)
                                button_count = page.locator("button.buy-btn:has-text('Buy Now')").count()
                                for i in range(button_count):
                                    try:
                                        buy_now_buttons = page.locator("button.buy-btn:has-text('Buy Now')")
                                        buy_now_buttons.nth(i).wait_for(state="visible", timeout=5000)
                                        buy_now_buttons.nth(i).click()
                                        page.wait_for_timeout(2000)
                                        log_step("Purchase Lead", "Pass", f"Clicked Buy Now button {i+1}")
                                        break
                                    except Exception as e:
                                        continue
                            except Exception as e:
                                log_step("Purchase Lead", "Fail", str(e))
                except Exception as e:
                        log_step("Purchase Lead Flow", "Fail", str(e))
                        continue

                    # Final navigation check
                try:
                        page.go_back()
                        page.wait_for_load_state("load")
                        page.wait_for_timeout(2000)
                        log_step("Final Navigation", "Pass", "Returned to previous page")
                except Exception as e:
                        log_step("Final Navigation", "Fail", str(e))

                finally:
                    browser.close()
                    print(f"ðŸ Completed automation on {browser_name}")
                    print(f"Results: {browser_results[browser_name]}")

            except Exception as e:
                print(f"âŒ Error in {browser_name}: {e}")
                if 'log_step' in locals():
                    log_step(f"Automation on {browser_name}", "Fail", f"Error: {e}")

    print("\nðŸŽ¯ Final Results:")
    for browser, results in browser_results.items():
        print(f"{browser}: {results['Pass']} Passed, {results['Fail']} Failed")

if __name__ == "__main__":
    main()

