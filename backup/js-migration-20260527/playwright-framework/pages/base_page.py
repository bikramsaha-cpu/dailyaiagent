from __future__ import annotations

from typing import Any, Callable

from core.step_runner import run_step


class BasePage:
    def __init__(
        self,
        page,
        *,
        browser_name: str,
        run_time: str,
        browser_results,
        logger,
        mobile_number: str,
    ):
        self.page = page
        self.browser_name = browser_name
        self.run_time = run_time
        self.browser_results = browser_results
        self.logger = logger
        self.mobile_number = mobile_number

    def step(self, name: str, action: Callable[[], Any]) -> None:
        run_step(
            step_name=name,
            func=action,
            page=self.page,
            browser_name=self.browser_name,
            run_time=self.run_time,
            browser_results=self.browser_results,
            logger=self.logger,
            mobile_number=self.mobile_number,
        )

    def goto(self, url: str, *, timeout: int = 60000) -> None:
        self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)

    def dismiss_common_blockers(self) -> None:
        try:
            self.page.keyboard.press("Escape")
        except Exception:
            pass
