"""
Accounts models for Tractor Showroom Management System.
Defines UserProfile extending standard Django User with roles and contact information.
"""

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """
    Profile model extending standard Django User.
    Stores showroom staff role, mobile number, and address.
    """
    ROLE_ADMIN = 'ADMIN'
    ROLE_MANAGER = 'MANAGER'
    ROLE_STAFF = 'STAFF'

    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_MANAGER, 'Manager'),
        (ROLE_STAFF, 'Staff'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='User'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_STAFF,
        verbose_name='Role',
        help_text='Defines access level across the showroom management system.'
    )
    mobile_number = models.CharField(
        max_length=15,
        blank=True,
        verbose_name='Mobile Number',
        help_text='Contact phone number for communication.'
    )
    address = models.TextField(
        blank=True,
        verbose_name='Address',
        help_text='Residential or mailing address.'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']

    def __str__(self):
        """String representation of user profile."""
        full_name = self.user.get_full_name()
        display_name = full_name if full_name else self.user.username
        return f"{display_name} ({self.get_role_display()})"

    @property
    def is_admin(self):
        """Check if user has Admin role or superuser permissions."""
        return self.role == self.ROLE_ADMIN or self.user.is_superuser

    @property
    def is_manager(self):
        """Check if user has Manager role or higher."""
        return self.role in [self.ROLE_ADMIN, self.ROLE_MANAGER] or self.user.is_superuser

    @property
    def is_staff_member(self):
        """Check if user is showroom staff."""
        return self.role in [self.ROLE_ADMIN, self.ROLE_MANAGER, self.ROLE_STAFF]

    @property
    def role_badge_color(self):
        """Tailwind CSS badge color classes based on role."""
        if self.role == self.ROLE_ADMIN:
            return 'bg-purple-100 text-purple-800 border-purple-200'
        elif self.role == self.ROLE_MANAGER:
            return 'bg-blue-100 text-blue-800 border-blue-200'
        return 'bg-emerald-100 text-emerald-800 border-emerald-200'


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    """
    Signal receiver to automatically create or ensure UserProfile exists
    when a User instance is created or saved.
    """
    if kwargs.get('raw', False):
        return

    if created:
        UserProfile.objects.get_or_create(user=instance)
    else:
        # Ensure profile exists for existing users (e.g. superusers created via CLI)
        if not hasattr(instance, 'profile'):
            UserProfile.objects.get_or_create(user=instance)
