
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class VoiceDraftIn(BaseModel):
    """Structured JSON produced by Gauri's speech/AI pipeline.

    Extra fields are tolerated (extra="allow") so her schema can evolve
    without breaking this endpoint.
    """
    model_config = {"extra": "allow"}

    intent: str  # sale | credit_sale | purchase | expense | payment
    customer: dict[str, Any] | None = None   # {"name": ..., "phone": ...}
    items: list[dict[str, Any]] | None = None  # [{"name":..., "quantity":..., "unit_price":...}]
    amount: Decimal | None = None            # used when there are no line items
    note: str | None = None


class VoiceDraftOut(BaseModel):
    draft_id: str
    expires_at: datetime
    parsed: dict[str, Any]  # normalized preview for the confirmation screen
    message: str


class VoiceConfirmIn(BaseModel):
    draft_id: str
    confirmed: bool
    corrections: dict[str, Any] | None = None  # optional user edits before saving


class VoiceConfirmOut(BaseModel):
    saved: bool
    transaction_id: int | None = None
    payment_id: int | None = None
    already_saved: bool = False


from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_business
from app.models import Business
from app.models.enums import TransactionType
from app.schemas.transaction import TransactionOut, TransactionItemIn
from app.schemas.voice import VoiceConfirmIn, VoiceConfirmOut, VoiceDraftIn, VoiceDraftOut
from app.services import payments as payment_service
from app.services import transactions as txn_service
from app.services import voice as voice_service
from app.utils.draft_store import voice_drafts
from app.utils.responses import fail, ok

router = APIRouter(prefix="/voice", tags=["Voice Integration"])


@router.post("/draft", status_code=201)
def create_draft(payload: VoiceDraftIn,
                 business: Business = Depends(get_current_business),
                 db: Session = Depends(get_db)):
    """Receives Gauri's structured JSON, validates it and stages a draft.
    Nothing is written to the ledger yet."""
    normalized = voice_service.build_draft(db, business, payload.model_dump(exclude_unset=True))
    draft_id = voice_drafts.put({
        "business_id": business.id,
        "user_id": business.user_id,
        "normalized": normalized,
    })
    return ok(VoiceDraftOut(
        draft_id=draft_id,
        expires_at=None,  # filled below via store TTL
        parsed=normalized,
        message="Draft staged. Confirm via POST /voice/confirm to save to the ledger.",
    ).model_dump() | {"expires_in_seconds": 900})


@router.post("/confirm")
def confirm_draft(payload: VoiceConfirmIn,
                  business: Business = Depends(get_current_business),
                  db: Session = Depends(get_db)):
    """User-confirmed save. Idempotent per draft: re-confirming returns the
    already-saved result instead of creating a duplicate."""
    draft = voice_drafts.get(payload.draft_id)
    if draft is None:
        fail(404, "DRAFT_NOT_FOUND", "Draft missing or expired. Re-run POST /voice/draft.")
    if draft["business_id"] != business.id:
        fail(403, "FORBIDDEN", "This draft belongs to a different business.")

    if draft.get("result"):
        result = draft["result"]
        return ok(VoiceConfirmOut(saved=True, already_saved=True,
                                  transaction_id=result.get("transaction_id"),
                                  payment_id=result.get("payment_id")).model_dump())

    if not payload.confirmed:
        return ok(VoiceConfirmOut(saved=False).model_dump())

    normalized = dict(draft["normalized"])
    corrections = payload.corrections or {}
    if corrections.get("customer_id"):
        normalized["customer_id"] = corrections["customer_id"]
    if corrections.get("items"):
        normalized["items"] = corrections["items"]
    if corrections.get("note") is not None:
        normalized["note"] = corrections["note"]

    idem = f"voice-{payload.draft_id}"
    txn_type = TransactionType(normalized["transaction_type"])

    if normalized["is_payment"]:
        payment, _ = payment_service.record_payment(
            db, business,
            customer_id=normalized.get("customer_id"),
            amount=normalized["computed_total"],
            method="cash",
            notes=normalized.get("note"),
            idempotency_key=idem,
        )
        result = {"payment_id": payment.id, "transaction_id": payment.transaction_id}
    else:
        items = [
            TransactionItemIn(name=i["name"], quantity=i["quantity"], unit_price=i["unit_price"])
            for i in normalized["items"]
        ]
        txn, _ = txn_service.create_transaction(
            db, business,
            txn_type=txn_type,
            customer_id=normalized.get("customer_id"),
            items=items,
            notes=normalized.get("note"),
            idempotency_key=idem,
        )
        result = {"transaction_id": txn.id, "payment_id": None}

    voice_drafts.set_result(payload.draft_id, result)
    return ok(VoiceConfirmOut(saved=True, already_saved=False,
                              transaction_id=result["transaction_id"],
                              payment_id=result["payment_id"]).model_dump())


