"""
Admin registration for accounts application.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    """Inline administration for UserProfile attached to standard User."""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Showroom Profile'
    fk_name = 'user'
    extra = 0


class CustomUserAdmin(BaseUserAdmin):
    """Custom User admin showing showroom profile inline."""
    inlines = [UserProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'get_role', 'is_active', 'is_staff']
    list_filter = ['is_active', 'is_staff', 'profile__role']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile')

    @admin.display(description='Role')
    def get_role(self, instance):
        """Retrieve user role display."""
        if hasattr(instance, 'profile'):
            return instance.profile.get_role_display()
        return '-'


# Re-register UserAdmin with the inline profile
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile model."""
    list_display = ['user', 'role', 'mobile_number', 'created_at']
    list_filter = ['role', 'created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    search_fields = [
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
        'mobile_number',
        'address',
    ]
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('User Association', {
            'fields': ('user',)
        }),
        ('Role & Access', {
            'fields': ('role',)
        }),
        ('Contact Information', {
            'fields': ('mobile_number', 'address')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
