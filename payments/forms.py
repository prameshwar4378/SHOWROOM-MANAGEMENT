"""
Forms for the payments application.
"""
from django import forms
from .models import Payment, PaymentAllocation
from customers.models import Customer
from billing.models import Bill


class TailwindFormMixin:
    """Helper mixin to inject standard Tailwind CSS classes to widgets."""
    def apply_tailwind(self):
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'h-4 w-4 rounded-md border-slate-300 text-emerald-600 focus:ring-emerald-500 transition')
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault('class', 'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-800 shadow-2xs hover:border-slate-400 focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100/60 focus:outline-none transition duration-150 cursor-pointer')
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault('rows', 3)
                widget.attrs.setdefault('class', 'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 shadow-2xs hover:border-slate-400 focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100/60 focus:outline-none transition duration-150')
            elif isinstance(widget, forms.DateInput):
                widget.attrs.setdefault('class', 'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2 text-sm text-slate-800 shadow-2xs hover:border-slate-400 focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100/60 focus:outline-none transition duration-150')
            else:
                widget.attrs.setdefault('class', 'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 shadow-2xs hover:border-slate-400 focus:border-emerald-600 focus:ring-4 focus:ring-emerald-100/60 focus:outline-none transition duration-150')


class PaymentForm(forms.ModelForm, TailwindFormMixin):
    """
    Form to manually record money received into a customer's account.
    Independent of bills.
    """
    class Meta:
        model = Payment
        fields = [
            'customer', 'amount', 'payment_date', 'payment_mode',
            'purpose', 'reference_number', 'cheque_number', 'cheque_date',
            'bank_name', 'description'
        ]
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
            'cheque_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_tailwind()
        cust_id = None
        if self.data and self.data.get('customer'):
            cust_id = self.data.get('customer')
        elif self.instance and self.instance.customer_id:
            cust_id = self.instance.customer_id

        if cust_id:
            from django.db.models import Q
            self.fields['customer'].queryset = Customer.objects.filter(
                Q(is_active=True) | Q(pk=cust_id)
            ).order_by('full_name')
        else:
            self.fields['customer'].queryset = Customer.objects.filter(is_active=True).order_by('full_name')
        self.fields['reference_number'].required = False
        self.fields['cheque_number'].required = False
        self.fields['cheque_date'].required = False
        self.fields['bank_name'].required = False
        self.fields['description'].required = False

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Payment amount must be greater than zero.")
        return amount

    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get('payment_mode')
        if mode == 'CHEQUE':
            if not cleaned_data.get('cheque_number'):
                self.add_error('cheque_number', "Cheque number is required for Cheque payments.")
            if not cleaned_data.get('bank_name'):
                self.add_error('bank_name', "Bank name is required for Cheque payments.")
        elif mode in ('UPI', 'BANK_TRANSFER', 'LOAN'):
            if not cleaned_data.get('reference_number'):
                self.add_error('reference_number', "Reference/UTR number is required for digital or loan payments.")
        return cleaned_data


class PaymentAllocationForm(forms.ModelForm, TailwindFormMixin):
    """
    Form to allocate an existing payment (or portion of it) to a specific bill.
    """
    class Meta:
        model = PaymentAllocation
        fields = ['bill', 'allocated_amount', 'notes']

    def __init__(self, *args, payment=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_tailwind()
        self.payment = payment
        self.fields['notes'].required = False

        if payment:
            self.instance.payment = payment
            # Show only Tax Invoices belonging to this customer that have remaining balance
            bills = Bill.objects.filter(
                customer=payment.customer,
                bill_type='TAX_INVOICE'
            ).exclude(status='CANCELLED')
            unpaid_pks = [b.pk for b in bills if b.balance_due > 0]
            self.fields['bill'].queryset = Bill.objects.filter(pk__in=unpaid_pks).order_by('-bill_date')
            self.fields['allocated_amount'].initial = payment.unallocated_amount
        else:
            self.fields['bill'].queryset = Bill.objects.none()

    def clean_allocated_amount(self):
        amt = self.cleaned_data.get('allocated_amount')
        if amt is not None and amt <= 0:
            raise forms.ValidationError("Allocated amount must be greater than zero.")
        return amt
