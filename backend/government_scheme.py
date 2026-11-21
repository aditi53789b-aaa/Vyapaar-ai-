from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Source Registry Schemas ---
class GovernmentSourceBase(BaseModel):
    source_code: str
    name: str
    ministry: str
    portal_url: str
    api_endpoint: Optional[str] = None
    integration_tier: str
    auth_requirements: str = "NONE"
    status: str = "VERIFIED"
    is_official: bool = True
    verification_notes: Optional[str] = None

class GovernmentSourceCreate(GovernmentSourceBase):
    pass

class GovernmentSourceResponse(GovernmentSourceBase):
    id: int
    last_sync_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Scheme Catalog Schemas ---
class GovernmentSchemeBase(BaseModel):
    scheme_code: str
    name: str
    hindi_name: Optional[str] = None
    ministry: str
    administering_level: str = "CENTRAL"
    state: str = "ALL"
    scheme_category: str
    short_description: str
    detailed_description: Optional[str] = None
    key_benefits: Optional[str] = None
    max_financial_benefit: float = 0.0
    subsidy_percentage: float = 0.0
    interest_subvention: float = 0.0
    collateral_required: bool = False
    min_turnover: float = 0.0
    max_turnover: float = 1000000000.0
    min_operating_years: int = 0
    eligible_business_types: str = "all"
    eligible_social_categories: str = "all"
    eligible_genders: str = "all"
    required_documents: Optional[str] = None
    official_portal_url: str
    application_portal_url: Optional[str] = None
    api_supported: bool = False

class GovernmentSchemeCreate(GovernmentSchemeBase):
    source_id: Optional[int] = None

class GovernmentSchemeResponse(GovernmentSchemeBase):
    id: int
    source_id: Optional[int]
    verification_date: datetime
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class SchemeListResponse(BaseModel):
    total: int
    items: List[GovernmentSchemeResponse]
    categories: List[str]
    ministries: List[str]

# --- Personalized Assessment Schemas ---
class AssessmentCriterion(BaseModel):
    title: str
    status: str  # SATISFIED, NOT_SATISFIED, UNVERIFIED
    description: str

class SchemeAssessmentResponse(BaseModel):
    scheme_id: int
    scheme_code: str
    scheme_name: str
    hindi_name: Optional[str]
    match_score: float  # 0 to 100
    eligibility_status: str  # HIGHLY_RECOMMENDED, POTENTIALLY_ELIGIBLE, INELIGIBLE, INSUFFICIENT_DATA
    satisfied_criteria: List[str]
    missing_criteria: List[str]
    unverified_criteria: List[str]
    ai_explanation: str
    ai_explanation_hindi: Optional[str]
    recommended_actions: List[str]
    official_portal_url: str
    application_portal_url: Optional[str]
    assessed_at: datetime

# --- Application Readiness Schemas ---
class ChecklistItem(BaseModel):
    key: str
    name: str
    is_required: bool
    is_satisfied: bool
    reusable_from_ledger: bool
    source_field: Optional[str] = None
    help_text: Optional[str] = None

class FinancialSummarySnapshot(BaseModel):
    total_sales_recorded: float
    monthly_sales_runrate: float
    recorded_transactions_count: int
    total_udhar_outstanding: float
    udhar_recovery_percentage: float
    estimated_operating_profit: float
    data_freshness_period: str

class ReadinessResponse(BaseModel):
    scheme_id: int
    scheme_name: str
    scheme_code: str
    readiness_percentage: float
    checklist: List[ChecklistItem]
    financial_summary: FinancialSummarySnapshot
    application_status: str
    portal_reference_number: Optional[str] = None
    official_application_url: str
    step_by_step_instructions: List[str]

class UpdateReadinessConsentRequest(BaseModel):
    consent_given: bool
    portal_reference_number: Optional[str] = None

# --- Scheme Document Schemas ---
class SchemeDocumentResponse(BaseModel):
    id: int
    document_type: str
    file_name: str
    file_size: int
    verification_status: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Application Guide Schema ---
class ApplicationGuideResponse(BaseModel):
    scheme_name: str
    ministry: str
    official_portal_url: str
    application_portal_url: str
    submission_mode: str  # ONLINE_PORTAL, CSC_FACILITATION, BANK_BRANCH, DIRECT_API
    fees: str
    prerequisites: List[str]
    step_by_step_steps: List[Dict[str, str]]
    disclaimers: List[str]
    helpline_contacts: List[Dict[str, str]]

# --- AI Assistant / RAG Schemas ---
class RAGQueryRequest(BaseModel):
    question: str
    language: str = "en"  # "en" or "hi"
    context_scheme_id: Optional[int] = None

class RAGQueryResponse(BaseModel):
    question: str
    answer: str
    language: str
    sources: List[Dict[str, Any]]
    confidence_level: str
    disclaimer: str
