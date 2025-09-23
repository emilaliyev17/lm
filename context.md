# LOAN MANAGEMENT SYSTEM - COMPLETE TECHNICAL CONTEXT

## CRITICAL BUSINESS LOGIC - MUST UNDERSTAND

### Checkpoint Formula (J23) - NEVER CHANGE THIS
Checkpoint = First Wired Amount + Settlement Charges - Advanced Loan Amount = 0
- **Advanced Loan Amount**: Total debt borrower signs for
- **First Wired Amount**: Actual money transferred to borrower
- **Settlement Charges**: Fees we pay but add to borrower's debt
- **MUST EQUAL ZERO** for valid loan

### Total Funded Amount Formula - CORRECTED VERSION
Total Funded = Advanced Loan Amount + Additional Draws
NOT First Wired + Additional Draws (common mistake!)

### Interest Rate Storage
- Stored as decimal (0.13 = 13%)
- NEVER change database values
- Only multiply by 100 for display in UI

## PROJECT STRUCTURE
```
loan-management-system/
├── backend/
│   ├── loan_system/          # Django project settings
│   ├── loans/                # Main app
│   │   ├── models.py         # Core business logic
│   │   ├── views.py          # View functions
│   │   ├── admin.py          # Django admin config
│   │   └── urls.py           # URL routing
│   ├── templates/            # HTML templates
│   │   ├── base.html         # Base template
│   │   └── loans/            # App templates
│   └── manage.py
├── docker-compose.yml        # PostgreSQL container
└── frontend/                 # Reserved for React (not implemented)
```

## DATABASE SCHEMA

### Core Tables
1. **borrowers** - Borrower information
2. **loan_cards** - Main loan records (checkpoint validation here)
3. **settlement_charge_types** - Configurable charge types
4. **settlement_charges** - Individual charges per loan
5. **draws** - Additional funding after loan creation
6. **interest_payments** - Payment tracking

### Critical Relationships
- LoanCard → Borrower (many-to-one)
- LoanCard → SettlementCharge (one-to-many)
- LoanCard → Draw (one-to-many)
- SettlementCharge → SettlementChargeType (many-to-one)

## TECHNICAL STACK

- **Backend**: Django 5.2.6 + Django REST Framework
- **Database**: PostgreSQL 15 (Docker)
- **Frontend**: HTML/CSS/JavaScript (simple templates)
- **Python**: 3.13.7

## CRITICAL CODE SECTIONS - DO NOT MODIFY

### models.py - LoanCard.calculate_checkpoint()
```python
def calculate_checkpoint(self):
    checkpoint = self.first_wired_amount + self.total_settlement_charges - self.advanced_loan_amount
    return checkpoint
```

### models.py - LoanCard.get_total_funded_amount()
```python
def get_total_funded_amount(self):
    additional_draws_total = self.additional_draws.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    return self.advanced_loan_amount + additional_draws_total  # NOT first_wired_amount!
```

## COMMON MISTAKES TO AVOID

### 1. Interest Rate Display
- **WRONG**: Changing database to store as 13 instead of 0.13
- **RIGHT**: Keep as 0.13 in DB, multiply by 100 only in view/template

### 2. Total Funded Calculation
- **WRONG**: First Wired + Additional Draws
- **RIGHT**: Advanced Loan + Additional Draws

### 3. Checkpoint Formula
- **WRONG**: Any other formula
- **RIGHT**: First Wired + Settlement - Advanced Loan = 0

### 4. Settlement Charges
- **WRONG**: Allowing edit after loan creation
- **RIGHT**: One-time setup, no edits (would break checkpoint)

### 5. Draw Numbering
- **WRONG**: Starting from 1
- **RIGHT**: Starting from 2 (First Wired is implied Draw #1)

## URL STRUCTURE
```
/api/loans/                    # Loan list dashboard
/api/loans/create/             # Create new loan
/api/loans/<card_number>/      # Loan detail view
/api/loans/<card_number>/add-draw/  # Add additional draw
/api/borrowers/                # Borrower list
/api/borrowers/create/         # Create borrower
/admin/                        # Django admin panel
```

## VIEW FUNCTIONS
- **loan_list** - Dashboard with all loans
- **loan_detail** - Specific loan details
- **create_loan** - Form with checkpoint validation
- **add_draw** - Additional funding after creation
- **borrower_list** - All borrowers
- **create_borrower** - New borrower form

## FRONTEND VALIDATION

### Checkpoint Real-time Validation (create_loan.html)
- Calculates on every input change
- Blocks submit if checkpoint ≠ 0
- Visual feedback (red/green border)

## DEPLOYMENT CONSIDERATIONS

### Environment Variables (.env)
```
DEBUG=False  # Change for production
SECRET_KEY=<generate-new-key>
DATABASE_NAME=loandb
DATABASE_USER=postgres
DATABASE_PASSWORD=<secure-password>
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

### Static Files
- Run `python manage.py collectstatic` for production
- Configure nginx/apache to serve static files

### Security
- Add ALLOWED_HOSTS for production domain
- Enable HTTPS
- Use environment variables for secrets
- Regular backups of PostgreSQL

## TESTING CHECKLIST
- [ ] Create loan with valid checkpoint (= 0)
- [ ] Try creating loan with invalid checkpoint (≠ 0)
- [ ] Add additional draw to existing loan
- [ ] Verify Total Funded updates correctly
- [ ] Check interest rate displays as percentage
- [ ] Ensure Settlement Charges can't be edited

## KNOWN LIMITATIONS
- No user authentication system (uses Django admin)
- No Excel import/export (planned feature)
- No interest payment automation
- No email notifications
- No audit trail/history tracking

## FUTURE ENHANCEMENTS (DO NOT IMPLEMENT WITHOUT DISCUSSION)
- React frontend to replace templates
- Excel import for 200+ existing loans
- Automated interest calculations
- Payment tracking system
- Document attachments
- Email notifications

## CRITICAL WARNINGS
⚠️ **NEVER** modify checkpoint formula  
⚠️ **NEVER** change interest rate storage format in DB  
⚠️ **NEVER** allow Settlement Charges editing after creation  
⚠️ **NEVER** change Draw numbering logic  
⚠️ **ALWAYS** validate checkpoint before saving loan  

## SUPPORT INFORMATION
- **Original Developer**: Emil Aliyev
- **Repository**: https://github.com/emilaliyev17/lm
- **Critical Business Logic Expert**: Emil (consult before ANY formula changes)

## FOR NEW DEVELOPERS
After reading this document, you should understand:
- The checkpoint formula and why it's critical
- How Total Funded is calculated
- Why Settlement Charges can't be edited
- The correct interest rate display approach
- All common pitfalls to avoid

If you have questions after reading this, **DO NOT PROCEED**. Consult with the team first.

---
**Last Updated**: September 2024  
**Version**: 1.0.0
