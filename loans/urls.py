from django.urls import path
from . import views

urlpatterns = [
    path('loans/', views.loan_list, name='loan_list'),
    path('borrowers/', views.borrower_list, name='borrower_list'),
    path('borrowers/create/', views.create_borrower, name='create_borrower'),
    path('loans/create/', views.create_loan, name='create_loan'),
    path('loans/<str:card_number>/add-draw/', views.add_draw, name='add_draw'),
    path('loans/<str:card_number>/add-extension/', views.add_extension, name='add_extension'),
    path('loans/<str:card_number>/interest-schedule/', views.interest_schedule, name='interest_schedule'),
    path('loans/<str:card_number>/generate-schedule/', views.generate_interest_schedule, name='generate_interest_schedule'),
    path('post-interest-schedule/', views.post_interest_schedule, name='post_interest_schedule'),
    path('loans/<str:card_number>/', views.loan_detail, name='loan_detail'),
    path('api/loans/', views.api_loans, name='api_loans'),
    path('api/loan/<str:card_number>/', views.api_loan_detail, name='api_loan_detail'),
]
