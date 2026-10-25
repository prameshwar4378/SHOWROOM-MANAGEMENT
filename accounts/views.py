"""
Views for accounts application.
Handles authentication, user profile management, and administrator user CRUD.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.auth.views import redirect_to_login
from django.db.models import Q
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView

from .forms import LoginForm, UserProfileForm, UserCreateForm, UserUpdateForm, PasswordChangeForm
from .models import UserProfile





class LoginView(View):
    """
    Custom branded login view for the Tractor Showroom Management System.
    """
    template_name = 'accounts/login.html'

    def get(self, request, *args, **kwargs):
        """Render login form if not authenticated, else redirect to dashboard."""
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        form = LoginForm(request=request)
        next_url = request.GET.get('next', '')
        return render(request, self.template_name, {
            'form': form,
            'next': next_url,
        })

    def post(self, request, *args, **kwargs):
        """Validate credentials and log in the user."""
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)

        form = LoginForm(data=request.POST, request=request)
        next_url = request.POST.get('next', '') or request.GET.get('next', '')

        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)

            # Handle "Remember me" session expiry
            if form.cleaned_data.get('remember_me'):
                request.session.set_expiry(1209600)  # 2 weeks
            else:
                request.session.set_expiry(0)  # expires on browser close

            # Ensure profile exists
            UserProfile.objects.get_or_create(user=user)

            display_name = user.get_full_name() or user.username
            messages.success(request, f"Welcome back, {display_name}!")

            # Security check for redirect URL
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect(settings.LOGIN_REDIRECT_URL)

        messages.error(request, "Authentication failed. Please verify your username and password.")
        return render(request, self.template_name, {
            'form': form,
            'next': next_url,
        })


class LogoutView(View):
    """
    Logout view that clears the session and redirects to the login screen.
    Supports both GET and POST requests.
    """
    def get(self, request, *args, **kwargs):
        return self._logout(request)

    def post(self, request, *args, **kwargs):
        return self._logout(request)

    def _logout(self, request):
        if request.user.is_authenticated:
            auth_logout(request)
            messages.info(request, "You have been successfully logged out.")
        return redirect('accounts:login')


class ProfileView(LoginRequiredMixin, View):
    """
    View and edit personal profile and change password.
    """
    template_name = 'accounts/profile.html'

    def get_profile(self, user):
        """Get or create user profile."""
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return profile

    def get(self, request, *args, **kwargs):
        """Display profile information and edit forms."""
        profile = self.get_profile(request.user)
        is_admin = request.user.is_superuser or profile.role == UserProfile.ROLE_ADMIN

        profile_form = UserProfileForm(instance=profile, allow_role_edit=is_admin)
        password_form = PasswordChangeForm(user=request.user)

        return render(request, self.template_name, {
            'profile': profile,
            'profile_form': profile_form,
            'password_form': password_form,
            'active_tab': request.GET.get('tab', 'profile'),
        })

    def post(self, request, *args, **kwargs):
        """Handle profile update or password change."""
        profile = self.get_profile(request.user)
        is_admin = request.user.is_superuser or profile.role == UserProfile.ROLE_ADMIN
        action = request.POST.get('action', 'update_profile')

        if action == 'change_password':
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            profile_form = UserProfileForm(instance=profile, allow_role_edit=is_admin)

            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Your password has been changed successfully.")
                return redirect(f"{reverse('accounts:profile')}?tab=security")
            else:
                messages.error(request, "Failed to update password. Please check the errors below.")
                return render(request, self.template_name, {
                    'profile': profile,
                    'profile_form': profile_form,
                    'password_form': password_form,
                    'active_tab': 'security',
                })

        else:  # update_profile
            profile_form = UserProfileForm(request.POST, instance=profile, allow_role_edit=is_admin)
            password_form = PasswordChangeForm(user=request.user)

            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Your profile details have been updated successfully.")
                return redirect(f"{reverse('accounts:profile')}?tab=profile")
            else:
                messages.error(request, "Failed to update profile. Please correct the errors below.")
                return render(request, self.template_name, {
                    'profile': profile,
                    'profile_form': profile_form,
                    'password_form': password_form,
                    'active_tab': 'profile',
                })


class AdminRequiredMixin(UserPassesTestMixin):
    """Restricts access to superusers and showroom admin role users."""
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return hasattr(user, 'profile') and user.profile.is_admin

    def handle_no_permission(self):
        messages.error(self.request, "Access restricted. Administrator privileges are required.")
        return redirect('accounts:profile')


class UserListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """
    Admin-only view listing showroom staff and management users.
    Supports filtering by search query, role, and active status.
    """
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 10

    def get_queryset(self):
        """Filter and search queryset."""
        qs = User.objects.select_related('profile').all().order_by('-date_joined')

        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(username__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(email__icontains=q) |
                Q(profile__mobile_number__icontains=q)
            )

        role = self.request.GET.get('role', '').strip()
        if role in [UserProfile.ROLE_ADMIN, UserProfile.ROLE_MANAGER, UserProfile.ROLE_STAFF]:
            qs = qs.filter(profile__role=role)

        status = self.request.GET.get('status', '').strip()
        if status == 'active':
            qs = qs.filter(is_active=True)
        elif status == 'inactive':
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        """Provide metrics and active filter values to template."""
        context = super().get_context_data(**kwargs)
        all_users = User.objects.select_related('profile')

        context['total_users'] = all_users.count()
        context['admin_count'] = all_users.filter(
            Q(profile__role=UserProfile.ROLE_ADMIN) | Q(is_superuser=True)
        ).distinct().count()
        context['manager_count'] = all_users.filter(profile__role=UserProfile.ROLE_MANAGER).count()
        context['staff_count'] = all_users.filter(profile__role=UserProfile.ROLE_STAFF).count()

        context['current_q'] = self.request.GET.get('q', '')
        context['current_role'] = self.request.GET.get('role', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['role_choices'] = UserProfile.ROLE_CHOICES
        return context


class UserCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """
    View to create a new showroom user account.
    """
    model = User
    form_class = UserCreateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Add New User'
        context['page_subtitle'] = 'Create a new user'
        context['form_title'] = 'Create System User'
        context['is_edit'] = False
        return context

    def form_valid(self, form):
        user = form.save()
        messages.success(
            self.request,
            f"User '{user.username}' was created successfully."
        )
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, "Failed to create user. Please check the form errors below.")
        return super().form_invalid(form)


class UserUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """
    Admin-only view to edit an existing user's details and showroom role.
    """
    model = User
    form_class = UserUpdateForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        target_user = self.get_object()
        context['page_title'] = f"Edit User: {target_user.username}"
        context['page_subtitle'] = f"Update permissions and profile details for {target_user.get_full_name() or target_user.username}"
        context['form_title'] = f"Edit User: {target_user.username}"
        context['is_edit'] = True
        context['target_user'] = target_user
        return context

    def form_valid(self, form):
        target_user = self.get_object()
        current_user = self.request.user
        is_active = form.cleaned_data.get('is_active')
        role = form.cleaned_data.get('role')

        if target_user == current_user and not is_active:
            form.add_error('is_active', "You cannot deactivate your own administrative account.")
            return self.form_invalid(form)

        if getattr(target_user, 'profile', None) and target_user.profile.is_admin and role != UserProfile.ROLE_ADMIN:
            active_admins = User.objects.filter(
                Q(profile__role=UserProfile.ROLE_ADMIN) | Q(is_superuser=True),
                is_active=True
            ).count()
            if active_admins <= 1:
                form.add_error('role', "Cannot demote the last remaining active administrator.")
                return self.form_invalid(form)

        user = form.save()
        messages.success(
            self.request,
            f"User '{user.username}' was updated successfully."
        )
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, "Failed to update user. Please check the form errors below.")
        return super().form_invalid(form)
