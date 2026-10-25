from django.contrib import admin
from .models import (
    CompanyProfile, BankDetail, GSTConfig, BillNumberSequence,
    NotificationConfig, NotificationLog
)


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'mobile_numbers', 'email', 'city', 'state', 'gstin_number']
    search_fields = ['company_name', 'mobile_numbers', 'email', 'gstin_number']


@admin.register(BankDetail)
class BankDetailAdmin(admin.ModelAdmin):
    list_display = ['bank_name', 'account_number', 'ifsc_code', 'branch_name', 'is_primary', 'is_active']
    list_filter = ['is_primary', 'is_active']
    search_fields = ['bank_name', 'account_number', 'ifsc_code', 'branch_name']


@admin.register(GSTConfig)
class GSTConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'hsn_code', 'cgst_rate', 'sgst_rate', 'igst_rate', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'hsn_code']


@admin.register(BillNumberSequence)
class BillNumberSequenceAdmin(admin.ModelAdmin):
    list_display = ['bill_type', 'prefix', 'last_number', 'financial_year']
    list_filter = ['bill_type', 'financial_year']
    search_fields = ['prefix', 'financial_year']


@admin.register(NotificationConfig)
class NotificationConfigAdmin(admin.ModelAdmin):
    list_display = ['provider', 'is_enabled', 'auto_send_payment_receipt', 'auto_send_invoice_alert', 'auto_send_booking_alert', 'updated_at']
    list_filter = ['is_enabled', 'provider']


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['message_type', 'recipient_name', 'recipient_mobile', 'status', 'created_at']
    list_filter = ['message_type', 'status', 'created_at']
    search_fields = ['recipient_name', 'recipient_mobile', 'message_text']
    readonly_fields = ['customer', 'recipient_name', 'recipient_mobile', 'message_type', 'message_text', 'status', 'response_payload', 'sent_by', 'created_at']


