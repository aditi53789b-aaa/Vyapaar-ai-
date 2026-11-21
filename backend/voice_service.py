import re
from typing import Dict, Any

def parse_voice_transaction(transcript: str) -> Dict[str, Any]:
    """
    Parses merchant natural language voice transcripts in Hindi, Hinglish, and English.
    Examples:
    - "Ramesh ko 500 rupaye ka samaan udhar diya" -> type: CREDIT_GIVEN, customer: Ramesh, amount: 500
    - "Suresh ne 1200 rupaye jama kiye" -> type: PAYMENT_RECEIVED, customer: Suresh, amount: 1200
    - "Dukan ke liye 450 ka petrol kharch hua" -> type: EXPENSE, amount: 450
    - "Cash sale of 2500 rupees today" -> type: SALE, amount: 2500
    """
    text = transcript.lower().strip()
    
    # 1. Extract amount
    # Matches patterns like "500", "500 rupaye", "₹500", "500.50"
    amount = 0.0
    amount_match = re.search(r'(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?)\s*(?:rupaye|rupees|rs)?', text)
    if amount_match:
        try:
            amount = float(amount_match.group(1))
        except ValueError:
            amount = 0.0

    # 2. Identify transaction type & intent
    txn_type = "SALE"
    if any(k in text for k in ["udhar", "baaki", "credit", "debit diya", "udhar diya"]):
        txn_type = "CREDIT_GIVEN"
    elif any(k in text for k in ["jama", "diya", "received", "payment mila", "wapas diya", "paid"]):
        txn_type = "PAYMENT_RECEIVED"
    elif any(k in text for k in ["kharch", "expense", "purchase", "diesel", "petrol", "rent"]):
        txn_type = "EXPENSE"
    elif any(k in text for k in ["sale", "bika", "becha", "cash mila"]):
        txn_type = "SALE"

    # 3. Identify customer name
    customer_name = None
    # Pattern: "X ko ... udhar" or "X ne ... jama"
    cust_match = re.search(r'([a-zA-Z\u0900-\u097F]+)\s+(?:ko|ne|from|to)', transcript, re.IGNORECASE)
    if cust_match:
        extracted = cust_match.group(1).strip()
        if extracted.lower() not in ["aaj", "kal", "dukan", "cash", "upi"]:
            customer_name = extracted.capitalize()

    return {
        "raw_transcript": transcript,
        "amount": amount,
        "transaction_type": txn_type,
        "customer_name": customer_name,
        "detected_language": "hi-IN" if re.search(r'[\u0900-\u097F]', transcript) or "rupaye" in text else "en-IN",
        "status": "PARSED"
    }
