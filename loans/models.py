from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal

class Borrower(models.Model):
    """Заемщик"""
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class SettlementChargeType(models.Model):
    """Configurable settlement charge types"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_required = models.BooleanField(default=False)
    default_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['display_order', 'name']


class LoanCard(models.Model):
    """Main loan record"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('defaulted', 'Defaulted'),
        ('pending', 'Pending'),
    ]
    
    card_number = models.CharField(max_length=50, unique=True)
    borrower = models.ForeignKey(Borrower, on_delete=models.PROTECT, related_name='loan_cards')
    property_address = models.TextField(blank=True, null=True)
    
    # Core amounts - CRITICAL BUSINESS LOGIC
    advanced_loan_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Total debt amount that borrower signed for (J13)"
    )
    
    first_wired_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Initial money actually transferred to borrower (J14)"
    )
    
    total_settlement_charges = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0'),
        help_text="Sum of all settlement charges (J22)"
    )
    
    first_loan_date = models.DateField()
    maturity_date = models.DateField(blank=True, null=True)
    
    initial_interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        default=Decimal('0.13')
    )
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def calculate_checkpoint(self):
        """CRITICAL: J14 + J22 - J13 = 0"""
        checkpoint = self.first_wired_amount + self.total_settlement_charges - self.advanced_loan_amount
        return checkpoint
    
    def update_settlement_charges_total(self):
        """Update total from related charges"""
        from django.db.models import Sum
        total = self.settlement_charges.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        self.total_settlement_charges = total
        self.save(update_fields=['total_settlement_charges'])
    
    def get_total_funded_amount(self):
        """
        Total funded = Advanced Loan Amount + Sum of all additional draws
        This represents the total debt after all additional funding
        """
        from django.db.models import Sum
        additional_draws_total = self.additional_draws.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        return self.advanced_loan_amount + additional_draws_total
    
    def get_monthly_interest_for_initial(self):
        """Monthly interest for first wired amount"""
        return (self.first_wired_amount * self.initial_interest_rate) / 12
    
    def get_total_extension_fees(self):
        from django.db.models import Sum
        total = self.extensions.aggregate(total=Sum('extension_fee'))['total']
        return total or Decimal('0')
    
    def calculate_monthly_interest(self, for_date):
        """Calculate interest for a specific month"""
        # Base interest from advanced loan
        base = self.advanced_loan_amount * Decimal(str(self.initial_interest_rate)) / 12
        
        # Add interest from each additional draw that exists before this date
        for draw in self.additional_draws.filter(draw_date__lte=for_date):
            draw_interest = draw.amount * Decimal(str(draw.interest_rate)) / 12
            base += draw_interest
        
        return base.quantize(Decimal('0.01'))
    
    def __str__(self):
        return f"{self.card_number} - {self.borrower.name}"
    
    class Meta:
        ordering = ['-created_at']


class SettlementCharge(models.Model):
    """Settlement charges for a loan"""
    loan_card = models.ForeignKey(LoanCard, on_delete=models.CASCADE, related_name='settlement_charges')
    charge_type = models.ForeignKey(SettlementChargeType, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.loan_card.update_settlement_charges_total()
    
    def delete(self, *args, **kwargs):
        loan_card = self.loan_card
        super().delete(*args, **kwargs)
        loan_card.update_settlement_charges_total()
    
    def __str__(self):
        return f"{self.charge_type.name}: ${self.amount}"
    
    class Meta:
        ordering = ['charge_type__display_order']


class Draw(models.Model):
    """Additional draws after initial funding"""
    loan_card = models.ForeignKey(LoanCard, on_delete=models.CASCADE, related_name='additional_draws')
    draw_number = models.IntegerField(validators=[MinValueValidator(2)])
    draw_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    interest_rate = models.DecimalField(max_digits=5, decimal_places=4, validators=[MinValueValidator(0), MaxValueValidator(1)])
    invoice_number = models.CharField(max_length=100, blank=True, null=True)
    draw_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    inspection_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    @property
    def monthly_interest(self):
        """Calculate monthly interest"""
        return (self.amount * self.interest_rate) / 12
    
    def __str__(self):
        return f"Draw #{self.draw_number} - ${self.amount}"
    
    class Meta:
        ordering = ['draw_number']
        unique_together = ['loan_card', 'draw_number']


class InterestPayment(models.Model):
    """Interest payment records"""
    loan_card = models.ForeignKey(LoanCard, on_delete=models.CASCADE, related_name='interest_payments')
    period_number = models.IntegerField(blank=True, null=True)
    charge_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    received_date = models.DateField(blank=True, null=True)
    invoice_number = models.CharField(max_length=100, blank=True, null=True)
    
    @property
    def is_paid(self):
        return self.received_date is not None
    
    def __str__(self):
        return f"Interest {self.period_number or 'Daily'} - ${self.amount}"
    
    class Meta:
        ordering = ['charge_date']


class LoanExtension(models.Model):
    loan_card = models.ForeignKey(LoanCard, on_delete=models.CASCADE, related_name='extensions')
    extension_months = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(24)])
    extension_fee = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    has_interest = models.BooleanField(default=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    reason = models.TextField(blank=True)
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Extension for {self.loan_card.card_number}"

    class Meta:
        ordering = ['created_date']


class InterestSchedule(models.Model):
    """Monthly interest payment schedule for loan cards"""
    PERIOD_TYPE_CHOICES = [
        ('daily', 'Daily'),
        ('monthly', 'Monthly'),
    ]
    
    loan_card = models.ForeignKey(LoanCard, on_delete=models.CASCADE, related_name='interest_schedules')
    period_number = models.IntegerField(
        help_text="0 for daily, 1,2,3... for monthly periods"
    )
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPE_CHOICES)
    charge_date = models.DateField()
    calculated_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        help_text="Auto-calculated interest amount"
    )
    adjusted_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        blank=True, 
        null=True,
        help_text="Manual adjustments to calculated amount"
    )
    is_posted = models.BooleanField(default=False)
    received_date = models.DateField(blank=True, null=True)
    invoice_number = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="QuickBooks Online invoice number"
    )
    posted_at = models.DateTimeField(blank=True, null=True)
    posted_by = models.CharField(max_length=100, blank=True, null=True)
    
    @property
    def effective_amount(self):
        """Return adjusted amount if set, otherwise calculated amount"""
        return self.adjusted_amount if self.adjusted_amount is not None else self.calculated_amount
    
    def clean(self):
        """Validate that posted records cannot be modified"""
        if self.pk:  # Only check for existing records
            try:
                old_instance = InterestSchedule.objects.get(pk=self.pk)
                if old_instance.is_posted and old_instance != self:
                    raise ValidationError("Posted interest schedule records cannot be modified.")
            except InterestSchedule.DoesNotExist:
                pass  # New record, no validation needed
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        period_display = f"Period {self.period_number}" if self.period_type == 'monthly' else "Daily"
        return f"{self.loan_card.card_number} - {period_display} - ${self.effective_amount}"
    
    class Meta:
        ordering = ['loan_card', 'charge_date', 'period_number']
        unique_together = ['loan_card', 'period_type', 'period_number']
