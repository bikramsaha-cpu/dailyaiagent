import pytest

from pages.enq.enquiry_form import EnquiryForm
from pages.enq.pdp_page import PdpPage


pytestmark = [pytest.mark.enq, pytest.mark.loggedin, pytest.mark.smoke, pytest.mark.module("PDP")]


def test_pdp_enquiry_flow(page, page_context):
    pdp_page = PdpPage(page, **page_context)
    enquiry_form = EnquiryForm(page, **page_context)

    pdp_page.open()
    pdp_page.click_contact_supplier()
    enquiry_form.complete_pdp_flow()
    enquiry_form.wait_for_thank_you()
