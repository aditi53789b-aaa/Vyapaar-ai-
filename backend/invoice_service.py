from sqlalchemy.orm import Session
from app.models.invoice import Invoice, InvoiceItem
from app.models.transaction import Transaction
from app.schemas.invoice import InvoiceCreate

def create_invoice(db: Session, business_id: int, data: InvoiceCreate) -> Invoice:
    invoice = Invoice(
        business_id=business_id,
        customer_id=data.customer_id,
        invoice_number=data.invoice_number,
        subtotal=data.subtotal,
        tax_amount=data.tax_amount,
        total_amount=data.total_amount,
        payment_status=data.payment_status,
        due_date=data.due_date,
        notes=data.notes
    )
    db.add(invoice)
    db.flush()

    for item in data.items:
        inv_item = InvoiceItem(
            invoice_id=invoice.id,
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            tax_rate=item.tax_rate,
            total=item.total
        )
        db.add(inv_item)

    # If paid, record sale transaction
    if invoice.payment_status == "PAID":
        sale_txn = Transaction(
            business_id=business_id,
            customer_id=data.customer_id,
            type="SALE",
            amount=invoice.total_amount,
            payment_mode="INVOICE_SETTLED",
            notes=f"Auto-recorded from Invoice #{invoice.invoice_number}"
        )
        db.add(sale_txn)

    db.commit()
    db.refresh(invoice)
    return invoice
