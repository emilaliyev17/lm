from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import Sum, Count
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from decimal import Decimal, InvalidOperation
from datetime import datetime, date, timedelta
import calendar
from .models import LoanCard, Borrower, SettlementChargeType, SettlementCharge, Draw, InterestSchedule

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
            'advanced_loan_invoice': loan.advanced_loan_invoice,
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
            'advanced_loan_invoice': loan.advanced_loan_invoice,
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
            'notes': charge.notes or '',
            'invoice_number': charge.invoice_number
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
        'advanced_loan_invoice': loan.advanced_loan_invoice,
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


@login_required
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

        advanced_invoice = (request.POST.get('advanced_loan_invoice', '') or '').strip()

        # Calculate settlement charges total
        settlement_total = Decimal('0')
        charge_types = list(SettlementChargeType.objects.filter(is_active=True))
        charges_to_create = []
        
        for charge_type in charge_types:
            amount = request.POST.get(f'charge_{charge_type.id}', '0')
            invoice_number = (request.POST.get(f'charge_{charge_type.id}_invoice', '') or '').strip()
            try:
                amount_decimal = Decimal(amount) if amount else Decimal('0')
                if amount_decimal > 0:
                    settlement_total += amount_decimal
                    charges_to_create.append((charge_type, amount_decimal, invoice_number))
            except (InvalidOperation, TypeError):
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
                advanced_loan_invoice=advanced_invoice or None,
                first_wired_amount=first_wired,
                total_settlement_charges=settlement_total,  # Set it directly
                first_loan_date=request.POST.get('first_loan_date'),
                initial_interest_rate=Decimal('0.13'),
                status='active'
            )
            
            # Create individual settlement charges
            for charge_type, amount, invoice_number in charges_to_create:
                SettlementCharge.objects.create(
                    loan_card=loan,
                    charge_type=charge_type,
                    amount=amount,
                    invoice_number=invoice_number or None
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
        'charge_types': SettlementChargeType.objects.filter(is_active=True),
    }
    return render(request, 'loans/create_loan.html', context)


@login_required
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

@login_required
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

@login_required
def add_extension(request, card_number):
    loan = get_object_or_404(LoanCard, card_number=card_number)
    
    if request.method == 'POST':
        try:
            from .models import LoanExtension
            extension = LoanExtension.objects.create(
                loan_card=loan,
                extension_months=int(request.POST.get('extension_months', 0)),
                extension_fee=Decimal(request.POST.get('extension_fee', '0')),
                has_interest=request.POST.get('has_interest') == 'yes',
                interest_rate=Decimal(request.POST.get('interest_rate', '0.13')) if request.POST.get('has_interest') == 'yes' else None,
                reason=request.POST.get('reason', '')
            )
            return redirect('loan_detail', card_number=card_number)
        except Exception as e:
            context = {
                'loan': loan,
                'error': str(e)
            }
            return render(request, 'loans/add_extension.html', context)
    
    context = {
        'loan': loan,
        'existing_extensions': loan.extensions.all()
    }
    return render(request, 'loans/add_extension.html', context)


@login_required
def interest_schedule(request, card_number):
    """Display and manage interest payment schedule"""
    loan = get_object_or_404(LoanCard, card_number=card_number)
    
    # Get or create interest schedules
    schedules = loan.interest_schedules.all().order_by('charge_date')
    
    context = {
        'loan': loan,
        'schedules': schedules,
    }
    return render(request, 'loans/interest_schedule.html', context)


def add_months(source_date, months):
    """Add months to a date, handling month overflow correctly"""
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@login_required
def generate_interest_schedule(request, card_number):
    """Generate monthly interest payment schedule for a loan"""
    loan = get_object_or_404(LoanCard, card_number=card_number)
    
    if request.method == 'POST':
        try:
            # Calculate the end date (maturity + extensions)
            end_date = loan.maturity_date
            if end_date is None:
                # If no maturity date set, default to 12 months from first loan date
                end_date = add_months(loan.first_loan_date, 12)
            
            # Add extension months to end date
            total_extension_months = loan.extensions.aggregate(
                total=Sum('extension_months')
            )['total'] or 0
            
            if total_extension_months > 0:
                end_date = add_months(end_date, total_extension_months)
            
            # Generate monthly schedule from first loan date to end date
            current_date = loan.first_loan_date.replace(day=1)  # Start from first of the month
            period_number = 1
            created_count = 0
            
            while current_date <= end_date:
                # Check if this period already exists and is posted
                existing_schedule = loan.interest_schedules.filter(
                    period_type='monthly',
                    period_number=period_number
                ).first()
                
                if existing_schedule and existing_schedule.is_posted:
                    # Skip posted records
                    current_date = add_months(current_date, 1)
                    period_number += 1
                    continue
                
                # Calculate total monthly interest
                # Base interest from advanced loan amount
                monthly_interest = (loan.advanced_loan_amount * loan.initial_interest_rate) / 12
                
                # Add interest from all draws that are active by this date
                for draw in loan.additional_draws.all():
                    if draw.draw_date <= current_date:
                        monthly_interest += (draw.amount * draw.interest_rate) / 12
                
                # Create or update the schedule record
                if existing_schedule and not existing_schedule.is_posted:
                    # Update existing unpposted record
                    existing_schedule.charge_date = current_date
                    existing_schedule.calculated_amount = monthly_interest
                    existing_schedule.save()
                else:
                    # Create new record
                    InterestSchedule.objects.create(
                        loan_card=loan,
                        period_number=period_number,
                        period_type='monthly',
                        charge_date=current_date,
                        calculated_amount=monthly_interest,
                        is_posted=False
                    )
                    created_count += 1
                
                current_date = add_months(current_date, 1)
                period_number += 1
            
            if created_count > 0:
                messages.success(request, f'Generated {created_count} new interest schedule periods.')
            else:
                messages.info(request, 'Interest schedule already exists or all periods are posted.')
                
        except Exception as e:
            messages.error(request, f'Error generating interest schedule: {str(e)}')
    
    return redirect('interest_schedule', card_number=card_number)


@login_required
@csrf_exempt
def post_interest_schedule(request):
    """Handle posting of interest schedule records"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            
            schedule_id = data.get('schedule_id')
            received_date = data.get('received_date')
            invoice_number = data.get('invoice_number')
            adjusted_amount = data.get('adjusted_amount')
            
            if not schedule_id:
                return JsonResponse({'success': False, 'error': 'Schedule ID is required'})
            
            # Get the schedule record
            schedule = get_object_or_404(InterestSchedule, id=schedule_id)
            
            # Check if already posted
            if schedule.is_posted:
                return JsonResponse({'success': False, 'error': 'This schedule is already posted'})
            
            # Update the schedule
            if received_date:
                try:
                    schedule.received_date = datetime.strptime(received_date, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Invalid date format'})
            
            if invoice_number:
                schedule.invoice_number = invoice_number
            
            if adjusted_amount:
                try:
                    schedule.adjusted_amount = Decimal(str(adjusted_amount))
                except (ValueError, TypeError):
                    return JsonResponse({'success': False, 'error': 'Invalid amount'})
            
            # Mark as posted
            schedule.is_posted = True
            schedule.posted_at = timezone.now()
            schedule.posted_by = 'Admin'  # You might want to use request.user.username if you have authentication
            schedule.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Schedule period {schedule.period_number} posted successfully'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Only POST method allowed'})


@login_required
@require_POST
def update_charge_date(request, schedule_id):
    schedule = get_object_or_404(InterestSchedule, id=schedule_id)

    if not schedule.is_posted:
        new_date = request.POST.get('charge_date')
        if new_date:
            schedule.charge_date = new_date
            schedule.save()
            return JsonResponse({'success': True})

    return JsonResponse({'success': False})


@login_required
def edit_loan_invoices(request, card_number):
    loan = get_object_or_404(LoanCard, card_number=card_number)
    
    if request.method == 'POST':
        # Update advanced loan invoice
        loan.advanced_loan_invoice = request.POST.get('advanced_loan_invoice', '').strip() or None
        loan.save()
        
        # Update settlement charges invoices
        for charge in loan.settlement_charges.all():
            invoice_num = request.POST.get(f'charge_{charge.id}_invoice', '').strip() or None
            charge.invoice_number = invoice_num
            charge.save()
        
        messages.success(request, 'Invoice numbers updated successfully')
        return redirect('loan_detail', card_number=card_number)
    
    # GET request - show form
    context = {
        'loan': loan,
        'settlement_charges': loan.settlement_charges.all()
    }
    return render(request, 'loans/edit_invoices.html', context)
