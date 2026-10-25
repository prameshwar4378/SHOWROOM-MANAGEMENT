"""
Views for the settings_app of Tractor Showroom Management System.

Class-based views for managing CompanyProfile singleton, BankDetail records,
GSTConfig tax configurations, and BillNumberSequence counters.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    UpdateView,
    CreateView,
    DeleteView,
)

from django.db.models import Q, Count
from .models import (
    CompanyProfile,
    BankDetail,
    GSTConfig,
    BillNumberSequence,
    NotificationConfig,
    NotificationLog,
)
from .forms import (
    CompanyProfileForm,
    BankDetailForm,
    GSTConfigForm,
    BillNumberSequenceForm,
    NotificationConfigForm,
)
from .notification_service import send_notification, normalize_indian_mobile


class SettingsAccessRequiredMixin(UserPassesTestMixin):
    """Restricts access to settings configurations to Administrators and Managers."""
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return hasattr(user, 'profile') and (user.profile.is_admin or user.profile.is_manager)

    def handle_no_permission(self):
        messages.error(self.request, "Access restricted. Administrator or Manager privileges are required to configure settings.")
        return redirect('accounts:profile')


class CompanyProfileView(LoginRequiredMixin, SettingsAccessRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    View to edit the showroom CompanyProfile singleton.
    If no record exists, get_object retrieves or creates one automatically.
    """
    model = CompanyProfile
    form_class = CompanyProfileForm
    template_name = 'settings_app/company_profile.html'
    success_url = reverse_lazy('settings_app:company_profile')
    success_message = "Company Profile updated successfully."

    def get_object(self, queryset=None):
        """Always retrieve the singleton instance."""
        return CompanyProfile.get_instance()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'profile'
        context['page_title'] = 'Company Profile'
        context['page_subtitle'] = 'Manage showroom contact details, branding logos, and legal declarations'
        return context


# ============================================================================
# Bank Detail Views
# ============================================================================

class BankDetailListView(LoginRequiredMixin, SettingsAccessRequiredMixin, ListView):
    """Lists all configured bank accounts for the showroom."""
    model = BankDetail
    template_name = 'settings_app/bank_list.html'
    context_object_name = 'banks'

    def get_queryset(self):
        company = CompanyProfile.get_instance()
        return BankDetail.objects.filter(company=company).order_by('-is_primary', 'bank_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'bank'
        context['page_title'] = 'Bank Details'
        context['page_subtitle'] = 'Manage company bank accounts displayed on customer invoices'
        return context


class BankDetailCreateView(LoginRequiredMixin, SettingsAccessRequiredMixin, SuccessMessageMixin, CreateView):
    """Adds a new bank account linked to the showroom company profile."""
    model = BankDetail
    form_class = BankDetailForm
    template_name = 'settings_app/bank_form.html'
    success_url = reverse_lazy('settings_app:bank_list')
    success_message = "Bank account '%(bank_name)s' added successfully."

    def form_valid(self, form):
        form.instance.company = CompanyProfile.get_instance()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'bank'
        context['page_title'] = 'Add Bank Account'
        context['page_subtitle'] = 'Provide bank, account, and IFSC details'
        context['is_edit'] = False
        return context


class BankDetailUpdateView(LoginRequiredMixin, SettingsAccessRequiredMixin, SuccessMessageMixin, UpdateView):
    """Edits an existing bank account."""
    model = BankDetail
    form_class = BankDetailForm
    template_name = 'settings_app/bank_form.html'
    success_url = reverse_lazy('settings_app:bank_list')
    success_message = "Bank account '%(bank_name)s' updated successfully."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'bank'
        context['page_title'] = 'Edit Bank Account'
        context['page_subtitle'] = f"Updating details for {self.object.bank_name}"
        context['is_edit'] = True
        return context


class BankDetailDeleteView(LoginRequiredMixin, SettingsAccessRequiredMixin, DeleteView):
    """Deletes a bank account with confirmation."""
    model = BankDetail
    template_name = 'settings_app/bank_confirm_delete.html'
    success_url = reverse_lazy('settings_app:bank_list')

    def form_valid(self, form):
        bank_name = self.object.bank_name
        response = super().form_valid(form)
        messages.success(self.request, f"Bank account '{bank_name}' was deleted successfully.")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'bank'
        context['page_title'] = 'Delete Bank Account'
        context['page_subtitle'] = 'Confirm removal of this bank record'
        return context


# ============================================================================
# GST Config Views
# ============================================================================

class GSTConfigListView(LoginRequiredMixin, SettingsAccessRequiredMixin, ListView):
    """Lists all configured GST tax rates."""
    model = GSTConfig
    template_name = 'settings_app/gst_list.html'
    context_object_name = 'gst_configs'

    def get_queryset(self):
        return GSTConfig.objects.all().order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'gst'
        context['active_count'] = GSTConfig.objects.filter(is_active=True).count()
        context['page_title'] = 'GST Configuration'
        context['page_subtitle'] = 'Manage CGST, SGST, IGST tax slabs and HSN codes'
        return context


class GSTConfigCreateView(LoginRequiredMixin, SettingsAccessRequiredMixin, SuccessMessageMixin, CreateView):
    """Adds a new GST tax slab."""
    model = GSTConfig
    form_class = GSTConfigForm
    template_name = 'settings_app/gst_form.html'
    success_url = reverse_lazy('settings_app:gst_list')
    success_message = "GST configuration '%(name)s' added successfully."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'gst'
        context['page_title'] = 'Add GST Configuration'
        context['page_subtitle'] = 'Create a new tax slab for tractors, parts, or implements'
        context['is_edit'] = False
        return context


class GSTConfigUpdateView(LoginRequiredMixin, SettingsAccessRequiredMixin, SuccessMessageMixin, UpdateView):
    """Edits an existing GST tax slab."""
    model = GSTConfig
    form_class = GSTConfigForm
    template_name = 'settings_app/gst_form.html'
    success_url = reverse_lazy('settings_app:gst_list')
    success_message = "GST configuration '%(name)s' updated successfully."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'gst'
        context['page_title'] = 'Edit GST Configuration'
        context['page_subtitle'] = f"Updating {self.object.name}"
        context['is_edit'] = True
        return context


# ============================================================================
# Bill Number Sequence Views
# ============================================================================

class BillSequenceListView(LoginRequiredMixin, SettingsAccessRequiredMixin, ListView):
    """Lists all bill numbering sequences, auto-seeding defaults if empty."""
    model = BillNumberSequence
    template_name = 'settings_app/sequence_list.html'
    context_object_name = 'sequences'

    def get_queryset(self):
        current_fy = BillNumberSequence.calculate_financial_year()
        # Seed default sequences if they do not exist for the current financial year
        defaults = [
            ('QUOTATION', 'QT-'),
            ('TAX_INVOICE', 'TI-'),
            ('MARGIN_MONEY', 'MM-'),
            ('DELIVERY_CHALLAN', 'DC-'),
        ]
        if BillNumberSequence.objects.filter(financial_year=current_fy).count() < 4:
            for b_type, pfx in defaults:
                BillNumberSequence.objects.get_or_create(
                    bill_type=b_type,
                    financial_year=current_fy,
                    defaults={'prefix': pfx, 'last_number': 0}
                )
        return BillNumberSequence.objects.all().order_by('bill_type', '-financial_year')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'sequence'
        context['current_fy'] = BillNumberSequence.calculate_financial_year()
        context['page_title'] = 'Bill Sequences'
        context['page_subtitle'] = 'Manage prefix and counters for Quotation, Invoice, Challan, and Margin Money'
        return context


class BillSequenceUpdateView(LoginRequiredMixin, SettingsAccessRequiredMixin, SuccessMessageMixin, UpdateView):
    """Edits a bill number sequence configuration."""
    model = BillNumberSequence
    form_class = BillNumberSequenceForm
    template_name = 'settings_app/sequence_form.html'
    success_url = reverse_lazy('settings_app:sequence_list')
    success_message = "Bill sequence for '%(bill_type)s' updated successfully."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'sequence'
        context['page_title'] = 'Edit Bill Sequence'
        context['page_subtitle'] = f"Configure sequence for {self.object.get_bill_type_display()} ({self.object.financial_year})"
        return context


# ============================================================================
# WhatsApp & SMS Notification Views
# ============================================================================

class NotificationSettingsView(LoginRequiredMixin, SettingsAccessRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Manage WhatsApp & SMS gateway configuration, credentials, and automation switches.
    Also provides a direct 'Send Test Notification' feature to verify gateway health.
    """
    model = NotificationConfig
    form_class = NotificationConfigForm
    template_name = 'settings_app/notification_settings.html'
    success_url = reverse_lazy('settings_app:notification_settings')
    success_message = "Notification settings saved successfully."

    def get_object(self, queryset=None):
        return NotificationConfig.get_instance()

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if 'action_test_send' in request.POST:
            test_recipient = request.POST.get('test_recipient', '').strip()
            clean_recipient = normalize_indian_mobile(test_recipient)
            if not clean_recipient:
                messages.error(request, "Please enter a valid 10-digit Indian mobile number for the test alert.")
                return redirect('settings_app:notification_settings')

            # Ensure current configuration is saved first if submitted
            form = self.get_form()
            if form.is_valid():
                self.object = form.save()
            config = self.object

            test_message = (
                f"Showroom Alert Test:\n"
                f"Automated notification gateway is operating normally.\n"
                f"Provider: {config.get_provider_display()}"
            )
            log = send_notification(
                recipient=clean_recipient,
                message=test_message,
                notification_type='CUSTOM',
                user=request.user,
                entity_id='SYSTEM_TEST'
            )
            if log.status == 'SENT':
                messages.success(request, f"Test notification sent to {clean_recipient} successfully via {log.provider}!")
            elif log.status == 'SIMULATED':
                messages.info(request, f"Test notification simulated for {clean_recipient} (Simulator mode active; check Notification Logs).")
            else:
                messages.error(request, f"Test notification delivery failed: {log.error_message}")
            return redirect('settings_app:notification_settings')

        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'notifications'
        context['page_title'] = 'Notification Settings'
        context['page_subtitle'] = 'Configure WhatsApp & SMS gateway, automation triggers, and test credentials'
        context['recent_logs'] = NotificationLog.objects.select_related('sent_by').order_by('-created_at')[:8]
        return context


class NotificationLogListView(LoginRequiredMixin, SettingsAccessRequiredMixin, ListView):
    """
    Audit log of all SMS / WhatsApp messages dispatched to customers.
    """
    model = NotificationLog
    template_name = 'settings_app/notification_logs.html'
    context_object_name = 'logs'
    paginate_by = 25

    def get_queryset(self):
        qs = NotificationLog.objects.select_related('sent_by').order_by('-created_at')
        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip().upper()
        msg_type = self.request.GET.get('type', '').strip().upper()

        if q:
            qs = qs.filter(
                Q(recipient_mobile__icontains=q) |
                Q(recipient_name__icontains=q) |
                Q(entity_id__icontains=q) |
                Q(message_text__icontains=q)
            )
        if status in ('SENT', 'FAILED', 'SIMULATED'):
            qs = qs.filter(status=status)
        if msg_type in dict(NotificationLog.MESSAGE_TYPE_CHOICES):
            qs = qs.filter(message_type=msg_type)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'notification_logs'
        context['page_title'] = 'Notification Audit Trail'
        context['page_subtitle'] = 'Comprehensive log of all automated customer SMS and WhatsApp notifications'

        kpi = NotificationLog.objects.aggregate(
            total=Count('id'),
            sent=Count('id', filter=Q(status='SENT')),
            failed=Count('id', filter=Q(status='FAILED')),
            simulated=Count('id', filter=Q(status='SIMULATED')),
        )
        context['total_count'] = kpi['total'] or 0
        context['sent_count'] = kpi['sent'] or 0
        context['failed_count'] = kpi['failed'] or 0
        context['simulated_count'] = kpi['simulated'] or 0
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['current_status'] = self.request.GET.get('status', '').strip().upper()
        context['current_type'] = self.request.GET.get('type', '').strip().upper()
        context['type_choices'] = NotificationLog.MESSAGE_TYPE_CHOICES
        return context

