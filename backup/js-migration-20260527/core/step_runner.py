from __future__ import annotations

import re
import time
from typing import Any, Callable

from core.browser_diagnostics import collect_page_diagnostics
from core.store import ExecutionStore


def is_locator_error(exc: Exception) -> bool:
    message = f"{type(exc).__name__}: {exc}".lower()
    patterns = [
        "locator",
        "wait_for_selector",
        "wait for selector",
        "timeout",
        "strict mode violation",
        "element is not visible",
        "element is not attached",
        "not found",
    ]
    return any(pattern in message for pattern in patterns)


def auto_unblock_page(page) -> list[str]:
    actions: list[str] = []
    candidates = [
        "#cityPopupOverlay span.close-btn",
        "#cityPopupOverlay .close-btn",
        "#cityPopupOverlay button",
        "span.close-btn",
        "button[aria-label='close']",
        "button[title='close']",
        "#closeCityPopup.close-btn26",
        "span#closeCityPopup.close-btn26",
        "[data-testid='close']",
        "[data-click*='close']",
        "#t0102_blkwrap",
        ".blckbg",
        ".imgDivs",
        "#t0102_bewrapper .close-btn",
        "#t0102_bewrapper [aria-label='close']",
        "#t0102_bewrapper button[type='button']",
    ]

    for selector in candidates:
        try:
            loc = page.locator(selector)
            if loc.count() and loc.first.is_visible():
                loc.first.click(timeout=1000)
                actions.append(f"clicked:{selector}")
                time.sleep(0.2)
        except Exception:
            continue

    try:
        page.keyboard.press("Escape")
        actions.append("pressed:Escape")
    except Exception:
        pass

    try:
        page.evaluate(
            """
            () => {
                const ids = ['cityPopupOverlay', 'closeCityPopup'];
                for (const id of ids) {
                    const node = document.getElementById(id);
                    if (node) {
                        node.style.display = 'none';
                        node.style.visibility = 'hidden';
                        node.style.pointerEvents = 'none';
                    }
                }
                const blockers = Array.from(document.querySelectorAll(
                    '#t0102_blkwrap, .blckbg, .imgDivs, .ber-frwrap, .popup, .modal-backdrop, [class*="overlay"], [class*="backdrop"]'
                ));
                for (const node of blockers) {
                    try {
                        node.style.display = 'none';
                        node.style.visibility = 'hidden';
                        node.style.pointerEvents = 'none';
                        node.removeAttribute('style');
                        node.style.pointerEvents = 'none';
                        node.style.opacity = '0';
                    } catch (e) {}
                }
                const buttons = Array.from(document.querySelectorAll('span.close-btn, button[aria-label="close"], button[title="close"]'));
                for (const btn of buttons) {
                    try {
                        btn.click();
                    } catch (e) {}
                }
            }
            """
        )
        actions.append("dom:dismissed")
    except Exception:
        pass

    return actions


def run_step(
    *,
    step_name: str,
    func: Callable[[], Any],
    page,
    browser_name: str,
    run_time: str,
    browser_results: dict[str, dict[str, int]],
    logger,
    mobile_number: str,
    logger_tab_name: str | None = None,
    heal_retry_delay: float = 0.35,
) -> None:
    full_title = f"[{browser_name}] {step_name}"
    page_context = getattr(page, "_context", {})
    test_title = page_context.get("test_file") or readable_test_title(page_context.get("test_name") or full_title)
    unblock_actions: list[str] = []
    try:
        result = func()
    except Exception as exc:
        if is_locator_error(exc):
            unblock_actions = auto_unblock_page(page)
            time.sleep(heal_retry_delay)
            try:
                result = func()
                browser_results[browser_name]["Pass"] += 1
                pass_remarks = result if isinstance(result, str) else ""
                print(f"[Pass-Healed] {step_name}: {exc} | unblock={unblock_actions}")
                if logger:
                    logger.log_status(
                        test_title,
                        "Pass",
                        (
                            f"Healed and retried successfully after: {type(exc).__name__}: {exc} "
                            f"| unblock={', '.join(unblock_actions) if unblock_actions else 'none'}"
                            + (f" | {pass_remarks}" if pass_remarks else "")
                        ),
                        browser_name,
                        mobile_number,
                        run_time,
                        tab_name=logger_tab_name,
                        test_step=step_name,
                    )
                ExecutionStore().record_step_event(
                    suite_name=getattr(page, "_context", {}).get("suite_name"),
                    module_name=getattr(page, "_context", {}).get("module_name"),
                    test_name=getattr(page, "_context", {}).get("test_name"),
                    browser_name=browser_name,
                    step_name=step_name,
                    status="Pass-Healed",
                    remarks=f"Recovered from {type(exc).__name__}: {exc}",
                    run_time=run_time,
                    extra={"unblock_actions": unblock_actions, "healed": True},
                )
                return
            except Exception as healed_exc:
                unblock_actions = auto_unblock_page(page)
                time.sleep(heal_retry_delay)
                try:
                    result = func()
                    browser_results[browser_name]["Pass"] += 1
                    pass_remarks = result if isinstance(result, str) else ""
                    print(f"[Pass-Healed-2] {step_name}: {exc} | unblock={unblock_actions}")
                    if logger:
                        logger.log_status(
                            test_title,
                            "Pass",
                            (
                                f"Healed on second retry after: {type(exc).__name__}: {exc} "
                                f"| unblock={', '.join(unblock_actions) if unblock_actions else 'none'}"
                                + (f" | {pass_remarks}" if pass_remarks else "")
                            ),
                            browser_name,
                            mobile_number,
                            run_time,
                            tab_name=logger_tab_name,
                            test_step=step_name,
                        )
                    ExecutionStore().record_step_event(
                        suite_name=getattr(page, "_context", {}).get("suite_name"),
                        module_name=getattr(page, "_context", {}).get("module_name"),
                        test_name=getattr(page, "_context", {}).get("test_name"),
                        browser_name=browser_name,
                        step_name=step_name,
                        status="Pass-Healed",
                        remarks=f"Recovered on second retry from {type(exc).__name__}: {exc}",
                        run_time=run_time,
                        extra={"unblock_actions": unblock_actions, "healed": True, "second_retry": True},
                    )
                    return
                except Exception as second_exc:
                    exc = second_exc

        browser_results[browser_name]["Fail"] += 1
        error_msg = f"{type(exc).__name__}: {exc}"
        screenshot_name = safe_filename(f"{browser_name}_{step_name}.png")
        diagnostics = {}
        screenshot_note = screenshot_name
        try:
            page.screenshot(path=screenshot_name, full_page=True)
        except Exception as screenshot_exc:
            screenshot_note = f"not captured: {type(screenshot_exc).__name__}: {screenshot_exc}"
        try:
            diagnostics = collect_page_diagnostics(
                page,
                action="step_failure",
                locator_name=step_name,
                intent=step_name,
            )
        except Exception as diagnostics_exc:
            diagnostics = {"collection_error": f"{type(diagnostics_exc).__name__}: {diagnostics_exc}"}
        print(f"[Fail] {step_name}: {error_msg} (Screenshot: {screenshot_note})")
        if logger:
            logger.log_status(
                test_title,
                "Fail",
                error_msg,
                browser_name,
                mobile_number,
                run_time,
                tab_name=logger_tab_name,
                test_step=step_name,
            )
        ExecutionStore().record_step_event(
            suite_name=getattr(page, "_context", {}).get("suite_name"),
            module_name=getattr(page, "_context", {}).get("module_name"),
            test_name=getattr(page, "_context", {}).get("test_name"),
            browser_name=browser_name,
            step_name=step_name,
            status="Fail",
            remarks=error_msg,
            screenshot_path=screenshot_name if screenshot_note == screenshot_name else None,
            run_time=run_time,
            extra={
                "unblock_actions": unblock_actions if is_locator_error(exc) else [],
                "diagnostics": diagnostics,
            },
        )
        raise
    else:
        browser_results[browser_name]["Pass"] += 1
        pass_remarks = result if isinstance(result, str) else ""
        print(f"[Pass] {step_name}")
        if logger:
            logger.log_status(
                test_title,
                "Pass",
                pass_remarks,
                browser_name,
                mobile_number,
                run_time,
                tab_name=logger_tab_name,
                test_step=step_name,
            )
        ExecutionStore().record_step_event(
            suite_name=getattr(page, "_context", {}).get("suite_name"),
            module_name=getattr(page, "_context", {}).get("module_name"),
            test_name=getattr(page, "_context", {}).get("test_name"),
            browser_name=browser_name,
            step_name=step_name,
            status="Pass",
            run_time=run_time,
        )


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value)


def readable_test_title(value: str) -> str:
    title = re.sub(r"^\[[^\]]+\]\s*", "", str(value or "").strip())
    title = re.sub(r"\[[^\]]+\]$", "", title).strip()
    title = re.sub(r"^test[_\s-]+", "", title, flags=re.IGNORECASE)
    title = title.replace("_", " ").replace("-", " ")
    title = re.sub(r"\s+", " ", title).strip()
    return title.title() if title else "Untitled Test"
