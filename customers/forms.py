import re
from django import forms
from .models import Customer


TAILWIND_INPUT_CLASS = (
    'w-full px-3.5 py-2.5 text-sm text-slate-800 bg-white border border-slate-300 '
    'rounded-xl shadow-2xs placeholder:text-slate-400 hover:border-slate-400 focus:outline-none '
    'focus:border-blue-600 focus:ring-4 focus:ring-blue-100/60 transition duration-150'
)

TAILWIND_TEXTAREA_CLASS = (
    'w-full px-3.5 py-2.5 text-sm text-slate-800 bg-white border border-slate-300 '
    'rounded-xl shadow-2xs placeholder:text-slate-400 hover:border-slate-400 focus:outline-none '
    'focus:border-blue-600 focus:ring-4 focus:ring-blue-100/60 transition duration-150'
)

TAILWIND_CHECKBOX_CLASS = (
    'h-4 w-4 text-blue-600 focus:ring-blue-500 border-slate-300 rounded-md transition'
)


class CustomerForm(forms.ModelForm):
    """
    Form for adding and updating showroom customers with grouped sections:
    Personal Information, Address Details, Documents, and Bank Information.
    """
    class Meta:
        model = Customer
        exclude = ['created_at', 'updated_at']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': 'Enter full name (e.g. Ramesh Shankar Patil)',
                'autocomplete': 'name',
            }),
            'father_name': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': "Enter father's or husband's name",
            }),
            'mobile_primary': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': '10-digit primary mobile number',
                'type': 'tel',
                'maxlength': '15',
            }),
            'mobile_secondary': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': 'Optional alternate mobile number',
                'type': 'tel',
                'maxlength': '15',
            }),
            'email': forms.EmailInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': 'customer@example.com',
            }),
            'village': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': 'Village or Town name (e.g. Shirwal)',
            }),
            'taluka': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': 'Taluka / Tehsil (e.g. Khandala)',
            }),
            'district': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': 'District (e.g. Satara)',
            }),
            'state': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': 'State (default: Maharashtra)',
            }),
            'pin_code': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': '6-digit PIN code',
                'maxlength': '10',
            }),
            'aadhar_number': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': '12-digit Aadhaar number (e.g. 1234 5678 9012)',
                'maxlength': '15',
            }),
            'pan_number': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': '10-character PAN (e.g. ABCDE1234F)',
                'maxlength': '15',
                'style': 'text-transform: uppercase;',
            }),
            'bank_name': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': 'Bank financing or primary bank (e.g. SBI, HDFC)',
            }),
            'bank_branch': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': 'Branch location (e.g. Shirwal Main Branch)',
            }),
            'reference_by': forms.TextInput(attrs={
                'class': TAILWIND_INPUT_CLASS,
                'placeholder': 'Name of referrer or sales agent',
            }),
            'notes': forms.Textarea(attrs={
                'class': TAILWIND_TEXTAREA_CLASS,
                'rows': 3,
                'placeholder': 'Enter any special notes, tractor preferences, or loan details...',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': TAILWIND_CHECKBOX_CLASS,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and self.instance.pk is None:
            self.fields['is_active'].initial = True

    def clean_is_active(self):
        return bool(self.cleaned_data.get('is_active', False))

    def clean_mobile_primary(self):
        mobile = self.cleaned_data.get('mobile_primary', '').strip()
        cleaned = re.sub(r'[\s\-\(\)\+]', '', mobile)
        if len(cleaned) < 10 or not cleaned.isdigit():
            raise forms.ValidationError('Please enter a valid mobile number with at least 10 digits.')
        return mobile

    def clean_mobile_secondary(self):
        mobile = self.cleaned_data.get('mobile_secondary', '').strip()
        if mobile:
            cleaned = re.sub(r'[\s\-\(\)\+]', '', mobile)
            if len(cleaned) < 10 or not cleaned.isdigit():
                raise forms.ValidationError('Please enter a valid secondary mobile number or leave blank.')
        return mobile

    def clean_pin_code(self):
        pin = self.cleaned_data.get('pin_code', '').strip()
        if pin:
            cleaned = re.sub(r'\s+', '', pin)
            if len(cleaned) != 6 or not cleaned.isdigit():
                raise forms.ValidationError('Please enter a valid 6-digit PIN code.')
            return cleaned
        return pin

    def clean_pan_number(self):
        pan = self.cleaned_data.get('pan_number', '').strip().upper()
        if pan:
            if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan):
                raise forms.ValidationError('Please enter a valid 10-character PAN number (e.g. ABCDE1234F).')
        return pan

    def clean_aadhar_number(self):
        aadhar = self.cleaned_data.get('aadhar_number', '').strip()
        if aadhar:
            digits = re.sub(r'\D', '', aadhar)
            if len(digits) != 12:
                raise forms.ValidationError('Aadhaar number must contain 12 digits.')
            return f"{digits[:4]} {digits[4:8]} {digits[8:]}"
        return aadhar


class CustomerSearchForm(forms.Form):
    """
    Search and filter form designed for HTMX live queries.
    """
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'type': 'search',
                'placeholder': 'Search by name, mobile, village, or Aadhaar...',
                'class': (
                    'w-full pl-10 pr-4 py-2.5 text-sm bg-white border border-gray-300 '
                    'rounded-lg shadow-sm placeholder:text-gray-400 focus:outline-none '
                    'focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition duration-150'
                ),
                'autocomplete': 'off',
            }
        )
    )
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Status'),
            ('active', 'Active'),
            ('inactive', 'Inactive'),
        ],
        widget=forms.Select(
            attrs={
                'class': (
                    'px-3 py-2.5 text-sm bg-white border border-gray-300 rounded-lg shadow-sm '
                    'text-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
                )
            }
        )
    )
