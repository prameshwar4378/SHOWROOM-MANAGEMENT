"""
URL patterns for the payments application.
"""
from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('', views.PaymentListView.as_view(), name='payment_list'),
    path('add/', views.PaymentCreateView.as_view(), name='payment_add'),
    path('<int:pk>/', views.PaymentDetailView.as_view(), name='payment_detail'),
    path('<int:pk>/delete/', views.PaymentDeleteView.as_view(), name='payment_delete'),
    path('<int:pk>/allocate/', views.PaymentAllocationCreateView.as_view(), name='payment_allocate'),
    path('allocation/<int:pk>/delete/', views.PaymentAllocationDeleteView.as_view(), name='allocation_delete'),
    path('pending/', views.PendingPaymentsView.as_view(), name='pending_payments'),
    path('ledger/<int:pk>/', views.CustomerLedgerView.as_view(), name='customer_ledger'),
    path('<int:pk>/pdf/', views.PaymentPDFView.as_view(), name='payment_pdf'),
    # WhatsApp / SMS Notification Endpoints
    path('<int:pk>/send-notification/', views.PaymentSendNotificationView.as_view(), name='payment_send_notification'),
    path('reminder/<int:customer_id>/', views.CustomerSendReminderView.as_view(), name='customer_send_reminder'),
    path('batch-reminders/', views.BatchSendRemindersView.as_view(), name='batch_send_reminders'),
]

