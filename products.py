
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_business
from app.models import Business, Product
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.utils.responses import fail, ok

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("", status_code=201)
def create_product(payload: ProductCreate, business: Business = Depends(get_current_business),
                   db: Session = Depends(get_db)):
    product = Product(business_id=business.id, **payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return ok(ProductOut.model_validate(product).model_dump())


@router.get("")
def list_products(search: str | None = Query(default=None, max_length=100),
                  skip: int = Query(default=0, ge=0),
                  limit: int = Query(default=50, ge=1, le=200),
                  business: Business = Depends(get_current_business),
                  db: Session = Depends(get_db)):
    stmt = select(Product).where(Product.business_id == business.id, Product.is_active.is_(True))
    if search:
        stmt = stmt.where(Product.name.ilike(f"%{search}%"))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(Product.name).offset(skip).limit(limit)).scalars().all()
    return ok({"items": [ProductOut.model_validate(r).model_dump() for r in rows],
               "total": total, "skip": skip, "limit": limit})


@router.patch("/{product_id}")
def update_product(product_id: int, payload: ProductUpdate,
                   business: Business = Depends(get_current_business),
                   db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None or product.business_id != business.id:
        fail(404, "PRODUCT_NOT_FOUND", "Product not found in this business.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return ok(ProductOut.model_validate(product).model_dump())


@router.delete("/{product_id}")
def delete_product(product_id: int, business: Business = Depends(get_current_business),
                   db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None or product.business_id != business.id:
        fail(404, "PRODUCT_NOT_FOUND", "Product not found in this business.")
    product.is_active = False  # keep history on old transaction items
    db.commit()
    return ok({"deleted": True})