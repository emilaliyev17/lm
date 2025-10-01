# Generated migration for invoice search indexes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loans', '0013_interestschedule_payment_source'),
    ]

    operations = [
        # Index for LoanCard.advanced_loan_invoice
        migrations.AddIndex(
            model_name='loancard',
            index=models.Index(
                fields=['advanced_loan_invoice'],
                name='idx_loancard_invoice',
                condition=models.Q(advanced_loan_invoice__isnull=False)
            ),
        ),
        
        # Index for SettlementCharge.invoice_number
        migrations.AddIndex(
            model_name='settlementcharge',
            index=models.Index(
                fields=['invoice_number'],
                name='idx_settlement_invoice',
                condition=models.Q(invoice_number__isnull=False)
            ),
        ),
        
        # Index for Draw.invoice_number
        migrations.AddIndex(
            model_name='draw',
            index=models.Index(
                fields=['invoice_number'],
                name='idx_draw_invoice',
                condition=models.Q(invoice_number__isnull=False)
            ),
        ),
        
        # Index for InterestSchedule.invoice_number (only posted records)
        migrations.AddIndex(
            model_name='interestschedule',
            index=models.Index(
                fields=['invoice_number'],
                name='idx_intschedule_invoice',
                condition=models.Q(invoice_number__isnull=False, is_posted=True)
            ),
        ),
        
        # Index for InterestPayment.invoice_number (legacy)
        migrations.AddIndex(
            model_name='interestpayment',
            index=models.Index(
                fields=['invoice_number'],
                name='idx_intpayment_invoice',
                condition=models.Q(invoice_number__isnull=False)
            ),
        ),
    ]

