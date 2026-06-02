import pytest

from pages.enq.dir_page import DirPage
from pages.enq.enquiry_form import EnquiryForm


pytestmark = [pytest.mark.enq, pytest.mark.loggedin, pytest.mark.smoke, pytest.mark.module("DIR")]


def test_dir_impcat_enquiry_flow(page, page_context):
    dir_page = DirPage(page, **page_context)
    enquiry_form = EnquiryForm(page, **page_context)

    dir_page.open_impcat()
    dir_page.click_contact_supplier()
    enquiry_form.complete_dir_flow()
    enquiry_form.wait_for_thank_you()
