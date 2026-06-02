import pytest

from test_data.config import ENQ_ALL_INDIA_SEARCH_TERM
from pages.enq.enquiry_form import EnquiryForm
from pages.enq.search_page import SearchPage


pytestmark = [pytest.mark.enq, pytest.mark.loggedin, pytest.mark.regression, pytest.mark.module("Search")]


def test_search_all_india_enquiry_flow(page, page_context):
    search_page = SearchPage(page, **page_context)
    enquiry_form = EnquiryForm(page, **page_context)

    search_page.open()
    search_page.search_for(ENQ_ALL_INDIA_SEARCH_TERM)
    search_page.select_all_india()
    search_page.click_first_contact_supplier()
    enquiry_form.complete_search_all_india_flow()
