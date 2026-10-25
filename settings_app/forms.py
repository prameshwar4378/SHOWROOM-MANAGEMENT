"""
Forms for the settings_app of Tractor Showroom Management System.

Includes ModelForms for CompanyProfile, BankDetail, GSTConfig, and BillNumberSequence.
Styled with Tailwind CSS compatible widgets and field validation.
"""

import re
from decimal import Decimal
from django import forms
from .models import CompanyProfile, BankDetail, GSTConfig, BillNumberSequence, NotificationConfig


TAILWIND_INPUT_CLASSES = (
    "w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm text-slate-800 "
    "placeholder-slate-400 bg-white shadow-2xs hover:border-slate-400 focus:border-blue-600 focus:outline-none focus:ring-4 focus:ring-blue-100/60 transition duration-150"
)

TAILWIND_TEXTAREA_CLASSES = (
    "w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm text-slate-800 "
    "placeholder-slate-400 bg-white shadow-2xs hover:border-slate-400 focus:border-blue-600 focus:outline-none focus:ring-4 focus:ring-blue-100/60 transition duration-150"
)

TAILWIND_SELECT_CLASSES = (
    "w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm text-slate-800 "
    "bg-white shadow-2xs hover:border-slate-400 focus:border-blue-600 focus:outline-none focus:ring-4 focus:ring-blue-100/60 transition duration-150 cursor-pointer"
)

TAILWIND_CHECKBOX_CLASSES = (
    "h-4 w-4 rounded-md border-slate-300 text-blue-600 focus:ring-blue-500 transition"
)

TAILWIND_FILE_CLASSES = (
    "block w-full text-sm text-slate-500 "
    "file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 "
    "file:text-xs file:font-bold file:bg-blue-50 file:text-blue-700 "
    "hover:file:bg-blue-100 cursor-pointer transition"
)


class CompanyProfileForm(forms.ModelForm):
    """Form for updating company showroom details and branding assets."""

    class Meta:
        model = CompanyProfile
        fields = [
            'company_name',
            'tagline',
            'company_logo',
            'brand_logo',
            'address_line1',
            'address_line2',
            'city',
            'taluka',
            'district',
            'state',
            'pin_code',
            'mobile_numbers',
            'email',
            'gstin_number',
            'pan_number',
            'declaration_text',
            'footer_text',
            'signature_image',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'e.g. Captain Tractor Showroom'
            }),
            'tagline': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'e.g. Authorized Sales, Spares & Service'
            }),
            'company_logo': forms.FileInput(attrs={
                'class': TAILWIND_FILE_CLASSES,
                'accept': 'image/*'
            }),
            'brand_logo': forms.FileInput(attrs={
                'class': TAILWIND_FILE_CLASSES,
                'accept': 'image/*'
            }),
            'address_line1': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'Building / Shop No. / Street'
            }),
            'address_line2': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'Area / Landmark / Near Market Yard'
            }),
            'city': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'City / Town'
            }),
            'taluka': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'Taluka'
            }),
            'district': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'District'
            }),
            'state': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'State'
            }),
            'pin_code': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': '6-digit PIN Code'
            }),
            'mobile_numbers': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': '9876543210, 9123456780'
            }),
            'email': forms.EmailInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'showroom@example.com'
            }),
            'gstin_number': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': '27AAAAA0000A1Z5'
            }),
            'pan_number': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'AAAAA0000A'
            }),
            'declaration_text': forms.Textarea(attrs={
                'class': TAILWIND_TEXTAREA_CLASSES,
                'rows': 3,
                'placeholder': 'Legal declaration printed on tax invoices...'
            }),
            'footer_text': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'This is Computer Generated Print'
            }),
            'signature_image': forms.FileInput(attrs={
                'class': TAILWIND_FILE_CLASSES,
                'accept': 'image/*'
            }),
        }

    def clean_gstin_number(self):
        gstin = self.cleaned_data.get('gstin_number', '').strip().upper()
        if gstin:
            if not re.match(r'^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', gstin):
                raise forms.ValidationError("Enter a valid 15-character GSTIN (e.g. 27AAAAA0000A1Z5).")
        return gstin

    def clean_pan_number(self):
        pan = self.cleaned_data.get('pan_number', '').strip().upper()
        if pan:
            if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan):
                raise forms.ValidationError("Enter a valid 10-character PAN (e.g. ABCDE1234F).")
        return pan

    def clean_pin_code(self):
        pin = self.cleaned_data.get('pin_code', '').strip()
        if pin and (len(pin) != 6 or not pin.isdigit()):
            raise forms.ValidationError("PIN code must be a 6-digit numeric value.")
        return pin


class BankDetailForm(forms.ModelForm):
    """Form for adding and editing bank accounts. Company is automatically set in view."""

    class Meta:
        model = BankDetail
        exclude = ['company']
        widgets = {
            'bank_name': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'e.g. State Bank of India'
            }),
            'branch_name': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'e.g. Main Branch, Pune'
            }),
            'account_holder_name': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'Showroom account name'
            }),
            'account_number': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'e.g. 123456789012'
            }),
            'ifsc_code': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'e.g. SBIN0001234'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': TAILWIND_CHECKBOX_CLASSES
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': TAILWIND_CHECKBOX_CLASSES
            }),
        }

    def clean_ifsc_code(self):
        ifsc = self.cleaned_data.get('ifsc_code', '').strip().upper()
        if ifsc:
            if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', ifsc):
                raise forms.ValidationError("Enter a valid 11-character IFSC code (e.g. SBIN0001234).")
        return ifsc

    def clean_account_number(self):
        acc = self.cleaned_data.get('account_number', '').strip()
        if acc and not re.match(r'^[0-9A-Za-z]+$', acc):
            raise forms.ValidationError("Account number should contain valid alphanumeric characters only.")
        return acc


class GSTConfigForm(forms.ModelForm):
    """Form for adding and editing GST tax configurations."""

    class Meta:
        model = GSTConfig
        fields = ['name', 'hsn_code', 'cgst_rate', 'sgst_rate', 'igst_rate', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'e.g. GST 12% (Tractor), GST 18% (Spares)'
            }),
            'hsn_code': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'e.g. 8701 (Tractors) or 8432 (Implements)'
            }),
            'cgst_rate': forms.NumberInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': 'e.g. 6.00'
            }),
            'sgst_rate': forms.NumberInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': 'e.g. 6.00'
            }),
            'igst_rate': forms.NumberInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'step': '0.01',
                'min': '0',
                'max': '100',
                'placeholder': 'e.g. 12.00'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': TAILWIND_CHECKBOX_CLASSES
            }),
        }

    def clean_cgst_rate(self):
        val = self.cleaned_data.get('cgst_rate')
        if val is not None and (val < Decimal('0') or val > Decimal('100')):
            raise forms.ValidationError("CGST rate must be between 0% and 100%.")
        return val

    def clean_sgst_rate(self):
        val = self.cleaned_data.get('sgst_rate')
        if val is not None and (val < Decimal('0') or val > Decimal('100')):
            raise forms.ValidationError("SGST rate must be between 0% and 100%.")
        return val

    def clean_igst_rate(self):
        val = self.cleaned_data.get('igst_rate')
        if val is not None and (val < Decimal('0') or val > Decimal('100')):
            raise forms.ValidationError("IGST rate must be between 0% and 100%.")
        return val


class BillNumberSequenceForm(forms.ModelForm):
    """Form for editing bill sequence prefixes, financial year, and counters."""

    class Meta:
        model = BillNumberSequence
        fields = ['bill_type', 'prefix', 'last_number', 'financial_year']
        widgets = {
            'bill_type': forms.Select(attrs={
                'class': TAILWIND_SELECT_CLASSES,
            }),
            'prefix': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'e.g. TI-, QT-, MM-, DC-'
            }),
            'last_number': forms.NumberInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'min': '0',
                'placeholder': 'e.g. 0'
            }),
            'financial_year': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'e.g. 2026-27'
            }),
        }

    def clean_prefix(self):
        prefix = self.cleaned_data.get('prefix', '').strip().upper()
        if not prefix:
            raise forms.ValidationError("Prefix cannot be empty.")
        return prefix

    def clean_financial_year(self):
        fy = self.cleaned_data.get('financial_year', '').strip()
        if fy and not re.match(r'^\d{4}-\d{2}$', fy):
            raise forms.ValidationError("Financial Year must be in format YYYY-YY (e.g. 2026-27).")
        return fy

    def clean_last_number(self):
        last_num = self.cleaned_data.get('last_number')
        if last_num is not None and self.instance and self.instance.pk:
            from billing.models import Bill
            prefix = self.cleaned_data.get('prefix') or self.instance.prefix
            existing_count = Bill.objects.filter(
                bill_type=self.instance.bill_type,
                bill_number__startswith=prefix
            ).count()
            if last_num < existing_count:
                raise forms.ValidationError(
                    f"Counter cannot be decreased to {last_num}. At least {existing_count} bills have already been issued with prefix '{prefix}'."
                )
        return last_num


class NotificationConfigForm(forms.ModelForm):
    """Form for configuring WhatsApp & SMS notification gateways and automation switches."""

    class Meta:
        model = NotificationConfig
        fields = [
            'is_enabled',
            'provider',
            'api_endpoint',
            'api_key_or_token',
            'sender_phone_id',
            'auto_send_payment_receipt',
            'auto_send_invoice_alert',
            'auto_send_booking_alert',
        ]
        widgets = {
            'is_enabled': forms.CheckboxInput(attrs={'class': TAILWIND_CHECKBOX_CLASSES}),
            'provider': forms.Select(attrs={'class': TAILWIND_SELECT_CLASSES}),
            'api_endpoint': forms.URLInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'e.g. https://graph.facebook.com/v19.0 or https://api.ultramsg.com'
            }),
            'api_key_or_token': forms.PasswordInput(render_value=True, attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'Paste Bearer Token or API Secret Key'
            }),
            'sender_phone_id': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASSES,
                'placeholder': 'e.g. Meta Phone Number ID (105928374...) or Instance ID'
            }),
            'auto_send_payment_receipt': forms.CheckboxInput(attrs={'class': TAILWIND_CHECKBOX_CLASSES}),
            'auto_send_invoice_alert': forms.CheckboxInput(attrs={'class': TAILWIND_CHECKBOX_CLASSES}),
            'auto_send_booking_alert': forms.CheckboxInput(attrs={'class': TAILWIND_CHECKBOX_CLASSES}),
        }

