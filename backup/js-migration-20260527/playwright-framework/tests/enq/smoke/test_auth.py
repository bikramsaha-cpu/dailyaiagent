import pytest

from pages.login_page import LoginPage


pytestmark = [pytest.mark.enq, pytest.mark.auth]


def test_enq_login_session_can_be_saved(page, page_context):
    LoginPage(page, **page_context).login_and_save_session()
