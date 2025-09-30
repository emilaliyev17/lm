import logging
from decimal import Decimal, ROUND_FLOOR

from .models import PrepaidInterest


PREPAID_CHARGE_NAME = "Prepaid Interest"
logger = logging.getLogger(__name__)


def ensure_prepaid_interest_for_loan(loan_card):
    """Create or update prepaid interest record when the charge exists."""

    prepaid_charge = (
        loan_card.settlement_charges
        .select_related('charge_type')
        .filter(charge_type__name=PREPAID_CHARGE_NAME)
        .order_by('-created_at')
        .first()
    )

    if not prepaid_charge:
        return None

    monthly_interest = loan_card.get_monthly_interest_for_initial()

    months = 0
    remainder = Decimal('0')
    if monthly_interest and monthly_interest > 0:
        months_decimal = prepaid_charge.amount / monthly_interest
        months = int(months_decimal.to_integral_value(rounding=ROUND_FLOOR))
        remainder = prepaid_charge.amount - (monthly_interest * Decimal(months))
        remainder = remainder.quantize(Decimal('0.01'))
        if remainder != Decimal('0.00'):
            logger.warning(
                "Prepaid interest for loan %s has remainder %s when divided by monthly interest %s.",
                loan_card.card_number,
                remainder,
                monthly_interest,
            )
    else:
        logger.warning(
            "Monthly interest calculation returned %s for loan %s while creating prepaid interest.",
            monthly_interest,
            loan_card.card_number,
        )

    defaults = {
        'settlement_charge': prepaid_charge,
        'initial_amount': prepaid_charge.amount,
        'remaining_balance': prepaid_charge.amount,
        'months_covered': months,
        'monthly_amount': monthly_interest,
    }

    prepaid_record, created = PrepaidInterest.objects.update_or_create(
        loan_card=loan_card,
        defaults=defaults,
    )

    if created:
        logger.info(
            "Created PrepaidInterest for loan %s with initial amount %s covering %s months.",
            loan_card.card_number,
            prepaid_charge.amount,
            months,
        )
    else:
        logger.info(
            "Updated PrepaidInterest for loan %s with new amount %s covering %s months.",
            loan_card.card_number,
            prepaid_charge.amount,
            months,
        )

    return prepaid_record
