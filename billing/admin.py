"""
Admin configuration for billing app.
"""
from django.contrib import admin
from .models import (
    Bill, BillItem, MarginMoneyDetail, DeliveryChallanDetail,
    Product, TractorStockUnit, PurchaseBill, PurchaseBillItem
)


class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 1


class MarginMoneyDetailInline(admin.StackedInline):
    model = MarginMoneyDetail
    can_delete = False
    max_num = 1


class DeliveryChallanDetailInline(admin.StackedInline):
    model = DeliveryChallanDetail
    can_delete = False
    max_num = 1


class PurchaseBillItemInline(admin.TabularInline):
    model = PurchaseBillItem
    extra = 1


@admin.register(PurchaseBill)
class PurchaseBillAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'supplier_name', 'invoice_date', 'total_amount', 'created_at']
    search_fields = ['invoice_number', 'supplier_name', 'supplier_gstin']
    list_filter = ['invoice_date']
    inlines = [PurchaseBillItemInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'hsn_code', 'default_price', 'stock_quantity', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'hsn_code']


@admin.register(TractorStockUnit)
class TractorStockUnitAdmin(admin.ModelAdmin):
    list_display = ['chassis_number', 'engine_number', 'product', 'status', 'purchase_date']
    list_filter = ['status', 'product__category']
    search_fields = ['chassis_number', 'engine_number', 'product__name']


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['bill_number', 'bill_type', 'customer', 'bill_date', 'grand_total', 'is_gst_bill', 'status', 'created_at']
    list_filter = ['bill_type', 'status', 'is_gst_bill', 'bill_date']
    search_fields = ['bill_number', 'customer__full_name', 'customer__mobile_primary']
    inlines = [BillItemInline, MarginMoneyDetailInline, DeliveryChallanDetailInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.calculate_totals(save=True)
