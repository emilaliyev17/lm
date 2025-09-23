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
7. **loan_extensions** - Loan period extensions with fees (NEW)

### Critical Relationships
- LoanCard → Borrower (many-to-one)
- LoanCard → SettlementCharge (one-to-many)
- LoanCard → Draw (one-to-many)
- LoanCard → LoanExtension (one-to-many) ← NEW
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

## RECENT UPDATES & ENHANCEMENTS

### Loan Extensions System (September 2024)
- **New Model**: `LoanExtension` added to track loan period extensions
- **Database Migration**: `0002_loanextension.py` created
- **Key Features**:
  - Extension period (months)
  - Extension fee tracking
  - Optional interest rate changes
  - Automatic date tracking
  - Total extension fees calculation

### Enhanced Loan Detail Template (`loan_detail.html`)

#### 1. Loan Extensions Section
- **Location**: Added between Funding Information and action buttons
- **Conditional Display**: Only shows if `loan.extensions.exists`
- **Features**:
  - Extension numbering with `{{ forloop.counter }}`
  - Period display in months
  - Fee formatting with currency and commas
  - Interest rate handling (shows "No" if no interest)
  - Creation date display
  - **Total Extension Fees** summary row

#### 2. Template Tag Improvements
- **Interest Rate Calculation**: Replaced `{{ extension.interest_rate|mul:100|floatformat:1 }}%` with `{% widthratio extension.interest_rate 1 100 %}%`
- **Reason**: Better Django compatibility, avoids custom filter dependencies

#### 3. Checkpoint Validation Display
- **Simplified Interface**: Removed technical reference "J14 + J22 - J13 = J23"
- **Clean Display**: Now shows only the actual calculation with values
- **User-Friendly**: Less confusing for non-technical users

#### 4. Date Format Standardization
- **Consistent Format**: Changed all date displays from `|date:"M d, Y"` to `|date:"n/j/y"`
- **Compact Display**: Dates now show as "1/1/25" instead of "Jan 01, 2025"
- **Applied To**: Funded dates, draw dates, and extension creation dates

#### 5. Enhanced Funding Information Table
- **New Column**: Added interest rate column to Funding Information table
- **Advanced Loan Rate**: Shows `loan.initial_interest_rate` with widthratio
- **Draw-Specific Rates**: Each additional draw shows its own interest rate
- **Consistent Formatting**: All rates display as percentages using widthratio template tag

### Template Structure Updates

#### Enhanced Funding Information Table
```html
<!-- loan_detail.html - Updated Funding Table with Interest Rates -->
<table>
    <tr>
        <td><strong>Draw #0 (Advanced Loan)</strong></td>
        <td style="text-align: right;">${{ loan.advanced_loan_amount|floatformat:2|intcomma }}</td>
        <td style="text-align: right;">{{ loan.first_loan_date|date:"n/j/y" }}</td>
        <td style="text-align: right;">{% widthratio loan.initial_interest_rate 1 100 %}%</td>
    </tr>
    {% for draw in loan.additional_draws.all %}
    <tr>
        <td><strong>Draw #{{ draw.draw_number|add:"-1" }}</strong></td>
        <td style="text-align: right;">${{ draw.amount|floatformat:2|intcomma }}</td>
        <td style="text-align: right;">{{ draw.draw_date|date:"n/j/y" }}</td>
        <td style="text-align: right;">{% widthratio draw.interest_rate 1 100 %}%</td>
    </tr>
    {% endfor %}
    <tr style="border-top: 2px solid #ddd; font-weight: bold;">
        <td>Total Funded</td>
        <td style="text-align: right;">${{ total_funded|floatformat:2|intcomma }}</td>
        <td colspan="2"></td>
    </tr>
</table>
```

#### Loan Extensions Section
```html
<!-- loan_detail.html - New Extension Section -->
{% if loan.extensions.exists %}
<div class="detail-card" style="margin-top: 2rem;">
    <h3>Loan Extensions</h3>
    <table>
        <tr>
            <th>Extension</th>
            <th>Period</th>
            <th>Fee</th>
            <th>Interest</th>
            <th>Date Added</th>
        </tr>
        {% for extension in loan.extensions.all %}
        <tr>
            <td>Extension #{{ forloop.counter }}</td>
            <td>{{ extension.extension_months }} months</td>
            <td>${{ extension.extension_fee|floatformat:2|intcomma }}</td>
            <td>{% if extension.has_interest %}{% widthratio extension.interest_rate 1 100 %}%{% else %}No{% endif %}</td>
            <td>{{ extension.created_date|date:"n/j/y" }}</td>
        </tr>
        {% endfor %}
        <tr style="font-weight: bold; border-top: 2px solid #ddd;">
            <td colspan="2">Total Extension Fees</td>
            <td>${{ loan.get_total_extension_fees|floatformat:2|intcomma }}</td>
            <td colspan="2"></td>
        </tr>
    </table>
</div>
{% endif %}
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
/api/loans/<card_number>/add-extension/  # Add loan extension (NEW)
/api/borrowers/                # Borrower list
/api/borrowers/create/         # Create borrower
/admin/                        # Django admin panel
```

## VIEW FUNCTIONS
- **loan_list** - Dashboard with all loans
- **loan_detail** - Specific loan details with extensions display
- **create_loan** - Form with checkpoint validation
- **add_draw** - Additional funding after creation
- **add_extension** - Extend loan period with fees (NEW)
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
- [ ] Add loan extension and verify display on detail page (NEW)
- [ ] Test extension interest rate calculation with widthratio (NEW)
- [ ] Verify total extension fees calculation (NEW)
- [ ] Check conditional display of extensions section (NEW)

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
**Last Updated**: September 23, 2025  
**Version**: 1.2.0 - Enhanced UI with compact dates and funding table interest rates
