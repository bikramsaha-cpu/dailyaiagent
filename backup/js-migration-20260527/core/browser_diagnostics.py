from __future__ import annotations

from typing import Any

from core.settings import DEVTOOLS_ENABLED, DIAGNOSTICS_HTML_LIMIT


def collect_page_diagnostics(
    page,
    *,
    action: str | None = None,
    locator_name: str | None = None,
    intent: str | None = None,
) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {
        "provider": "playwright",
        "action": action,
        "locator_name": locator_name,
        "intent": intent,
    }
    diagnostics.update(_basic_snapshot(page))
    diagnostics["interceptors"] = _detect_interceptors(page)
    diagnostics["candidates"] = _candidate_elements(page)

    if DEVTOOLS_ENABLED:
        devtools = _collect_cdp_snapshot(page)
        if devtools:
            diagnostics["devtools"] = devtools
            diagnostics["provider"] = "playwright+cdp"

    return diagnostics


def _basic_snapshot(page) -> dict[str, Any]:
    try:
        url = page.url
    except Exception:
        url = None

    try:
        title = page.title()
    except Exception:
        title = None

    try:
        page_text = page.locator("body").inner_text(timeout=1500)
        page_text = page_text[:3000] if page_text else None
    except Exception:
        page_text = None

    try:
        html = page.evaluate(
            """limit => {
                const html = document.documentElement ? document.documentElement.outerHTML : '';
                return html.slice(0, limit);
            }""",
            DIAGNOSTICS_HTML_LIMIT,
        )
    except Exception:
        html = None

    return {
        "page_url": url,
        "page_title": title,
        "page_text": page_text,
        "html_snapshot": html,
    }


def _detect_interceptors(page) -> list[dict[str, Any]]:
    try:
        return page.evaluate(
            """
            () => {
                const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                const selectors = [
                    '#cityPopupOverlay',
                    '#t0102_blkwrap',
                    '.blckbg',
                    '.imgDivs',
                    '.modal-backdrop',
                    '.popup',
                    '[class*="overlay"]',
                    '[class*="backdrop"]'
                ];
                const result = [];
                for (const selector of selectors) {
                    for (const el of document.querySelectorAll(selector)) {
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        if (style.display === 'none' || style.visibility === 'hidden' || rect.width === 0 || rect.height === 0) {
                            continue;
                        }
                        result.push({
                            selector,
                            tag: el.tagName.toLowerCase(),
                            id: el.id || '',
                            className: normalize(el.className || ''),
                            text: normalize(el.innerText || '').slice(0, 120),
                            zIndex: style.zIndex || '',
                            pointerEvents: style.pointerEvents || '',
                        });
                    }
                }
                const centerEl = document.elementFromPoint(window.innerWidth / 2, window.innerHeight / 2);
                if (centerEl) {
                    const centerStyle = window.getComputedStyle(centerEl);
                    result.push({
                        selector: 'viewport-center',
                        tag: centerEl.tagName.toLowerCase(),
                        id: centerEl.id || '',
                        className: normalize(centerEl.className || ''),
                        text: normalize(centerEl.innerText || '').slice(0, 120),
                        zIndex: centerStyle.zIndex || '',
                        pointerEvents: centerStyle.pointerEvents || '',
                    });
                }
                return result.slice(0, 20);
            }
            """
        )
    except Exception:
        return []


def _candidate_elements(page) -> list[dict[str, Any]]:
    try:
        return page.evaluate(
            """
            () => {
                const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                const nodes = Array.from(document.querySelectorAll(
                    'button, a, input[type="button"], input[type="submit"], [role="button"], [data-click], [aria-label], [title]'
                ));
                return nodes.slice(0, 40).map((el) => ({
                    tag: el.tagName.toLowerCase(),
                    id: el.id || '',
                    className: normalize(el.className || ''),
                    text: normalize(el.innerText || el.value || el.getAttribute('aria-label') || '').slice(0, 120),
                    role: el.getAttribute('role') || '',
                    dataClick: el.getAttribute('data-click') || '',
                    title: el.getAttribute('title') || '',
                    ariaLabel: el.getAttribute('aria-label') || '',
                }));
            }
            """
        )
    except Exception:
        return []


def _collect_cdp_snapshot(page) -> dict[str, Any] | None:
    try:
        session = page.context.new_cdp_session(page)
    except Exception:
        return None

    snapshot: dict[str, Any] = {}
    try:
        metrics = session.send("Performance.getMetrics")
        snapshot["metrics"] = {
            item["name"]: item["value"]
            for item in metrics.get("metrics", [])[:30]
        }
    except Exception:
        pass

    try:
        frame_tree = session.send("Page.getFrameTree")
        snapshot["frame_tree"] = frame_tree.get("frameTree", {})
    except Exception:
        pass

    try:
        ready_state = session.send(
            "Runtime.evaluate",
            {"expression": "document.readyState", "returnByValue": True},
        )
        snapshot["ready_state"] = ready_state.get("result", {}).get("value")
    except Exception:
        pass

    return snapshot or None
