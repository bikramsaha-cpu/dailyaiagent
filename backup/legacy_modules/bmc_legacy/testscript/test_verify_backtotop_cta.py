from datetime import datetime
import os
import sys
import time

from playwright.sync_api import sync_playwright

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from logger_instance import logger
from shared import DEFAULT_BMC_LOGIN_PHONE, SESSION_FILE_PATH, launch_browser
from shared import build_page, empty_browser_results, make_log_step, open_message_centre

BROWSERS = ["chromium", "firefox"]
MOBILE_NUMBER = DEFAULT_BMC_LOGIN_PHONE
test_case_name = os.path.basename(__file__).replace(".py", "")

browser_results = empty_browser_results()
SCROLL_CONTAINER_SELECTOR = "#messages_scrolling_div"
BACK_TO_TOP_SELECTOR = "#scrollArrow"


def get_scroll_metrics(page):
    return page.evaluate(
        """
        (rootSelector) => {
            const root = document.querySelector(rootSelector);
            if (!root) {
                throw new Error("Scrollable message root was not found.");
            }

            const candidates = [root, ...root.querySelectorAll("*")];
            const scrollable = candidates.find((node) => {
                const element = node;
                const style = window.getComputedStyle(element);
                const canScroll =
                    (style.overflowY === "auto" || style.overflowY === "scroll" || style.overflowY === "overlay") &&
                    element.scrollHeight > element.clientHeight + 20;
                return canScroll;
            });

            if (!scrollable) {
                return {
                    found: false,
                    scrollTop: 0,
                    scrollHeight: root.scrollHeight || 0,
                    clientHeight: root.clientHeight || 0,
                    tagName: root.tagName || "unknown",
                    id: root.id || "",
                    className: root.className || "",
                };
            }

            return {
                found: true,
                scrollTop: scrollable.scrollTop,
                scrollHeight: scrollable.scrollHeight,
                clientHeight: scrollable.clientHeight,
                tagName: scrollable.tagName || "unknown",
                id: scrollable.id || "",
                className: scrollable.className || "",
            };
        }
        """,
        SCROLL_CONTAINER_SELECTOR,
    )


def scroll_message_list(page):
    return page.evaluate(
        """
        (rootSelector) => {
            const root = document.querySelector(rootSelector);
            if (!root) {
                throw new Error("Scrollable message root was not found.");
            }

            const candidates = [root, ...root.querySelectorAll("*")];
            const scrollable = candidates.find((node) => {
                const element = node;
                const style = window.getComputedStyle(element);
                return (
                    (style.overflowY === "auto" || style.overflowY === "scroll" || style.overflowY === "overlay") &&
                    element.scrollHeight > element.clientHeight + 20
                );
            });

            if (!scrollable) {
                throw new Error("No scrollable descendant was found inside the message panel.");
            }

            scrollable.scrollTop = Math.max(scrollable.scrollHeight, 1500);
            return {
                scrollTop: scrollable.scrollTop,
                scrollHeight: scrollable.scrollHeight,
                clientHeight: scrollable.clientHeight,
                tagName: scrollable.tagName || "unknown",
                id: scrollable.id || "",
                className: scrollable.className || "",
            };
        }
        """,
        SCROLL_CONTAINER_SELECTOR,
    )


def run(playwright):
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for browser_name in BROWSERS:
        print(f"\nRunning go to top automation on: {browser_name}")
        browser = launch_browser(playwright, browser_name)
        context = browser.new_context(storage_state=SESSION_FILE_PATH)
        page = build_page(context.new_page(), test_name=test_case_name)
        base_log_step = make_log_step(
            page=page,
            browser_name=browser_name,
            run_time=run_time,
            browser_results=browser_results,
            logger=logger,
            mobile_number=MOBILE_NUMBER,
        )

        def log_step(step_name, func):
            return base_log_step(f"{test_case_name} -> {step_name}", func)

        log_step("Open Message Centre", lambda: open_message_centre(page))

        scroll_metrics = {"before": 0, "after_scroll": 0, "after_click": 0}
        scroll_target = {"label": "unknown"}

        def scroll_contact_list():
            page.wait_for_selector(SCROLL_CONTAINER_SELECTOR, timeout=15000)
            before = get_scroll_metrics(page)
            scroll_metrics["before"] = int(before["scrollTop"])
            scroll_result = scroll_message_list(page)
            time.sleep(2)
            after = get_scroll_metrics(page)
            scroll_metrics["after_scroll"] = int(after["scrollTop"])
            scroll_target["label"] = (
                f"{scroll_result['tagName']}#{scroll_result['id']}.{scroll_result['className']}".strip(".")
            )
            if scroll_metrics["after_scroll"] <= scroll_metrics["before"]:
                raise AssertionError(
                    "Scrollable container did not move down. "
                    f"Before={scroll_metrics['before']}, after scroll={scroll_metrics['after_scroll']}, "
                    f"target={scroll_target['label']}, scrollHeight={after['scrollHeight']}, clientHeight={after['clientHeight']}."
                )

        log_step("Scroll Contact List", scroll_contact_list)

        def click_go_to_top_button():
            page.wait_for_selector(BACK_TO_TOP_SELECTOR, timeout=10000)
            button = page.locator(BACK_TO_TOP_SELECTOR).first
            if not button.is_visible():
                raise AssertionError("Back to top CTA is present in DOM but not visible.")
            button.click(force=True)
            time.sleep(2)
            after_click = get_scroll_metrics(page)
            scroll_metrics["after_click"] = int(after_click["scrollTop"])
            if scroll_metrics["after_click"] > 20:
                raise AssertionError(
                    "Back to top CTA was clicked but the message list did not return to the top. "
                    f"ScrollTop after click={scroll_metrics['after_click']}, target={scroll_target['label']}."
                )

        log_step("Click Back To Top CTA", click_go_to_top_button)

        def verify_back_to_top_result():
            if scroll_metrics["after_scroll"] <= 0:
                raise AssertionError("Precondition failed: the message list never scrolled down before CTA verification.")
            if scroll_metrics["after_click"] > 20:
                raise AssertionError(
                    "Back to top verification failed because the list remained scrolled. "
                    f"After scroll={scroll_metrics['after_scroll']}, after click={scroll_metrics['after_click']}."
                )
            print(
                "Back to top CTA returned the message list to the top successfully. "
                f"After scroll={scroll_metrics['after_scroll']}, after click={scroll_metrics['after_click']}, target={scroll_target['label']}."
            )

        log_step("Verify Back To Top CTA Returns List To Top", verify_back_to_top_result)

        context.close()
        browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)

