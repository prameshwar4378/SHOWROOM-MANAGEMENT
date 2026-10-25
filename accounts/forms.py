"""
Forms for accounts application.
Provides login, profile management, user creation, update, and password change forms.
"""

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm as BasePasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from .models import UserProfile


class LoginForm(forms.Form):
    """
    Authentication form with customized Tailwind CSS styling.
    """
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 placeholder-gray-400 text-sm transition duration-150 ease-in-out bg-white shadow-sm',
            'placeholder': 'Enter your username',
            'autocomplete': 'username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-gray-900 placeholder-gray-400 text-sm transition duration-150 ease-in-out bg-white shadow-sm',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded cursor-pointer',
        })
    )

    def __init__(self, *args, request=None, **kwargs):
        """Initialize form with optional request parameter."""
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        """Validate credentials against Django authentication backend."""
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    "Invalid username or password. Please check your credentials and try again."
                )
            if not self.user_cache.is_active:
                raise forms.ValidationError(
                    "This account has been deactivated. Please contact the showroom administrator."
                )
        return cleaned_data

    def get_user(self):
        """Return the authenticated user."""
        return self.user_cache


class UserProfileForm(forms.ModelForm):
    """
    Form for users to edit their own profile details.
    Includes User basic fields (first_name, last_name, email)
    and UserProfile fields (mobile_number, address).
    """
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
            'placeholder': 'First Name',
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
            'placeholder': 'Last Name',
        })
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
            'placeholder': 'email@example.com',
        })
    )

    class Meta:
        model = UserProfile
        fields = ['role', 'mobile_number', 'address']
        widgets = {
            'role': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
            }),
            'mobile_number': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
                'placeholder': 'e.g. +91 9876543210',
            }),
            'address': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
                'rows': 3,
                'placeholder': 'Enter street address, city, state, pin code',
            }),
        }

    def __init__(self, *args, allow_role_edit=False, **kwargs):
        """
        Populate user fields from attached User and restrict role editing
        if not authorized.
        """
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_id:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

        if not allow_role_edit:
            self.fields['role'].disabled = True
            self.fields['role'].help_text = "Role changes can only be made by a showroom Admin."

    def save(self, commit=True):
        """Save both User and UserProfile models."""
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.email = self.cleaned_data.get('email', '')
        if commit:
            user.save()
            profile.save()
        return profile


class UserCreateForm(forms.ModelForm):
    """
    Form for showroom administrator to create new staff or manager users.
    Includes username, email, first_name, last_name, password, and role.
    """
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        initial=UserProfile.ROLE_STAFF,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
        })
    )
    mobile_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
            'placeholder': 'e.g. +91 9876543210',
        })
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
            'rows': 3,
            'placeholder': 'Enter residential or office address',
        })
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
            'placeholder': 'Enter at least 8 characters',
        }),
        help_text='Must be at least 8 characters long.'
    )
    confirm_password = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
            'placeholder': 'Confirm your password',
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
                'placeholder': 'e.g. john_doe',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
                'placeholder': 'user@showroom.com',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
                'placeholder': 'First name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
                'placeholder': 'Last name',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded',
            }),
        }

    def clean_username(self):
        """Validate that username is unique."""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean(self):
        """Validate passwords match and meet standard security requirements."""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                self.add_error('confirm_password', "Passwords do not match.")
            else:
                try:
                    validate_password(password, user=self.instance)
                except forms.ValidationError as e:
                    self.add_error('password', e)
        return cleaned_data

    def save(self, commit=True):
        """Create new User and set up corresponding UserProfile atomically."""
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        user.set_password(password)

        role = self.cleaned_data.get('role', UserProfile.ROLE_STAFF)
        user.is_staff = (role == UserProfile.ROLE_ADMIN) or getattr(user, 'is_superuser', False)

        if commit:
            with transaction.atomic():
                user.save()
                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.role = role
                profile.mobile_number = self.cleaned_data.get('mobile_number', '')
                profile.address = self.cleaned_data.get('address', '')
                profile.save()
        return user


class UserUpdateForm(forms.ModelForm):
    """
    Form for showroom administrator to update an existing user's details and role.
    """
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
        })
    )
    mobile_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
            'placeholder': 'e.g. +91 9876543210',
        })
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
            'rows': 3,
            'placeholder': 'Enter residential or office address',
        })
    )
    new_password = forms.CharField(
        label='Reset Password (optional)',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
            'placeholder': 'Leave blank to keep existing password',
        }),
        help_text='Leave blank to keep current password.'
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded',
            }),
        }

    def __init__(self, *args, **kwargs):
        """Pre-populate role, mobile_number, and address from profile."""
        super().__init__(*args, **kwargs)
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['role'].initial = self.instance.profile.role
            self.fields['mobile_number'].initial = self.instance.profile.mobile_number
            self.fields['address'].initial = self.instance.profile.address

    def clean_username(self):
        """Validate username uniqueness excluding current user."""
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def clean_new_password(self):
        """Validate password with Django validators if provided."""
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            validate_password(new_password, user=self.instance)
        return new_password

    def save(self, commit=True):
        """Update User and attached UserProfile atomically."""
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            user.set_password(new_password)

        role = self.cleaned_data.get('role', UserProfile.ROLE_STAFF)
        user.is_staff = (role == UserProfile.ROLE_ADMIN) or getattr(user, 'is_superuser', False)

        if commit:
            with transaction.atomic():
                user.save()
                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.role = role
                profile.mobile_number = self.cleaned_data.get('mobile_number', '')
                profile.address = self.cleaned_data.get('address', '')
                profile.save()
        return user


class PasswordChangeForm(BasePasswordChangeForm):
    """
    Subclass of Django's PasswordChangeForm with customized Tailwind styling.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm text-gray-800 bg-white',
            })
