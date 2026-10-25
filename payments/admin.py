"""
Admin configuration for payments app.
"""
from django.contrib import admin
from .models import Payment, PaymentAllocation


class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 0


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'customer', 'amount', 'payment_date', 'payment_mode', 'purpose', 'received_by']
    list_filter = ['payment_mode', 'purpose', 'payment_date']
    search_fields = ['receipt_number', 'customer__full_name', 'reference_number', 'cheque_number']
    inlines = [PaymentAllocationInline]


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = ['payment', 'bill', 'allocated_amount', 'allocated_date', 'allocated_by']
    search_fields = ['payment__receipt_number', 'bill__bill_number']
