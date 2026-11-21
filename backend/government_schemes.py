from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from app.core.database import get_db
from app.models.user import User
from app.models.business import BusinessProfile
from app.services.auth_service import get_current_user, get_current_business
from app.services.government.scheme_discovery import discover_schemes, get_scheme_by_id
from app.services.government.source_registry import get_all_sources
from app.services.government.sync_service import sync_government_schemes
from app.services.government.eligibility_engine import assess_scheme_eligibility, get_recommended_schemes_for_business
from app.services.government.readiness_service import evaluate_application_readiness
from app.services.government.application_service import (
    get_application_guide, 
    save_scheme_document, 
    update_merchant_application_consent
)
from app.services.government.rag_service import ask_government_assistant
from app.schemas.government_scheme import (
    SchemeListResponse,
    GovernmentSchemeResponse,
    GovernmentSourceResponse,
    SchemeAssessmentResponse,
    ReadinessResponse,
    ApplicationGuideResponse,
    SchemeDocumentResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    UpdateReadinessConsentRequest
)

router = APIRouter(prefix="/government-schemes", tags=["Government Schemes & Programmes"])

@router.get("", response_model=SchemeListResponse, summary="Discover all verified government schemes")
def get_schemes(
    query: Optional[str] = Query(None, description="Search keyword in English or Hindi"),
    category: Optional[str] = Query(None, description="Scheme category"),
    administering_level: Optional[str] = Query(None, description="CENTRAL or STATE"),
    state: Optional[str] = Query(None, description="Target state"),
    collateral_free_only: bool = Query(False, description="Filter for 0-collateral schemes only"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    return discover_schemes(
        db=db,
        query=query,
        category=category,
        administering_level=administering_level,
        state=state,
        collateral_free_only=collateral_free_only,
        skip=skip,
        limit=limit
    )

@router.get("/categories", response_model=List[str], summary="List available scheme categories")
def get_categories(db: Session = Depends(get_db)):
    res = discover_schemes(db=db, limit=1)
    return res.categories

@router.get("/sources", response_model=List[GovernmentSourceResponse], summary="List verified government source registry")
def get_sources(db: Session = Depends(get_db)):
    sources = get_all_sources(db)
    return [GovernmentSourceResponse.model_validate(s) for s in sources]

@router.get("/recommendations", response_model=List[SchemeAssessmentResponse], summary="Get personalized scheme recommendations for active merchant")
def get_recommendations(
    limit: int = Query(6, ge=1, le=20),
    current_business: BusinessProfile = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    return get_recommended_schemes_for_business(db, current_business, limit=limit)

@router.get("/{scheme_id}", response_model=GovernmentSchemeResponse, summary="Get full scheme details by ID")
def get_scheme_details(scheme_id: int, db: Session = Depends(get_db)):
    scheme = get_scheme_by_id(db, scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="Government scheme not found")
    return GovernmentSchemeResponse.model_validate(scheme)

@router.post("/{scheme_id}/assess", response_model=SchemeAssessmentResponse, summary="Perform personalized eligibility assessment for scheme")
def assess_scheme(
    scheme_id: int,
    current_business: BusinessProfile = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    scheme = get_scheme_by_id(db, scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="Government scheme not found")
    return assess_scheme_eligibility(db, current_business, scheme)

@router.get("/{scheme_id}/readiness", response_model=ReadinessResponse, summary="Check application readiness and generated financial summary")
def check_readiness(
    scheme_id: int,
    current_business: BusinessProfile = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    scheme = get_scheme_by_id(db, scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="Government scheme not found")
    return evaluate_application_readiness(db, current_business, scheme)

@router.get("/{scheme_id}/application-guide", response_model=ApplicationGuideResponse, summary="Get official application instructions and helpline")
def get_guide(scheme_id: int, db: Session = Depends(get_db)):
    scheme = get_scheme_by_id(db, scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="Government scheme not found")
    return get_application_guide(scheme)

@router.post("/{scheme_id}/documents", response_model=SchemeDocumentResponse, summary="Securely upload required document for scheme")
async def upload_document(
    scheme_id: int,
    document_type: str = Form(..., description="AADHAAR, PAN, UDYAM, BANK_PASSBOOK, COV, LAND_RECORD"),
    file: UploadFile = File(...),
    current_business: BusinessProfile = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    content = await file.read()
    if len(content) > 10 * 1024 * 1024: # 10MB limit
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed 10MB limit")
        
    return save_scheme_document(
        db=db,
        business_id=current_business.id,
        scheme_id=scheme_id,
        document_type=document_type,
        file_bytes=content,
        filename=file.filename or f"{document_type.lower()}.pdf"
    )

@router.post("/{scheme_id}/consent", summary="Record merchant explicit consent and tracking reference")
def update_consent(
    scheme_id: int,
    payload: UpdateReadinessConsentRequest,
    current_business: BusinessProfile = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    res = update_merchant_application_consent(
        db=db,
        business_id=current_business.id,
        scheme_id=scheme_id,
        consent_given=payload.consent_given,
        portal_reference_number=payload.portal_reference_number
    )
    return {
        "status": "UPDATED",
        "scheme_id": scheme_id,
        "consent_given": res.merchant_consent_given,
        "application_status": res.application_status,
        "portal_reference_number": res.portal_reference_number
    }

@router.post("/assistant/ask", response_model=RAGQueryResponse, summary="Query multilingual AI Government Assistant")
def ask_assistant(
    payload: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Lookup business if available
    business = db.query(BusinessProfile).filter(BusinessProfile.user_id == current_user.id).first()
    return ask_government_assistant(
        db=db,
        question=payload.question,
        language=payload.language,
        business=business,
        context_scheme_id=payload.context_scheme_id
    )

@router.post("/sync", summary="Admin-only: Synchronize scheme catalog and verify sources")
def sync_schemes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrative privilege required for sovereign sync")
    return sync_government_schemes(db)
