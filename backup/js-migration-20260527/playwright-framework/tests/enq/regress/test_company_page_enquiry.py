import pytest

from pages.enq.company_page import CompanyPage
from pages.enq.enquiry_form import EnquiryForm


pytestmark = [pytest.mark.enq, pytest.mark.loggedin, pytest.mark.regression, pytest.mark.module("CompanyPage")]


def test_company_page_enquiry_flow(page, page_context):
    company_page = CompanyPage(page, **page_context)
    enquiry_form = EnquiryForm(page, **page_context)

    company_page.open()
    company_page.click_contact_supplier()
    enquiry_form.complete_company_page_flow()
    enquiry_form.wait_for_thank_you(timeout_ms=3000)
