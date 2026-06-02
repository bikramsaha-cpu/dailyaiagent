def after_each(page) -> None:
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
