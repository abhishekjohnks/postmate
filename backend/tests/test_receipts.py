from datetime import datetime, timezone
from types import SimpleNamespace

import pypdfium2 as pdfium
import pytest
from app.services.receipts import render_receipt


def sample_receipt(**changes):
    snapshot = {
        "customer_name": "Meera Nair", "customer_code": "CUSTOMER-ID-INTERNAL-ONLY",
        "scheme": "Recurring Deposit", "account_number": "RD1234567890", "cif_id": "CIF7654321",
        "staff_name": "Anil Kumar", "staff_id": "STAFF-ID-INTERNAL-ONLY", "sequence": 7,
        "amount": "2500.00", "payment_date": "2026-10-28", "method": "bank_transfer",
        "reference": "BANK10284567", "due_date": "2026-10-28", "outstanding": "0.00",
        **changes,
    }
    return SimpleNamespace(receipt_number="PM-2B071C5CA12741C0BAC15FE5DAEE3C2A",
                           snapshot=snapshot, created_at=datetime(2026, 10, 28, 8, 30, tzinfo=timezone.utc))


@pytest.mark.parametrize("outstanding,reversed_payment,status", [
    ("0", False, "PAYMENT RECORDED"), ("750", False, "PART PAYMENT"), ("0", True, "REVERSED")])
def test_receipt_removes_internal_ids_and_preserves_payment_details(outstanding, reversed_payment, status):
    receipt = sample_receipt(outstanding=outstanding)
    content = render_receipt(receipt, receipt.created_at if reversed_payment else None)
    with pdfium.PdfDocument(content) as document:
        assert len(document) == 1
        page = document[0]
        text_page = page.get_textpage()
        text = text_page.get_text_bounded()
        metadata = str(document.get_metadata_dict())
        for forbidden in [receipt.receipt_number, receipt.snapshot["customer_code"], receipt.snapshot["staff_id"], "Customer ID", "Staff ID"]:
            assert forbidden not in text + metadata
        for required in ["PostMate", "Meera Nair", "RD1234567890", "INR 2,500.00", "28 Oct 2026", "Anil Kumar", "Bank Transfer", status, "not an official India Post receipt"]:
            assert required in text
        assert "OUTSTANDING FOR THIS INSTALMENT" in text if not reversed_payment else "excluded from current collections" in text
        text_page.close()
        page.close()


def test_receipt_handles_long_values_and_literal_markup():
    receipt = sample_receipt(customer_name="Customer <Family & Co> " * 8, account_number="A" * 100,
                             policy_number="P" * 100, staff_name="Staff Member " * 15,
                             reference="Reference <literal> " * 7, amount="999999999999.99")
    with pdfium.PdfDocument(render_receipt(receipt)) as document:
        text = ""
        for page in document:
            text_page = page.get_textpage()
            text += text_page.get_text_bounded()
            text_page.close()
            page.close()
        assert "<Family & Co>" in text
        assert "INR 9,99,99,99,99,999.99" in text
        assert "TRANSACTION REFERENCE" in text
