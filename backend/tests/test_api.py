import re
import uuid

from fastapi.testclient import TestClient

from app import main


def test_health_and_protected_routes():
    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/auth/me").status_code == 401
        assert client.post("/api/v1/voice/parse", json={"transcript": "Ramesh ko 500 rupaye udhar"}).status_code == 401


def test_email_registration_verification_login_and_ledger(monkeypatch):
    sent = []
    monkeypatch.setattr(main, "send_email", lambda to, subject, body: sent.append((to, subject, body)))
    email = f"merchant-{uuid.uuid4().hex[:12]}@example.com"

    with TestClient(main.app) as client:
        response = client.post("/api/v1/auth/register", json={
            "full_name": "Test Merchant",
            "email": email,
            "password": "correct-horse-battery-42",
            "merchant_type": "Street Vendor",
            "business_name": "Test Cart",
            "business_category": "street_vendor",
            "state": "Delhi",
            "preferred_language": "hi",
            "accepted_terms": True
        })
        assert response.status_code == 202, response.text
        otp = re.search(r"\b(\d{6})\b", sent[-1][2]).group(1)

        blocked = client.post("/api/v1/auth/login", json={"email": email, "password": "correct-horse-battery-42"})
        assert blocked.status_code == 403

        verified = client.post("/api/v1/auth/verify-email", json={"email": email, "otp": otp})
        assert verified.status_code == 200

        login = client.post("/api/v1/auth/login", json={"email": email, "password": "correct-horse-battery-42"})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        profile = client.get("/api/v1/auth/me", headers=headers)
        assert profile.status_code == 200
        assert profile.json()["business_name"] == "Test Cart"

        parsed = client.post("/api/v1/voice/parse", headers=headers, json={"transcript": "Ramesh ko 500 rupaye udhar diya"})
        assert parsed.status_code == 200
        draft = parsed.json()
        assert draft["transaction_type"] == "CREDIT_GIVEN"
        assert draft["amount"] == "500"

        saved = client.post("/api/v1/voice/confirm", headers=headers, json={
            "kind": "CREDIT_GIVEN", "amount": "500", "customer_name": "Ramesh", "notes": "Voice test"
        })
        assert saved.status_code == 200, saved.text

        summary = client.get("/api/v1/dashboard/summary", headers=headers)
        assert summary.status_code == 200
        assert summary.json()["total_outstanding_udhar"] == 500.0
        customers = client.get("/api/v1/customers", headers=headers)
        assert customers.status_code == 200
        assert any(x["name"] == "Ramesh" for x in customers.json()["items"])
        export = client.get("/api/v1/auth/me/export", headers=headers)
        assert export.status_code == 200
        assert export.json()["account"]["email"] == email

        invoice = client.post("/api/v1/invoices", headers=headers, json={
            "customer_name": "Sita", "item_description": "Rice 5 kg", "total": "250.00", "payment_status": "udhar"
        })
        assert invoice.status_code == 200, invoice.text
        listed = client.get("/api/v1/invoices", headers=headers)
        assert listed.status_code == 200
        assert any(x["invoice_number"] == invoice.json()["invoice_number"] for x in listed.json()["items"])


def test_scheme_catalogue_uses_official_https_links():
    with TestClient(main.app) as client:
        response = client.get("/api/v1/government-schemes")
        assert response.status_code == 200
        items = response.json()["items"]
        assert items
        assert all(item["official_portal_url"].startswith("https://") for item in items)
