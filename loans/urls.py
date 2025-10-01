from django.urls import path
from . import views

urlpatterns = [
    # ===== STATIC/SPECIFIC PATHS FIRST (no parameters) =====
    path('loans/', views.loan_list, name='loan_list'),
    path('loans/create/', views.create_loan, name='create_loan'),
    path('borrowers/', views.borrower_list, name='borrower_list'),
    path('borrowers/create/', views.create_borrower, name='create_borrower'),
    path('post-interest-schedule/', views.post_interest_schedule, name='post_interest_schedule'),
    
    # ===== API SEARCH ENDPOINT =====
    # Note: 'api/' prefix added by main urls.py, so these paths start without 'api/'
    path('loans/search/', views.search_loans, name='search_loans'),  # /api/loans/search/
    
    # ===== API DETAIL ENDPOINT =====
    path('loan/<str:card_number>/', views.api_loan_detail, name='api_loan_detail'),  # /api/loan/LC-001/
    
    # ===== INTEREST SCHEDULE PATHS WITH INT ID =====
    path('interest-schedule/<int:schedule_id>/update-date/', views.update_charge_date, name='update_charge_date'),
    path('interest-schedule/<int:schedule_id>/delete/', views.delete_interest_schedule, name='delete_interest_schedule'),
    
    # ===== LOAN CARD SPECIFIC ACTIONS (with card_number, but specific endpoints) =====
    path('loans/<str:card_number>/add-draw/', views.add_draw, name='add_draw'),
    path('loans/<str:card_number>/add-extension/', views.add_extension, name='add_extension'),
    path('loans/<str:card_number>/interest-schedule/', views.interest_schedule, name='interest_schedule'),
    path('loans/<str:card_number>/generate-schedule/', views.generate_interest_schedule, name='generate_interest_schedule'),
    path('loans/<str:card_number>/add-interest-invoice/', views.add_interest_invoice, name='add_interest_invoice'),
    path('loans/<str:card_number>/edit/', views.edit_loan_details, name='edit_loan_details'),
    path('loans/<str:card_number>/edit-invoices/', views.edit_loan_invoices, name='edit_loan_invoices'),
    path('loans/<str:card_number>/change-status/', views.change_loan_status, name='change_loan_status'),
    
    # ===== CATCH-ALL DYNAMIC PATHS LAST =====
    path('loans/<str:card_number>/', views.loan_detail, name='loan_detail'),  # MUST be LAST - catches everything else
]
