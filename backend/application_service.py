import os
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException
from app.models.government_scheme import GovernmentScheme
from app.models.scheme_document import SchemeDocument, ApplicationReadiness
from app.schemas.government_scheme import ApplicationGuideResponse, SchemeDocumentResponse
from app.core.config import settings

def get_application_guide(scheme: GovernmentScheme) -> ApplicationGuideResponse:
    submission_mode = "ONLINE_PORTAL"
    fees = "₹0 (Completely Free Government Service)"
    prerequisites = [
        "Aadhaar card with linked mobile phone for OTP verification",
        "Bank account in the name of the applicant/enterprise",
        "Business address proof (Electricity bill, shop lease, or local trade licence)"
    ]

    steps = [
        {"step": "1", "title": "Registration on Sovereign Portal", "description": f"Navigate to {scheme.official_portal_url} and sign up using your Aadhaar-linked mobile number."},
        {"step": "2", "title": "Profile & Enterprise Entry", "description": "Fill in the basic enterprise details, trade type, and bank account information."},
        {"step": "3", "title": "Document Upload / DigiLocker Fetch", "description": "Upload scanned copies of required documents or authorize DigiLocker for instant zero-paperwork verification."},
        {"step": "4", "title": "Lending Institution / Branch Selection", "description": "Select your preferred bank branch or nearest Common Service Centre (CSC) for physical verification."},
        {"step": "5", "title": "Submission & Reference Generation", "description": "Submit application and retain the 14-digit or alphanumeric Reference Number."}
    ]

    helpline = [
        {"name": "National MSME Champions Toll-Free", "contact": "1800-180-6763"},
        {"name": "National Jan Samarth Helpdesk", "contact": "support@jansamarth.in"},
        {"name": "PM SVANidhi Support", "contact": "1800-111-979"}
    ]

    disclaimers = [
        "Vyapaar AI never charges any fee for government scheme access or eligibility checks.",
        "Beware of fraudulent agents or fake websites requesting advance fee deposits.",
        "Only submit sensitive documents and OTPs on domains ending with .gov.in or .nic.in."
    ]

    return ApplicationGuideResponse(
        scheme_name=scheme.name,
        ministry=scheme.ministry,
        official_portal_url=scheme.official_portal_url,
        application_portal_url=scheme.application_portal_url or scheme.official_portal_url,
        submission_mode=submission_mode,
        fees=fees,
        prerequisites=prerequisites,
        step_by_step_steps=steps,
        disclaimers=disclaimers,
        helpline_contacts=helpline
    )

def save_scheme_document(
    db: Session,
    business_id: int,
    scheme_id: Optional[int],
    document_type: str,
    file_bytes: bytes,
    filename: str
) -> SchemeDocumentResponse:
    # 1. Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # 2. Compute SHA-256 hash for integrity and deduplication
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    file_size = len(file_bytes)

    # 3. Save securely to disk with sanitized filename
    safe_name = f"biz_{business_id}_{document_type.lower()}_{file_hash[:8]}.dat"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # 4. Check if document of this type already exists for this business
    existing_doc = db.query(SchemeDocument).filter(
        SchemeDocument.business_id == business_id,
        SchemeDocument.document_type == document_type.upper()
    ).first()

    if existing_doc:
        existing_doc.file_name = filename
        existing_doc.file_path = file_path
        existing_doc.file_size = file_size
        existing_doc.file_hash = file_hash
        existing_doc.scheme_id = scheme_id or existing_doc.scheme_id
        existing_doc.verification_status = "UPLOADED"
        existing_doc.uploaded_at = datetime.now(timezone.utc)
        doc = existing_doc
    else:
        doc = SchemeDocument(
            business_id=business_id,
            scheme_id=scheme_id,
            document_type=document_type.upper(),
            file_name=filename,
            file_path=file_path,
            file_size=file_size,
            file_hash=file_hash,
            verification_status="UPLOADED",
            uploaded_at=datetime.now(timezone.utc)
        )
        db.add(doc)

    db.commit()
    db.refresh(doc)
    return SchemeDocumentResponse.model_validate(doc)

def update_merchant_application_consent(
    db: Session,
    business_id: int,
    scheme_id: int,
    consent_given: bool,
    portal_reference_number: Optional[str] = None
) -> ApplicationReadiness:
    readiness = db.query(ApplicationReadiness).filter(
        ApplicationReadiness.business_id == business_id,
        ApplicationReadiness.scheme_id == scheme_id
    ).first()

    if not readiness:
        readiness = ApplicationReadiness(
            business_id=business_id,
            scheme_id=scheme_id,
            merchant_consent_given=consent_given,
            consent_timestamp=datetime.now(timezone.utc) if consent_given else None,
            portal_reference_number=portal_reference_number,
            application_status="APPLIED_ON_PORTAL" if portal_reference_number else "READY_TO_APPLY"
        )
        db.add(readiness)
    else:
        readiness.merchant_consent_given = consent_given
        if consent_given:
            readiness.consent_timestamp = datetime.now(timezone.utc)
        if portal_reference_number:
            readiness.portal_reference_number = portal_reference_number
            readiness.application_status = "APPLIED_ON_PORTAL"

    db.commit()
    db.refresh(readiness)
    return readiness
