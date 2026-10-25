from django import forms
from .models import ExpenseCategory, Expense


class TailwindFormMixin:
    """Helper mixin to inject standard Tailwind CSS classes to widgets."""
    def apply_tailwind(self):
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'h-4 w-4 rounded-md border-slate-300 text-blue-600 focus:ring-blue-500 transition')
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault('class', 'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-800 shadow-2xs hover:border-slate-400 focus:border-blue-600 focus:ring-4 focus:ring-blue-100/60 focus:outline-none transition duration-150 cursor-pointer')
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault('rows', 3)
                widget.attrs.setdefault('class', 'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 shadow-2xs hover:border-slate-400 focus:border-blue-600 focus:ring-4 focus:ring-blue-100/60 focus:outline-none transition duration-150')
            elif isinstance(widget, forms.DateInput):
                widget.attrs.setdefault('class', 'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-sm text-slate-800 shadow-2xs hover:border-slate-400 focus:border-blue-600 focus:ring-4 focus:ring-blue-100/60 focus:outline-none transition duration-150')
            elif isinstance(widget, forms.FileInput):
                widget.attrs.setdefault('class', 'block w-full text-sm text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 transition cursor-pointer')
            else:
                widget.attrs.setdefault('class', 'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 shadow-2xs hover:border-slate-400 focus:border-blue-600 focus:ring-4 focus:ring-blue-100/60 focus:outline-none transition duration-150')


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
            'title': forms.TextInput(attrs={'placeholder': 'उदा. शो-रूम वीज बिल / ट्रॅक्टर डिझेल / चहापान'}),
            'amount': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
            'payee_name': forms.TextInput(attrs={'placeholder': 'उदा. MSEB / भारत पेट्रोलियम / स्टाफ नाव'}),
            'payment_reference': forms.TextInput(attrs={'placeholder': 'UPI UTR / Cheque No. / Transaction ID'}),
            'notes': forms.Textarea(attrs={'placeholder': 'अधिक तपशील किंवा शेरा (Remarks)...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_tailwind()
        self.fields['category'].queryset = ExpenseCategory.objects.filter(is_active=True).order_by('name')
        self.fields['category'].empty_label = "-- खर्च प्रकार निवडा (Select Category) --"


class ExpenseCategoryForm(forms.ModelForm, TailwindFormMixin):
    """
    Form to create or edit an expense category.
    """
    class Meta:
        model = ExpenseCategory
        fields = ['name', 'code', 'icon', 'color', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'उदा. Diesel & Fuel / डिझेल खर्च'}),
            'code': forms.TextInput(attrs={'placeholder': 'उदा. diesel-fuel (रिकामे ठेवल्यास आपोआप तयार होईल)'}),
            'icon': forms.TextInput(attrs={'placeholder': 'उदा. fas fa-gas-pump / fas fa-bolt'}),
            'color': forms.TextInput(attrs={'placeholder': 'उदा. blue / emerald / amber / rose / purple'}),
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder': 'या खर्च प्रकाराविषयी माहिती...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_tailwind()
