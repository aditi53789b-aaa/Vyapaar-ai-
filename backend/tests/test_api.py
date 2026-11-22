import re
import uuid

from fastapi.testclient import TestClient

from app import main


def test_health_and_protected_routes():
    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/auth/me").status_code == 401
        assert client.post("/api/v1/voice/parse", json={"transcript": "Ramesh ko 500 rupaye udhar"}).status_code == 401


def test_password_registration_login_and_ledger(monkeypatch):
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
        assert response.status_code == 201, response.text
        assert response.json()["email"] == email
        assert sent == []

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
        assert draft["customer_name"] == "Ramesh"

        # Hindi number words and Devanagari digits should both be understood.
        spoken_words = client.post("/api/v1/voice/parse", headers=headers, json={"transcript": "Ramesh ko paanch sau rupaye udhar diya"})
        assert spoken_words.status_code == 200, spoken_words.text
        assert spoken_words.json()["amount"] == "500"
        devanagari = client.post("/api/v1/voice/parse", headers=headers, json={"transcript": "सीता को ५०० रुपये उधार"})
        assert devanagari.status_code == 200, devanagari.text
        assert devanagari.json()["amount"] == "500"
        assert devanagari.json()["transaction_type"] == "CREDIT_GIVEN"

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

        # Password reset revokes the previously issued bearer token.
        monkeypatch.setenv("PASSWORD_RESET_URL", "https://example.test/auth.html?mode=reset")
        forgot = client.post("/api/v1/auth/forgot-password", json={"email": email})
        assert forgot.status_code == 200
        reset_token = re.search(r"token=([A-Za-z0-9_-]+)", sent[-1][2]).group(1)
        reset = client.post("/api/v1/auth/reset-password", json={"token": reset_token, "new_password": "another-strong-password-55"})
        assert reset.status_code == 200
        assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
        new_login = client.post("/api/v1/auth/login", json={"email": email, "password": "another-strong-password-55"})
        assert new_login.status_code == 200
        new_headers = {"Authorization": f"Bearer {new_login.json()['access_token']}"}
        deleted = client.request("DELETE", "/api/v1/auth/me", headers=new_headers, json={"password": "another-strong-password-55"})
        assert deleted.status_code == 204
        assert client.get("/api/v1/auth/me", headers=new_headers).status_code == 401


def test_scheme_catalogue_uses_official_https_links():
    with TestClient(main.app) as client:
        response = client.get("/api/v1/government-schemes")
        assert response.status_code == 200
        items = response.json()["items"]
        assert items
        assert all(item["official_portal_url"].startswith("https://") for item in items)
