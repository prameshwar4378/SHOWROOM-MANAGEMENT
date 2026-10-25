from django.contrib import admin
from .models import ExpenseCategory, Expense


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'icon', 'color', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code', 'description')
    prepopulated_fields = {'code': ('name',)}


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        'expense_number',
        'expense_date',
        'category',
        'title',
        'amount',
        'payment_mode',
        'payee_name',
        'recorded_by',
        'created_at',
    )
    list_filter = ('payment_mode', 'category', 'expense_date')
    search_fields = (
        'expense_number',
        'title',
        'payee_name',
        'payment_reference',
        'notes',
    )
    date_hierarchy = 'expense_date'
    readonly_fields = ('expense_number', 'created_at', 'updated_at')
