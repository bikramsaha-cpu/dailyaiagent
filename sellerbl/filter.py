from playwright.sync_api import sync_playwright, TimeoutError
import re

def login(page):
    # Step 1: Login to Seller Dashboard
    page.goto("https://seller.indiamart.com/")
    page.fill("#mobNo", "1435463454")
    page.click("button:has-text('Start Selling')")
    page.wait_for_selector("#passwordbtn1", timeout=5000)
    page.click("#passwordbtn1")
    page.fill("input[type='password']", "desktoplms123")
    page.click("#signWP")
    page.wait_for_timeout(3000)
    print("✅ Step 1: Login successful")



def select_location_by_id(page, location_2):
    selector = "label.rdo_btn:has-text('India')"
    try:
        page.wait_for_selector(selector, timeout=5000)
        page.click(selector)
        print(f"✅ Selected order filter with id: {location_2}")
    except Exception as e:
        print(f"❌ Failed to select order filter {location_2}: {e}")

def select_category_by_id(page):
    selector = "#top_filter_catdiv label.chekbx_fltr"
    try:
        page.wait_for_selector(selector, timeout=5000)
        page.locator(selector).first.click()
        print("✅ Selected first category filter")
    except Exception as e:
        print(f"❌ Failed to select first category filter: {e}")

def select_order_by_id(page, order_id):
    selector = 'label.rdo_btn:has(input#order_id_400)'
    try:
        page.wait_for_selector(selector, timeout=5000)
        page.click(selector)
        print(f"✅ Selected order filter with id: {order_id}")
    except Exception as e:
        print(f"❌ Failed to select order filter {order_id}: {e}")

def select_Lead_by_id(page, Lead_id):
    selector = 'label.chekbx_fltr:has(input#lead_type_2)'
    try:
        page.wait_for_selector(selector, timeout=5000)
        page.click(selector)
        print(f"✅ Selected order filter with id: {Lead_id}")
    except Exception as e:
        print(f"❌ Failed to select order filter {Lead_id}: {e}")




# Step 5 onward: Main Automation Flow
def run(selected_option, selected_order_value, lead_type_option):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="chrome")
        context = browser.new_context(viewport={"width": 1366, "height": 768})
        page = context.new_page()

        # Step 1: Login
        login(page)

        # Step 5: Go to BuyLeads
        page.wait_for_selector("a:has-text('BuyLeads')", timeout=10000)
        page.click("a:has-text('BuyLeads')")
        print("✅ Step 5: Navigated to BuyLeads")
        page.wait_for_timeout(5000)


        # Step 6: Location Filter
        page.hover("span.word_elip:text('Location')")  # Open the dropdown first
        page.wait_for_timeout(3000)
        select_location_by_id(page, "location_2")  
        page.wait_for_timeout(3000)

        # Step 6: Category Filter
        page.hover("span.word_elip:text('Categories/Products')")  # Open the dropdown first
        page.wait_for_timeout(3000)
        select_category_by_id(page)  
        #page.wait_for_timeout(5000)

        # Step 6: Order Filter
        #page.hover("span.word_elip:text('Order Value (₹)')")  # Open the dropdown first
        #page.wait_for_timeout(5000)
        #select_order_by_id(page, "order_id")  
        #page.wait_for_timeout(5000)

        # Step 6: Lead  Filter
        page.hover("span.word_elip:text('Lead Type')")  # Open the dropdown first
        page.wait_for_timeout(5000)
        select_order_by_id(page, "Lead_id")  
        #page.wait_for_timeout(5000)

       



        
        browser.close()

# Run the script
try:
    run('India', 'Above 1 Lakh', 'GST')
except Exception as e:
    print(f"🔥 Unhandled Error: {e}")