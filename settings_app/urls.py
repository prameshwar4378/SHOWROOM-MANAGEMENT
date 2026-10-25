"""
URL configuration for settings_app.

Defines routes for Company Profile, Bank Details, GST Configurations,
and Bill Number Sequences.
"""

from django.urls import path
from . import views

app_name = 'settings_app'

urlpatterns = [
    # Company Profile (Singleton)
    path('', views.CompanyProfileView.as_view(), name='company_profile'),

    # Bank Details
    path('bank/', views.BankDetailListView.as_view(), name='bank_list'),
    path('bank/add/', views.BankDetailCreateView.as_view(), name='bank_add'),
    path('bank/<int:pk>/edit/', views.BankDetailUpdateView.as_view(), name='bank_edit'),
    path('bank/<int:pk>/delete/', views.BankDetailDeleteView.as_view(), name='bank_delete'),

    # GST Configuration
    path('gst/', views.GSTConfigListView.as_view(), name='gst_list'),
    path('gst/add/', views.GSTConfigCreateView.as_view(), name='gst_add'),
    path('gst/<int:pk>/edit/', views.GSTConfigUpdateView.as_view(), name='gst_edit'),

    # Bill Sequences
    path('sequences/', views.BillSequenceListView.as_view(), name='sequence_list'),
    path('sequences/<int:pk>/edit/', views.BillSequenceUpdateView.as_view(), name='sequence_edit'),

    # WhatsApp & SMS Notifications
    path('notifications/', views.NotificationSettingsView.as_view(), name='notification_settings'),
    path('notifications/logs/', views.NotificationLogListView.as_view(), name='notification_logs'),
]

