from django import forms
from .models import ExpenseCategory, Expense


class TailwindFormMixin:
    """Helper mixin to inject standard Tailwind CSS classes to widgets."""
    def apply_tailwind(self):
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'h-4 w-4 rounded-md border-slate-300 text-rose-600 focus:ring-rose-500 transition')
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault('class', 'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-800 shadow-2xs hover:border-slate-400 focus:border-rose-600 focus:ring-4 focus:ring-rose-100/60 focus:outline-none transition duration-150 cursor-pointer')
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault('rows', 3)
                widget.attrs.setdefault('class', 'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 shadow-2xs hover:border-slate-400 focus:border-rose-600 focus:ring-4 focus:ring-rose-100/60 focus:outline-none transition duration-150')
            elif isinstance(widget, forms.DateInput):
                widget.attrs.setdefault('class', 'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-sm text-slate-800 shadow-2xs hover:border-slate-400 focus:border-rose-600 focus:ring-4 focus:ring-rose-100/60 focus:outline-none transition duration-150')
            elif isinstance(widget, forms.FileInput):
                widget.attrs.setdefault('class', 'block w-full text-sm text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-rose-50 file:text-rose-700 hover:file:bg-rose-100 transition cursor-pointer')
            else:
                widget.attrs.setdefault('class', 'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 shadow-2xs hover:border-slate-400 focus:border-rose-600 focus:ring-4 focus:ring-rose-100/60 focus:outline-none transition duration-150')


class ExpenseForm(forms.ModelForm, TailwindFormMixin):
    """
    Form to record or update an operating showroom expense.
    """
    class Meta:
        model = Expense
        fields = [
            'category',
            'title',
            'amount',
            'expense_date',
            'payment_mode',
            'payee_name',
            'payment_reference',
            'receipt_voucher',
            'notes',
        ]
        widgets = {
            'expense_date': forms.DateInput(attrs={'type': 'date'}),
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Showroom Electricity Bill, Tractor Demo Diesel, Office Tea & Snacks'}),
            'amount': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
            'payee_name': forms.TextInput(attrs={'placeholder': 'e.g. MSEB, Bharat Petroleum, Staff Name'}),
            'payment_reference': forms.TextInput(attrs={'placeholder': 'e.g. UPI UTR, Cheque No, Bank Ref'}),
            'notes': forms.Textarea(attrs={'placeholder': 'Additional internal notes or remarks...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_tailwind()
        self.fields['category'].queryset = ExpenseCategory.objects.filter(is_active=True).order_by('name')
        self.fields['category'].empty_label = "-- Select Expense Category --"


class ExpenseCategoryForm(forms.ModelForm, TailwindFormMixin):
    """
    Form to create or edit an expense category.
    """
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'code', 'icon', 'color', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Diesel & Fuel, Staff Salaries, Office Rent'}),
            'code': forms.TextInput(attrs={'placeholder': 'e.g. diesel-fuel (leave blank to auto-generate)'}),
            'icon': forms.TextInput(attrs={'placeholder': 'e.g. fas fa-gas-pump, fas fa-bolt'}),
            'color': forms.TextInput(attrs={'placeholder': 'e.g. blue, emerald, amber, rose, purple'}),
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional description for this expense category...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_tailwind()
