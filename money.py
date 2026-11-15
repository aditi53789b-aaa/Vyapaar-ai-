
from decimal import ROUND_HALF_UP, Decimal

PAISE = Decimal("0.01")


def to_money(value) -> Decimal:
    """Normalize any numeric input to a 2-decimal Decimal. Never use floats for money."""
    return Decimal(str(value)).quantize(PAISE, rounding=ROUND_HALF_UP)