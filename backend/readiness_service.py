import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.business import BusinessProfile
from app.models.government_scheme import GovernmentScheme
from app.models.scheme_document import SchemeDocument, ApplicationReadiness
from app.models.transaction import Transaction
from app.models.customer import Customer
from app.schemas.government_scheme import (
    ReadinessResponse, 
    ChecklistItem, 
    FinancialSummarySnapshot
)

def compute_financial_summary(db: Session, business_id: int) -> FinancialSummarySnapshot:
    """Calculates financial health metrics directly from merchant's Vyapaar AI records."""
    total_sales = db.query(func.sum(Transaction.amount)).filter(
        Transaction.business_id == business_id,
        Transaction.type.in_(["SALE", "CREDIT_GIVEN"])
    ).scalar() or 0.0

    total_expenses = db.query(func.sum(Transaction.amount)).filter(
        Transaction.business_id == business_id,
        Transaction.type == "EXPENSE"
    ).scalar() or 0.0

    credit_given = db.query(func.sum(Transaction.amount)).filter(
        Transaction.business_id == business_id,
        Transaction.type == "CREDIT_GIVEN"
    ).scalar() or 0.0

    payment_received = db.query(func.sum(Transaction.amount)).filter(
        Transaction.business_id == business_id,
        Transaction.type == "PAYMENT_RECEIVED"
    ).scalar() or 0.0

    outstanding_udhar = db.query(func.sum(Customer.current_balance)).filter(
        Customer.business_id == business_id,
        Customer.current_balance > 0
    ).scalar() or 0.0

    txns_count = db.query(Transaction).filter(Transaction.business_id == business_id).count()

    recovery_pct = 100.0
    if credit_given > 0:
        recovery_pct = min(100.0, (payment_received / credit_given) * 100.0)

    # Monthly runrate estimate based on recorded transactions
    monthly_runrate = total_sales / 6.0 if total_sales > 0 else 0.0
    est_operating_profit = max(0.0, total_sales - total_expenses)

    return FinancialSummarySnapshot(
        total_sales_recorded=float(total_sales),
        monthly_sales_runrate=float(monthly_runrate),
        recorded_transactions_count=txns_count,
        total_udhar_outstanding=float(outstanding_udhar),
        udhar_recovery_percentage=float(round(recovery_pct, 1)),
        estimated_operating_profit=float(est_operating_profit),
        data_freshness_period="Last 6 Months (Real-time Ledger)"
    )

def evaluate_application_readiness(
    db: Session,
    business: BusinessProfile,
    scheme: GovernmentScheme
) -> ReadinessResponse:
    # 1. Financial metrics snapshot
    fin_summary = compute_financial_summary(db, business.id)

    # 2. Existing uploaded documents for this business
    uploaded_docs = db.query(SchemeDocument).filter(
        SchemeDocument.business_id == business.id
    ).all()
    uploaded_types = {d.document_type.upper() for d in uploaded_docs}

    # 3. Compile Checklist
    checklist: List[ChecklistItem] = []
    
    # Requirement: Identity & Aadhaar
    checklist.append(ChecklistItem(
        key="AADHAAR",
        name="Aadhaar Card (Linked with Mobile)",
        is_required=True,
        is_satisfied=bool(business.is_verified or "AADHAAR" in uploaded_types),
        reusable_from_ledger=True,
        source_field="business_profiles.is_verified",
        help_text="Required for Aadhaar e-KYC and Direct Benefit Transfer (DBT)."
    ))

    # Requirement: PAN Card
    checklist.append(ChecklistItem(
        key="PAN",
        name="PAN Card of Proprietor / Enterprise",
        is_required=True,
        is_satisfied=bool(business.pan or "PAN" in uploaded_types),
        reusable_from_ledger=bool(business.pan),
        source_field=f"PAN: {business.pan}" if business.pan else None,
        help_text="Mandatory for income tax verification and commercial bank accounts."
    ))

    # Requirement: Bank Account & IFSC
    checklist.append(ChecklistItem(
        key="BANK_DETAILS",
        name="Bank Passbook / Cancelled Cheque",
        is_required=True,
        is_satisfied=bool(business.bank_account_no and business.bank_ifsc),
        reusable_from_ledger=bool(business.bank_account_no and business.bank_ifsc),
        source_field=f"A/C: {business.bank_account_no} (IFSC: {business.bank_ifsc})" if business.bank_account_no else None,
        help_text="Account where loan amount and interest subsidies will be credited."
    ))

    # Requirement: Udyam Registration (for MSME / MUDRA / CGTMSE)
    if scheme.scheme_category in ["LOAN", "CREDIT_GUARANTEE", "PROCUREMENT", "SUBSIDY"]:
        checklist.append(ChecklistItem(
            key="UDYAM",
            name="Udyam Registration Certificate",
            is_required=(scheme.scheme_category != "VENDOR_SUPPORT"),
            is_satisfied=bool(business.udyam_registration_no or "UDYAM" in uploaded_types),
            reusable_from_ledger=bool(business.udyam_registration_no),
            source_field=f"Udyam No: {business.udyam_registration_no}" if business.udyam_registration_no else None,
            help_text="Official MSME certificate from udyamregistration.gov.in (free of charge)."
        ))

    # Scheme-Specific Requirements:
    if scheme.scheme_category == "VENDOR_SUPPORT":
        checklist.append(ChecklistItem(
            key="COV_OR_LOR",
            name="Certificate of Vending (CoV) or ULB Recommendation Letter",
            is_required=True,
            is_satisfied=("COV" in uploaded_types or "LOR" in uploaded_types),
            reusable_from_ledger=False,
            help_text="Issued by Municipal Corporation / Town Vending Committee (TVC)."
        ))

    if scheme.scheme_category == "ARTISAN_SUPPORT":
        checklist.append(ChecklistItem(
            key="ARTISAN_TRADE",
            name="Gram Panchayat / ULB Trade Verification (18 Traditional Trades)",
            is_required=True,
            is_satisfied=bool(business.business_category == "artisan_handicrafts" or "ARTISAN" in uploaded_types),
            reusable_from_ledger=True,
            source_field=f"Category: {business.business_category}",
            help_text="Confirms you practice one of the 18 eligible traditional artisanal crafts."
        ))

    if scheme.scheme_category == "FARMER_SUPPORT":
        checklist.append(ChecklistItem(
            key="LAND_RECORDS",
            name="Land Ownership Record (Khatauni / Khasra)",
            is_required=True,
            is_satisfied=("LAND_RECORD" in uploaded_types),
            reusable_from_ledger=False,
            help_text="Required for cultivating landholding verification by Department of Agriculture."
        ))

    # Financial Summary Dossier Checklist Item
    has_sales_history = fin_summary.total_sales_recorded > 0 or fin_summary.recorded_transactions_count >= 5
    checklist.append(ChecklistItem(
        key="FINANCIAL_DOSSIER",
        name="Vyapaar AI Certified Financial Summary Sheet",
        is_required=True,
        is_satisfied=has_sales_history,
        reusable_from_ledger=True,
        source_field=f"₹{fin_summary.total_sales_recorded:,.0f} recorded across {fin_summary.recorded_transactions_count} entries",
        help_text="Generated automatically from your digital khata ledger and invoices."
    ))

    # Calculate overall readiness percentage
    satisfied_count = sum(1 for item in checklist if item.is_satisfied)
    total_count = len(checklist)
    readiness_pct = (satisfied_count / total_count) * 100.0 if total_count > 0 else 0.0

    # Step-by-step instructions
    steps = [
        f"Step 1: Verify your basic merchant details (PAN: {business.pan or 'Pending'}, Bank IFSC: {business.bank_ifsc or 'Pending'}).",
        "Step 2: Download your Vyapaar AI Financial Summary Sheet showing your recorded sales and customer ledger health.",
        f"Step 3: Access the official government portal: {scheme.application_portal_url or scheme.official_portal_url}.",
        "Step 4: Log in using your Aadhaar-linked mobile number and enter your enterprise details.",
        "Step 5: Attach your identity proof and bank details. If applying via Jan Samarth or Bank, present your Vyapaar AI Financial Summary.",
        "Step 6: Receive your official Application Tracking Reference Number and save it in Vyapaar AI for status updates."
    ]

    # Save readiness record
    readiness_rec = db.query(ApplicationReadiness).filter(
        ApplicationReadiness.business_id == business.id,
        ApplicationReadiness.scheme_id == scheme.id
    ).first()

    app_status = "READY_TO_APPLY" if readiness_pct >= 80.0 else "IN_PREPARATION"
    portal_ref = None

    if not readiness_rec:
        readiness_rec = ApplicationReadiness(
            business_id=business.id,
            scheme_id=scheme.id,
            readiness_percentage=readiness_pct,
            checklist_state=json.dumps([item.model_dump() for item in checklist]),
            financial_summary_snapshot=json.dumps(fin_summary.model_dump()),
            application_status=app_status,
            updated_at=datetime.now(timezone.utc)
        )
        db.add(readiness_rec)
    else:
        readiness_rec.readiness_percentage = readiness_pct
        readiness_rec.checklist_state = json.dumps([item.model_dump() for item in checklist])
        readiness_rec.financial_summary_snapshot = json.dumps(fin_summary.model_dump())
        if readiness_rec.application_status == "NOT_STARTED":
            readiness_rec.application_status = app_status
        portal_ref = readiness_rec.portal_reference_number

    db.commit()

    return ReadinessResponse(
        scheme_id=scheme.id,
        scheme_name=scheme.name,
        scheme_code=scheme.scheme_code,
        readiness_percentage=round(readiness_pct, 1),
        checklist=checklist,
        financial_summary=fin_summary,
        application_status=readiness_rec.application_status if readiness_rec else app_status,
        portal_reference_number=portal_ref,
        official_application_url=scheme.application_portal_url or scheme.official_portal_url,
        step_by_step_instructions=steps
    )
