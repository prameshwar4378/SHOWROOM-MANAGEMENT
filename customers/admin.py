from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """
    Admin configuration for Customer model with rich filtering, search,
    and financial summary display.
    """
    list_display = [
        'full_name',
        'mobile_primary',
        'village',
        'taluka',
        'district',
        'is_active',
        'created_at',
    ]
    list_filter = [
        'is_active',
        'district',
        'taluka',
        'created_at',
    ]
    search_fields = [
        'full_name',
        'mobile_primary',
        'mobile_secondary',
        'village',
        'taluka',
        'district',
        'aadhar_number',
        'pan_number',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'total_billed_display',
        'total_paid_display',
        'outstanding_balance_display',
        'unallocated_balance_display',
    ]
    list_per_page = 25
    actions = ['activate_customers', 'deactivate_customers']

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ['created_at', 'updated_at']
        return self.readonly_fields

    fieldsets = (
        ('Personal Information', {
            'fields': (
                'full_name',
                'father_name',
                'mobile_primary',
                'mobile_secondary',
                'email',
            )
        }),
        ('Address Information', {
            'fields': (
                'village',
                'taluka',
                'district',
                'state',
                'pin_code',
            )
        }),
        ('Identification & Documents', {
            'fields': (
                'aadhar_number',
                'pan_number',
                'reference_by',
            )
        }),
        ('Banking Details', {
            'fields': (
                'bank_name',
                'bank_branch',
            )
        }),
        ('Account Status & Financial Summary', {
            'fields': (
                'is_active',
                'total_billed_display',
                'total_paid_display',
                'outstanding_balance_display',
                'unallocated_balance_display',
                'notes',
                'created_at',
                'updated_at',
            )
        }),
    )

    @admin.display(description='Total Billed (₹)')
    def total_billed_display(self, obj):
        return f"₹ {obj.total_billed:,.2f}"

    @admin.display(description='Total Paid (₹)')
    def total_paid_display(self, obj):
        return f"₹ {obj.total_paid:,.2f}"

    @admin.display(description='Outstanding Balance (₹)')
    def outstanding_balance_display(self, obj):
        return f"₹ {obj.outstanding_balance:,.2f}"

    @admin.display(description='Unallocated Balance (₹)')
    def unallocated_balance_display(self, obj):
        return f"₹ {obj.unallocated_balance:,.2f}"

    @admin.action(description="Mark selected customers as Active")
    def activate_customers(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} customer(s) marked as active.")

    @admin.action(description="Mark selected customers as Inactive (Soft Delete)")
    def deactivate_customers(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} customer(s) marked as inactive.")
