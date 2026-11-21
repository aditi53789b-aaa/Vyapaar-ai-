import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.business import BusinessProfile
from app.models.government_scheme import GovernmentScheme
from app.models.scheme_assessment import SchemeAssessment
from app.models.transaction import Transaction
from app.schemas.government_scheme import SchemeAssessmentResponse

DISCLAIMER_TEXT = (
    "Disclaimer: This assessment is an AI-assisted indicative readiness check based on your Vyapaar AI records. "
    "It is NOT an official government approval. Actual loan sanctions and scheme benefits depend on verification "
    "by the designated Ministry, Bank, or Implementing Agency on the official sovereign portal."
)

def assess_scheme_eligibility(
    db: Session,
    business: BusinessProfile,
    scheme: GovernmentScheme
) -> SchemeAssessmentResponse:
    satisfied: List[str] = []
    missing: List[str] = []
    unverified: List[str] = []
    recommended_actions: List[str] = []
    
    score = 0.0
    status = "POTENTIALLY_ELIGIBLE"
    current_year = datetime.now(timezone.utc).year
    operating_years = max(0, current_year - (business.operating_since_year or current_year))
    
    # -------------------------------------------------------------
    # 1. HARD SAFETY FIREWALL: Agriculture & Farmer Schemes (PM-KISAN)
    # -------------------------------------------------------------
    is_agri_merchant = (
        business.business_category.lower() in ["agriculture", "farmer", "farming", "agri_allied"] or
        business.merchant_type.lower() in ["farmer", "agriculturalist"]
    )
    
    if scheme.scheme_category == "FARMER_SUPPORT" or scheme.scheme_code == "PM_KISAN_SAMMAN":
        if not is_agri_merchant:
            return SchemeAssessmentResponse(
                scheme_id=scheme.id,
                scheme_code=scheme.scheme_code,
                scheme_name=scheme.name,
                hindi_name=scheme.hindi_name,
                match_score=0.0,
                eligibility_status="INELIGIBLE",
                satisfied_criteria=[],
                missing_criteria=[
                    "Business category is not Agriculture or Farming (Registered as: " + business.business_category + ")",
                    "Valid cultivable landholding records (Khasra/Khatauni) required by Ministry of Agriculture"
                ],
                unverified_criteria=[],
                ai_explanation="You are not eligible for PM-KISAN because your business is registered under non-agricultural commercial trade. PM-KISAN is legally restricted solely to landholding farmer families.",
                ai_explanation_hindi="आप पीएम-किसान के लिए पात्र नहीं हैं क्योंकि आपका व्यवसाय गैर-कृषि व्यापार के अंतर्गत पंजीकृत है। पीएम-किसान विशेष रूप से किसान परिवारों के लिए आरक्षित है।",
                recommended_actions=[
                    "Explore MSME, MUDRA or PM SVANidhi programmes suitable for your retail or micro-enterprise trade."
                ],
                official_portal_url=scheme.official_portal_url,
                application_portal_url=scheme.application_portal_url,
                assessed_at=datetime.now(timezone.utc)
            )
        else:
            satisfied.append("Verified as agricultural producer / farmer category")
            score += 35.0

    # -------------------------------------------------------------
    # 2. Business Category & Merchant Type Evaluation
    # -------------------------------------------------------------
    eligible_types = [t.strip().lower() for t in (scheme.eligible_business_types or "all").split(",") if t.strip()]
    
    if "all" in eligible_types:
        satisfied.append(f"Business type '{business.business_category}' is eligible under open sector guidelines")
        score += 35.0
    elif (
        business.business_category.lower() in eligible_types or 
        business.merchant_type.lower() in eligible_types
    ):
        satisfied.append(f"Target sector matched: {business.merchant_type.replace('_', ' ').title()} / {business.business_category.title()}")
        score += 35.0
    else:
        # Check partial alignment
        if scheme.scheme_category == "VENDOR_SUPPORT" and business.merchant_type != "street_vendor":
            missing.append(f"Requires registration as an Urban/Peri-urban Street Vendor with a Certificate of Vending (CoV)")
            score += 5.0
        elif scheme.scheme_category == "ARTISAN_SUPPORT" and business.business_category != "artisan_handicrafts":
            missing.append(f"Scheme is targeted specifically at the 18 designated traditional artisan and crafts trades")
            score += 5.0
        else:
            satisfied.append(f"General commercial enterprise in {business.business_category}")
            score += 20.0

    # -------------------------------------------------------------
    # 3. Turnover & Scale Evaluation
    # -------------------------------------------------------------
    turnover = business.annual_turnover or 0.0
    if turnover >= scheme.min_turnover and turnover <= scheme.max_turnover:
        satisfied.append(f"Annual turnover (₹{turnover:,.0f}) is within the allowable limit (Max: ₹{scheme.max_turnover:,.0f})")
        score += 25.0
    elif turnover < scheme.min_turnover:
        missing.append(f"Minimum annual turnover required is ₹{scheme.min_turnover:,.0f} (Recorded: ₹{turnover:,.0f})")
        recommended_actions.append(f"Record more completed sales transactions in your Vyapaar AI digital khata to build verifiable business turnover.")
    else:
        missing.append(f"Turnover exceeds the micro-enterprise ceiling for this subsidized scheme")

    # -------------------------------------------------------------
    # 4. Operating Duration Evaluation
    # -------------------------------------------------------------
    if operating_years >= scheme.min_operating_years:
        if scheme.min_operating_years > 0:
            satisfied.append(f"Business operational for {operating_years} years (Meets minimum {scheme.min_operating_years} year requirement)")
        else:
            satisfied.append("New and existing micro-enterprises both eligible")
        score += 15.0
    else:
        missing.append(f"Requires at least {scheme.min_operating_years} years of continuous operation (Current: {operating_years} years)")

    # -------------------------------------------------------------
    # 5. Geographic Alignment (State Schemes)
    # -------------------------------------------------------------
    if scheme.administering_level == "CENTRAL" or scheme.state == "ALL":
        satisfied.append(f"Nationwide Central Government programme (Applicable in {business.state})")
        score += 10.0
    elif business.state and scheme.state.lower() in business.state.lower():
        satisfied.append(f"State-specific programme matched for {business.state}")
        score += 10.0
    else:
        missing.append(f"Scheme is restricted to {scheme.state} (Your business is registered in {business.state})")

    # -------------------------------------------------------------
    # 6. Registrations & Document Verification Status
    # -------------------------------------------------------------
    if business.udyam_registration_no:
        satisfied.append(f"Official Udyam registration verified ({business.udyam_registration_no})")
        score += 10.0
    else:
        unverified.append("Udyam Registration Certificate (Recommended for PSL interest rebates and collateral waiver)")
        recommended_actions.append("Complete free Udyam registration on udyamregistration.gov.in using your Aadhaar.")

    if business.pan:
        satisfied.append("PAN details recorded")
        score += 5.0
    else:
        unverified.append("PAN Card needed for bank loan documentation")

    # Social category bonuses (Women / SC / ST / OBC)
    if scheme.scheme_code == "PMEGP_SCHEME":
        if business.owner_gender == "female" or business.social_category in ["sc", "st", "obc", "minority"]:
            satisfied.append(f"Special Category subsidy rate applies (Up to 35% subsidy instead of 15% general)")
            score += 5.0
            
    # Calculate Final Status
    score = min(100.0, max(0.0, score))
    
    if len(missing) == 0 and score >= 75.0:
        status = "HIGHLY_RECOMMENDED"
        ai_explanation = (
            f"Your business profile strongly matches {scheme.name}. Your category, turnover, and operational "
            f"track record satisfy the core criteria. You can proceed to prepare your application dossier."
        )
        ai_explanation_hindi = (
            f"आपकी व्यावसायिक प्रोफ़ाइल {scheme.hindi_name or scheme.name} के सभी मुख्य मानदंडों से मेल खाती है। "
            f"आपका व्यापार प्रकार, टर्नओवर और रिकॉर्ड ऋण पात्रता को पूरा करते हैं।"
        )
    elif len(missing) <= 1 and score >= 50.0:
        status = "POTENTIALLY_ELIGIBLE"
        ai_explanation = (
            f"You are potentially eligible for {scheme.name}. Most core parameters match, but you have "
            f"{len(missing)} requirement(s) or document verifications to complete before applying."
        )
        ai_explanation_hindi = (
            f"आप {scheme.hindi_name or scheme.name} के लिए संभावित रूप से पात्र हैं। "
            f"आवेदन करने से पहले कृपया शेष आवश्यक विवरण और दस्तावेज पूरे करें।"
        )
    else:
        status = "INELIGIBLE"
        ai_explanation = (
            f"Currently, your business does not meet one or more primary criteria for {scheme.name}. "
            f"Review the missing requirements below."
        )
        ai_explanation_hindi = (
            f"वर्तमान में आपका व्यवसाय {scheme.hindi_name or scheme.name} के एक या अधिक मुख्य मानदंडों को पूरा नहीं करता है।"
        )

    # Persistence to database
    existing_assessment = db.query(SchemeAssessment).filter(
        SchemeAssessment.business_id == business.id,
        SchemeAssessment.scheme_id == scheme.id
    ).first()
    
    if not existing_assessment:
        assessment = SchemeAssessment(
            business_id=business.id,
            scheme_id=scheme.id,
            match_score=score,
            eligibility_status=status,
            satisfied_criteria=json.dumps(satisfied),
            missing_criteria=json.dumps(missing),
            unverified_criteria=json.dumps(unverified),
            ai_explanation=ai_explanation,
            ai_explanation_hindi=ai_explanation_hindi,
            recommended_actions=json.dumps(recommended_actions),
            assessed_at=datetime.now(timezone.utc)
        )
        db.add(assessment)
    else:
        existing_assessment.match_score = score
        existing_assessment.eligibility_status = status
        existing_assessment.satisfied_criteria = json.dumps(satisfied)
        existing_assessment.missing_criteria = json.dumps(missing)
        existing_assessment.unverified_criteria = json.dumps(unverified)
        existing_assessment.ai_explanation = ai_explanation
        existing_assessment.ai_explanation_hindi = ai_explanation_hindi
        existing_assessment.recommended_actions = json.dumps(recommended_actions)
        existing_assessment.assessed_at = datetime.now(timezone.utc)
        
    db.commit()

    return SchemeAssessmentResponse(
        scheme_id=scheme.id,
        scheme_code=scheme.scheme_code,
        scheme_name=scheme.name,
        hindi_name=scheme.hindi_name,
        match_score=score,
        eligibility_status=status,
        satisfied_criteria=satisfied,
        missing_criteria=missing,
        unverified_criteria=unverified,
        ai_explanation=ai_explanation,
        ai_explanation_hindi=ai_explanation_hindi,
        recommended_actions=recommended_actions,
        official_portal_url=scheme.official_portal_url,
        application_portal_url=scheme.application_portal_url,
        assessed_at=datetime.now(timezone.utc)
    )

def get_recommended_schemes_for_business(
    db: Session,
    business: BusinessProfile,
    limit: int = 6
) -> List[SchemeAssessmentResponse]:
    all_schemes = db.query(GovernmentScheme).filter(GovernmentScheme.is_active == True).all()
    assessments = []
    for scheme in all_schemes:
        assessment = assess_scheme_eligibility(db, business, scheme)
        assessments.append(assessment)
        
    # Sort by match score descending, placing Highly Recommended first
    assessments.sort(key=lambda x: x.match_score, reverse=True)
    return assessments[:limit]
