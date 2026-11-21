from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional
from app.models.government_source import GovernmentSource
from app.schemas.government_scheme import GovernmentSourceCreate

OFFICIAL_SOURCE_CATALOG = [
    {
        "source_code": "MSME_UDYAM",
        "name": "Udyam Registration Portal",
        "ministry": "Ministry of Micro, Small and Medium Enterprises (MoMSME)",
        "portal_url": "https://udyamregistration.gov.in/",
        "api_endpoint": "https://api.setu.co/api/v1/udyam",
        "integration_tier": "TIER_2_AUTHORIZED_GATEWAY",
        "auth_requirements": "API_KEY / DIGILOCKER",
        "status": "VERIFIED",
        "is_official": True,
        "verification_notes": "Official zero-cost portal for MSME classification and priority sector lending recognition."
    },
    {
        "source_code": "MSME_UBP",
        "name": "Udyam Assist Platform (UBP)",
        "ministry": "Ministry of MSME / SIDBI",
        "portal_url": "https://www.ubp.msme.gov.in/",
        "api_endpoint": "https://ubp.msme.gov.in/api/v1/ime-validate",
        "integration_tier": "TIER_2_AUTHORIZED_GATEWAY",
        "auth_requirements": "DESIGNATED_AGGREGATOR_AUTH",
        "status": "VERIFIED",
        "is_official": True,
        "verification_notes": "Enables Informal Micro Enterprises (IMEs) to obtain priority lending certificates."
    },
    {
        "source_code": "MYSCHEME_GOV",
        "name": "myScheme National Platform",
        "ministry": "Ministry of Electronics & Information Technology (MeitY) / NeGD",
        "portal_url": "https://www.myscheme.gov.in/",
        "api_endpoint": "https://api.myscheme.gov.in/public/v1/schemes",
        "integration_tier": "TIER_1_PUBLIC_API",
        "auth_requirements": "PUBLIC_REST",
        "status": "VERIFIED",
        "is_official": True,
        "verification_notes": "National scheme discovery portal offering open scheme taxonomy and rules."
    },
    {
        "source_code": "DFS_JANSAMARTH",
        "name": "Jan Samarth National Portal",
        "ministry": "Department of Financial Services (DFS), Ministry of Finance",
        "portal_url": "https://www.jansamarth.in/",
        "api_endpoint": "https://partner.jansamarth.in/api/v1/lead",
        "integration_tier": "TIER_2_AUTHORIZED_GATEWAY",
        "auth_requirements": "OCEN_PARTNER_OAUTH2",
        "status": "VERIFIED",
        "is_official": True,
        "verification_notes": "Single unified platform linking 13+ credit-linked government subsidy schemes to 200+ partner banks."
    },
    {
        "source_code": "PMMY_MUDRA",
        "name": "Pradhan Mantri MUDRA Yojana (PMMY)",
        "ministry": "Department of Financial Services, Ministry of Finance",
        "portal_url": "https://www.mudra.org.in/",
        "api_endpoint": None,
        "integration_tier": "TIER_3_ASSISTED_PORTAL",
        "auth_requirements": "NONE",
        "status": "VERIFIED",
        "is_official": True,
        "verification_notes": "Loans up to 20 Lakhs across Shishu, Kishore, Tarun and Tarun Plus categories via banks and NBFCs."
    },
    {
        "source_code": "MOHUA_PMSVANIDHI",
        "name": "PM SVANidhi Scheme Portal",
        "ministry": "Ministry of Housing and Urban Affairs (MoHUA)",
        "portal_url": "https://pmsvanidhi.mohua.gov.in/",
        "api_endpoint": "https://pmsvanidhi.mohua.gov.in/api/vendor-status",
        "integration_tier": "TIER_2_AUTHORIZED_GATEWAY",
        "auth_requirements": "ULB_MLI_AUTHENTICATION",
        "status": "VERIFIED",
        "is_official": True,
        "verification_notes": "Working capital credit for urban and peri-urban street vendors with 7% interest subvention."
    },
    {
        "source_code": "MSME_PMVISHWAKARMA",
        "name": "PM Vishwakarma Portal",
        "ministry": "Ministry of MSME & Ministry of Skill Development",
        "portal_url": "https://pmvishwakarma.gov.in/",
        "api_endpoint": None,
        "integration_tier": "TIER_3_ASSISTED_PORTAL",
        "auth_requirements": "CSC_AADHAAR_BIOMETRIC",
        "status": "VERIFIED",
        "is_official": True,
        "verification_notes": "End-to-end support for 18 traditional artisan trades with toolkit incentive (₹15,000) and 5% credit."
    },
    {
        "source_code": "KVIC_PMEGP",
        "name": "PMEGP e-Portal",
        "ministry": "Khadi and Village Industries Commission (KVIC) / MoMSME",
        "portal_url": "https://www.kviconline.gov.in/pmegpeportal/",
        "api_endpoint": None,
        "integration_tier": "TIER_3_ASSISTED_PORTAL",
        "auth_requirements": "NONE",
        "status": "VERIFIED",
        "is_official": True,
        "verification_notes": "Credit-linked subsidy up to 35% for new micro-enterprises in manufacturing and services."
    },
    {
        "source_code": "SIDBI_CGTMSE",
        "name": "CGTMSE Trust Portal",
        "ministry": "SIDBI & Ministry of MSME",
        "portal_url": "https://www.cgtmse.in/",
        "api_endpoint": None,
        "integration_tier": "TIER_4_VERIFIED_REPOSITORY",
        "auth_requirements": "MEMBER_LENDING_INSTITUTION_ONLY",
        "status": "VERIFIED",
        "is_official": True,
        "verification_notes": "Credit guarantee coverage up to ₹5 Crore for collateral-free MSME bank loans."
    },
    {
        "source_code": "MOA_PMKISAN",
        "name": "PM-KISAN Portal",
        "ministry": "Ministry of Agriculture and Farmers Welfare",
        "portal_url": "https://pmkisan.gov.in/",
        "api_endpoint": "https://pmkisan.gov.in/public-api/beneficiary-status",
        "integration_tier": "TIER_1_PUBLIC_API",
        "auth_requirements": "AADHAAR_OTP_PUBLIC",
        "status": "VERIFIED",
        "is_official": True,
        "verification_notes": "Direct Income Support of ₹6,000/year to landholding farmer families. Strictly gated for agri-merchants."
    },
    {
        "source_code": "COMMERCE_GEM",
        "name": "Government e-Marketplace (GeM)",
        "ministry": "Ministry of Commerce and Industry",
        "portal_url": "https://gem.gov.in/",
        "api_endpoint": "https://gem.gov.in/api/v1/seller-onboarding",
        "integration_tier": "TIER_2_AUTHORIZED_GATEWAY",
        "auth_requirements": "PAN_AADHAAR_AUTH",
        "status": "VERIFIED",
        "is_official": True,
        "verification_notes": "National public procurement portal with 25% mandatory procurement preference from MSEs."
    },
    {
        "source_code": "MSME_SAMADHAAN",
        "name": "MSME Samadhaan Delayed Payments Portal",
        "ministry": "Ministry of Micro, Small and Medium Enterprises",
        "portal_url": "https://samadhaan.msme.gov.in/",
        "api_endpoint": None,
        "integration_tier": "TIER_3_ASSISTED_PORTAL",
        "auth_requirements": "UDYAM_OTP",
        "status": "VERIFIED",
        "is_official": True,
        "verification_notes": "Statutory monitoring of delayed payments to micro and small enterprises with compound interest penalisation."
    }
]

def init_government_sources(db: Session) -> List[GovernmentSource]:
    """Ensures all official verified sources exist in the database."""
    sources = []
    for item in OFFICIAL_SOURCE_CATALOG:
        existing = db.query(GovernmentSource).filter(GovernmentSource.source_code == item["source_code"]).first()
        if not existing:
            source = GovernmentSource(**item)
            db.add(source)
            sources.append(source)
        else:
            # Refresh attributes
            for k, v in item.items():
                setattr(existing, k, v)
            existing.last_sync_at = datetime.now(timezone.utc)
            sources.append(existing)
    db.commit()
    return db.query(GovernmentSource).all()

def get_all_sources(db: Session) -> List[GovernmentSource]:
    sources = db.query(GovernmentSource).order_by(GovernmentSource.id).all()
    if not sources:
        sources = init_government_sources(db)
    return sources

def get_source_by_code(db: Session, source_code: str) -> Optional[GovernmentSource]:
    return db.query(GovernmentSource).filter(GovernmentSource.source_code == source_code).first()
