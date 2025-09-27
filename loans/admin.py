from django.contrib import admin
from django.utils.html import format_html
from decimal import Decimal
from .models import Borrower, LoanCard, SettlementChargeType, SettlementCharge, Draw, InterestPayment


class SettlementChargeInline(admin.TabularInline):
    model = SettlementCharge
    extra = 0
    fields = ['charge_type', 'amount', 'invoice_number', 'notes']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "charge_type":
            kwargs["queryset"] = SettlementChargeType.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class DrawInline(admin.TabularInline):
    model = Draw
    extra = 0
    fields = ['draw_number', 'draw_date', 'amount', 'interest_rate', 'invoice_number']


class InterestPaymentInline(admin.TabularInline):
    model = InterestPayment
    extra = 0
    fields = ['period_number', 'charge_date', 'amount', 'received_date', 'invoice_number']


@admin.register(Borrower)
class BorrowerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'loan_count', 'created_at']
    search_fields = ['name', 'email', 'phone']
    list_filter = ['created_at']
    
    def loan_count(self, obj):
        return obj.loan_cards.count()
    loan_count.short_description = 'Active Loans'


@admin.register(SettlementChargeType)
class SettlementChargeTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'display_order', 'is_active', 'is_required', 'default_amount']
    list_editable = ['display_order', 'is_active', 'is_required', 'default_amount']
    ordering = ['display_order']


@admin.register(LoanCard)
class LoanCardAdmin(admin.ModelAdmin):
    list_display = ['card_number', 'borrower', 'advanced_loan_amount', 
                    'first_wired_amount', 'total_settlement_charges', 
                    'checkpoint_status', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['card_number', 'borrower__name']
    readonly_fields = ['checkpoint_display', 'total_funded_display', 
                      'monthly_interest_display', 'created_at', 'updated_at']
    
    inlines = [SettlementChargeInline, DrawInline, InterestPaymentInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('card_number', 'borrower', 'property_address', 'status')
        }),
        ('Loan Amounts', {
            'fields': ('advanced_loan_amount', 'first_wired_amount', 
                      'total_settlement_charges', 'initial_interest_rate')
        }),
        ('Dates', {
            'fields': ('first_loan_date', 'maturity_date')
        }),
        ('Calculated Values', {
            'fields': ('checkpoint_display', 'total_funded_display', 
                      'monthly_interest_display'),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def checkpoint_status(self, obj):
        checkpoint = obj.calculate_checkpoint()
        if abs(checkpoint) < Decimal('0.01'):
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ ${}</span>',
                '{:,.2f}'.format(checkpoint)
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ ${}</span>',
                '{:,.2f}'.format(checkpoint)
            )
    checkpoint_status.short_description = 'Checkpoint'
    
    def checkpoint_display(self, obj):
        checkpoint = obj.calculate_checkpoint()
        color = 'green' if abs(checkpoint) < Decimal('0.01') else 'red'
        return format_html(
            '<div style="padding: 10px; background: #f0f0f0; border-radius: 5px;">'
            '<strong>Checkpoint Formula (J23):</strong><br>'
            'First Wired (${}) + Settlement (${}) - Advanced Loan (${}) = '
            '<span style="color: {}; font-weight: bold;">${}</span>'
            '</div>',
            '{:,.2f}'.format(obj.first_wired_amount),
            '{:,.2f}'.format(obj.total_settlement_charges),
            '{:,.2f}'.format(obj.advanced_loan_amount),
            color,
            '{:,.2f}'.format(checkpoint)
        )
    checkpoint_display.short_description = 'Checkpoint Validation'
    
    def total_funded_display(self, obj):
        return f"${obj.get_total_funded_amount():,.2f}"
    total_funded_display.short_description = 'Total Funded (with draws)'
    
    def monthly_interest_display(self, obj):
        return f"${obj.get_monthly_interest_for_initial():,.2f}"
    monthly_interest_display.short_description = 'Monthly Interest (initial)'


@admin.register(Draw)
class DrawAdmin(admin.ModelAdmin):
    list_display = ['loan_card', 'draw_number', 'draw_date', 'amount', 
                    'interest_rate', 'monthly_interest']
    list_filter = ['draw_date']
    search_fields = ['loan_card__card_number', 'invoice_number']


@admin.register(InterestPayment) 
class InterestPaymentAdmin(admin.ModelAdmin):
    list_display = ['loan_card', 'period_number', 'charge_date', 
                    'amount', 'received_date', 'payment_status']
    list_filter = ['charge_date', 'received_date']
    search_fields = ['loan_card__card_number', 'invoice_number']
    
    def payment_status(self, obj):
        if obj.is_paid:
            return format_html('<span style="color: green;">✓ Paid</span>')
        return format_html('<span style="color: orange;">⏳ Pending</span>')
    payment_status.short_description = 'Status'
