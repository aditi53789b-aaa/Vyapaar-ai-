from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List, Dict, Any
from app.models.government_scheme import GovernmentScheme
from app.schemas.government_scheme import SchemeListResponse, GovernmentSchemeResponse

def discover_schemes(
    db: Session,
    query: Optional[str] = None,
    category: Optional[str] = None,
    administering_level: Optional[str] = None,
    state: Optional[str] = None,
    collateral_free_only: bool = False,
    skip: int = 0,
    limit: int = 50
) -> SchemeListResponse:
    q = db.query(GovernmentScheme).filter(GovernmentScheme.is_active == True)
    
    # 1. Text Search across English, Hindi, and Ministry names
    if query:
        search_term = f"%{query.strip()}%"
        q = q.filter(
            or_(
                GovernmentScheme.name.ilike(search_term),
                GovernmentScheme.hindi_name.ilike(search_term),
                GovernmentScheme.ministry.ilike(search_term),
                GovernmentScheme.short_description.ilike(search_term),
                GovernmentScheme.key_benefits.ilike(search_term),
                GovernmentScheme.scheme_code.ilike(search_term)
            )
        )
        
    # 2. Filter by Category
    if category and category.upper() != "ALL":
        q = q.filter(GovernmentScheme.scheme_category == category.upper())
        
    # 3. Filter by Administering Level
    if administering_level and administering_level.upper() != "ALL":
        q = q.filter(GovernmentScheme.administering_level == administering_level.upper())
        
    # 4. Filter by State
    if state and state.upper() != "ALL":
        q = q.filter(
            or_(
                GovernmentScheme.state == "ALL",
                GovernmentScheme.state.ilike(f"%{state}%")
            )
        )
        
    # 5. Collateral-free filter
    if collateral_free_only:
        q = q.filter(GovernmentScheme.collateral_required == False)
        
    total = q.count()
    items = q.order_by(GovernmentScheme.id.asc()).offset(skip).limit(limit).all()
    
    # Extract distinct categories and ministries
    all_schemes = db.query(GovernmentScheme.scheme_category, GovernmentScheme.ministry).all()
    categories = sorted(list({c[0] for c in all_schemes if c[0]}))
    ministries = sorted(list({c[1] for c in all_schemes if c[1]}))
    
    return SchemeListResponse(
        total=total,
        items=[GovernmentSchemeResponse.model_validate(item) for item in items],
        categories=categories,
        ministries=ministries
    )

def get_scheme_by_id(db: Session, scheme_id: int) -> Optional[GovernmentScheme]:
    return db.query(GovernmentScheme).filter(GovernmentScheme.id == scheme_id).first()

def get_scheme_by_code(db: Session, scheme_code: str) -> Optional[GovernmentScheme]:
    return db.query(GovernmentScheme).filter(GovernmentScheme.scheme_code == scheme_code).first()
