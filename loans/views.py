from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Sum, Count
from decimal import Decimal
from .models import LoanCard, Borrower, SettlementChargeType, SettlementCharge, Draw

# Create your views here.

def loan_list(request):
    """Display list of all loans"""
    loans = LoanCard.objects.all()
    
    # Calculate statistics
    total_loans = loans.count()
    active_loans = loans.filter(status='active').count()
    total_portfolio = loans.aggregate(total=Sum('advanced_loan_amount'))['total'] or Decimal('0')
    
    # Format loan data for template
    loan_data = []
    for loan in loans:
        checkpoint = loan.calculate_checkpoint()
        loan_data.append({
            'card_number': loan.card_number,
            'borrower': loan.borrower.name,
            'advanced_loan': loan.advanced_loan_amount,
            'first_wired': loan.first_wired_amount,
            'settlement': loan.total_settlement_charges,
            'checkpoint': checkpoint,
            'checkpoint_valid': abs(checkpoint) < Decimal('0.01'),
            'status': loan.get_status_display(),
            'interest_rate_display': loan.initial_interest_rate * 100,
        })
    
    context = {
        'loans': loan_data,
        'total_loans': total_loans,
        'active_loans': active_loans,
        'total_portfolio': total_portfolio,
    }
    
    return render(request, 'loans/loan_list.html', context)

def loan_detail(request, card_number):
    """Display details for a specific loan"""
    loan = get_object_or_404(LoanCard, card_number=card_number)
    
    # Calculate additional context data
    total_funded = loan.get_total_funded_amount()
    checkpoint = loan.calculate_checkpoint()
    checkpoint_valid = abs(checkpoint) < Decimal('0.01')
    monthly_interest = loan.get_monthly_interest_for_initial()
    interest_rate_display = loan.initial_interest_rate * 100
    
    # Get related data
    settlement_charges = loan.settlement_charges.all()
    additional_draws = loan.additional_draws.all()
    
    context = {
        'loan': loan,
        'total_funded': total_funded,
        'checkpoint': checkpoint,
        'checkpoint_valid': checkpoint_valid,
        'monthly_interest': monthly_interest,
        'interest_rate_display': interest_rate_display,
        'settlement_charges': settlement_charges,
        'additional_draws': additional_draws,
    }
    
    return render(request, 'loans/loan_detail.html', context)

def api_loans(request):
    """API endpoint for loans list"""
    loans = LoanCard.objects.all()
    data = []
    
    for loan in loans:
        data.append({
            'card_number': loan.card_number,
            'borrower': loan.borrower.name,
            'advanced_loan_amount': str(loan.advanced_loan_amount),
            'first_wired_amount': str(loan.first_wired_amount),
            'total_settlement_charges': str(loan.total_settlement_charges),
            'status': loan.status,
            'checkpoint': str(loan.calculate_checkpoint()),
            'created_at': loan.created_at.isoformat(),
        })
    
    return JsonResponse({'loans': data})

def api_loan_detail(request, card_number):
    """API endpoint for loan details"""
    loan = get_object_or_404(LoanCard, card_number=card_number)
    
    # Get settlement charges
    settlement_charges = []
    for charge in loan.settlement_charges.all():
        settlement_charges.append({
            'charge_type': charge.charge_type.name,
            'amount': str(charge.amount),
            'notes': charge.notes or ''
        })
    
    # Get draws
    draws = []
    for draw in loan.additional_draws.all():
        draws.append({
            'draw_number': draw.draw_number,
            'draw_date': draw.draw_date.isoformat(),
            'amount': str(draw.amount),
            'interest_rate': str(draw.interest_rate),
            'monthly_interest': str(draw.monthly_interest)
        })
    
    # Get interest payments
    interest_payments = []
    for payment in loan.interest_payments.all():
        interest_payments.append({
            'period_number': payment.period_number,
            'charge_date': payment.charge_date.isoformat(),
            'amount': str(payment.amount),
            'received_date': payment.received_date.isoformat() if payment.received_date else None,
            'is_paid': payment.is_paid
        })
    
    data = {
        'card_number': loan.card_number,
        'borrower': {
            'name': loan.borrower.name,
            'email': loan.borrower.email,
            'phone': loan.borrower.phone,
        },
        'property_address': loan.property_address,
        'advanced_loan_amount': str(loan.advanced_loan_amount),
        'first_wired_amount': str(loan.first_wired_amount),
        'total_settlement_charges': str(loan.total_settlement_charges),
        'first_loan_date': loan.first_loan_date.isoformat(),
        'maturity_date': loan.maturity_date.isoformat() if loan.maturity_date else None,
        'initial_interest_rate': str(loan.initial_interest_rate),
        'status': loan.status,
        'checkpoint': str(loan.calculate_checkpoint()),
        'total_funded_amount': str(loan.get_total_funded_amount()),
        'monthly_interest_initial': str(loan.get_monthly_interest_for_initial()),
        'settlement_charges': settlement_charges,
        'draws': draws,
        'interest_payments': interest_payments,
        'created_at': loan.created_at.isoformat(),
        'updated_at': loan.updated_at.isoformat(),
    }
    
    return JsonResponse(data)


def create_loan(request):
    """Simple form to create new loan card"""
    if request.method == 'POST':
        # Parse amounts
        try:
            advanced = Decimal(request.POST.get('advanced_loan_amount', '0'))
            first_wired = Decimal(request.POST.get('first_wired_amount', '0'))
        except:
            advanced = Decimal('0')
            first_wired = Decimal('0')
        
        # Calculate settlement charges total
        settlement_total = Decimal('0')
        charge_types = SettlementChargeType.objects.filter(is_active=True)[:4]
        charges_to_create = []
        
        for charge_type in charge_types:
            amount = request.POST.get(f'charge_{charge_type.id}', '0')
            try:
                amount_decimal = Decimal(amount) if amount else Decimal('0')
                if amount_decimal > 0:
                    settlement_total += amount_decimal
                    charges_to_create.append((charge_type, amount_decimal))
            except:
                pass
        
        # Calculate checkpoint BEFORE creating anything
        checkpoint = first_wired + settlement_total - advanced
        
        if abs(checkpoint) < Decimal('0.01'):  # Valid checkpoint
            # Create loan with correct total_settlement_charges
            loan = LoanCard.objects.create(
                card_number=request.POST.get('card_number'),
                borrower_id=request.POST.get('borrower'),
                property_address=request.POST.get('property_address', ''),
                advanced_loan_amount=advanced,
                first_wired_amount=first_wired,
                total_settlement_charges=settlement_total,  # Set it directly
                first_loan_date=request.POST.get('first_loan_date'),
                initial_interest_rate=Decimal('0.13'),
                status='active'
            )
            
            # Create individual settlement charges
            for charge_type, amount in charges_to_create:
                SettlementCharge.objects.create(
                    loan_card=loan,
                    charge_type=charge_type,
                    amount=amount
                )
            
            # Double-check by updating totals
            loan.update_settlement_charges_total()
            
            return redirect('loan_detail', card_number=loan.card_number)
        else:
            # Invalid checkpoint - return form with error
            context = {
                'borrowers': Borrower.objects.all(),
                'charge_types': charge_types,
                'checkpoint_error': f'Checkpoint must equal 0. Current: ${checkpoint:.2f}',
                'form_data': request.POST,
                'checkpoint': checkpoint,
                'advanced': advanced,
                'first_wired': first_wired,
                'settlement_total': settlement_total
            }
            return render(request, 'loans/create_loan.html', context)
    
    # GET request - show empty form
    context = {
        'borrowers': Borrower.objects.all(),
        'charge_types': SettlementChargeType.objects.filter(is_active=True)[:4],
    }
    return render(request, 'loans/create_loan.html', context)


def add_draw(request, card_number):
    """Add additional draw to existing loan"""
    loan = get_object_or_404(LoanCard, card_number=card_number)
    
    if request.method == 'POST':
        # Get next draw number (starts from 2)
        last_draw = loan.additional_draws.order_by('-draw_number').first()
        next_draw_number = (last_draw.draw_number + 1) if last_draw else 2
        
        try:
            # Create the draw
            draw = Draw.objects.create(
                loan_card=loan,
                draw_number=next_draw_number,
                draw_date=request.POST.get('draw_date'),
                amount=Decimal(request.POST.get('amount', '0')),
                interest_rate=Decimal(request.POST.get('interest_rate', '0.13')),
                invoice_number=request.POST.get('invoice_number', ''),
                notes=request.POST.get('notes', '')
            )
            return redirect('loan_detail', card_number=card_number)
        except Exception as e:
            context = {
                'loan': loan,
                'error': str(e),
                'next_draw_number': next_draw_number,
                'total_funded_before': loan.get_total_funded_amount()
            }
            return render(request, 'loans/add_draw.html', context)
    
    # GET request
    last_draw = loan.additional_draws.order_by('-draw_number').first()
    next_draw_number = (last_draw.draw_number + 1) if last_draw else 2
    
    context = {
        'loan': loan,
        'next_draw_number': next_draw_number,
        'total_funded_before': loan.get_total_funded_amount(),
        'existing_draws': loan.additional_draws.all().order_by('draw_number')
    }
    return render(request, 'loans/add_draw.html', context)

def borrower_list(request):
    """Display all borrowers"""
    borrowers = Borrower.objects.all().annotate(
        loan_count=Count('loan_cards')
    ).order_by('name')
    
    context = {
        'borrowers': borrowers,
        'total_borrowers': borrowers.count(),
    }
    return render(request, 'loans/borrower_list.html', context)

def create_borrower(request):
    if request.method == 'POST':
        borrower = Borrower.objects.create(
            name=request.POST.get('name'),
            email=request.POST.get('email', ''),
            phone=request.POST.get('phone', ''),
            address=request.POST.get('address', '')
        )
        return redirect('borrower_list')
    return render(request, 'loans/create_borrower.html')