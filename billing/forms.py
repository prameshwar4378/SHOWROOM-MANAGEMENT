"""
Forms for the billing application.
"""
from decimal import Decimal
from django import forms
from django.forms import inlineformset_factory
from .models import (
    Bill, BillItem, MarginMoneyDetail, DeliveryChallanDetail,
    Product, TractorStockUnit, PurchaseBill, PurchaseBillItem
)
from customers.models import Customer
from settings_app.models import GSTConfig


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
            else:
                widget.attrs.setdefault('class', 'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 shadow-2xs hover:border-slate-400 focus:border-blue-600 focus:ring-4 focus:ring-blue-100/60 focus:outline-none transition duration-150')


class ProductForm(forms.ModelForm, TailwindFormMixin):
    """Form for tractor models, implements, and spare parts inventory catalog."""
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'part_number', 'hsn_code',
            'purchase_price', 'default_price', 'min_stock_level',
            'stock_quantity', 'is_active'
        ]
        widgets = {
            'default_price': forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'Selling price'}),
            'purchase_price': forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'Procurement cost'}),
            'min_stock_level': forms.NumberInput(attrs={'min': 0, 'placeholder': '2'}),
            'stock_quantity': forms.NumberInput(attrs={'min': 0, 'placeholder': 'Current showroom stock'}),
            'part_number': forms.TextInput(attrs={'placeholder': 'e.g. SKU-8701 or OEM Part #'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_tailwind()
        self.fields['part_number'].required = False
        self.fields['purchase_price'].required = False

    def clean_purchase_price(self):
        val = self.cleaned_data.get('purchase_price')
        return val if val not in (None, '') else Decimal('0.00')

    def clean_default_price(self):
        val = self.cleaned_data.get('default_price')
        return val if val not in (None, '') else Decimal('0.00')


class PurchaseBillForm(forms.ModelForm, TailwindFormMixin):
    """Form for Inward Stock / Manufacturer Purchase Invoice."""
    class Meta:
        model = PurchaseBill
        fields = [
            'invoice_number', 'supplier_name', 'supplier_gstin',
            'invoice_date', 'received_date', 'purchase_type', 'notes'
        ]
        widgets = {
            'invoice_date': forms.DateInput(attrs={'type': 'date'}),
            'received_date': forms.DateInput(attrs={'type': 'date'}),
            'invoice_number': forms.TextInput(attrs={'placeholder': 'e.g. INV-2026-0814'}),
            'supplier_name': forms.TextInput(attrs={'placeholder': 'e.g. Captain Tractors Pvt. Ltd.'}),
            'supplier_gstin': forms.TextInput(attrs={'placeholder': 'Supplier GSTIN'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Transporter, batch, or lorry receipt details...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_tailwind()
        self.fields['supplier_gstin'].required = False
        self.fields['notes'].required = False


class PurchaseBillItemForm(forms.ModelForm):
    """Line item form for Purchase / Stock Inward."""
    class Meta:
        model = PurchaseBillItem
        fields = ['product', 'quantity', 'unit_cost', 'chassis_number', 'engine_number', 'color']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'w-full min-w-[200px] px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-800 bg-white shadow-2xs hover:border-slate-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 focus:outline-none transition'
            }),
            'quantity': forms.NumberInput(attrs={
                'min': 1,
                'class': 'w-20 px-2.5 py-2 border border-slate-300 rounded-lg text-center text-xs font-semibold text-slate-800 bg-white shadow-2xs hover:border-slate-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 focus:outline-none transition'
            }),
            'unit_cost': forms.NumberInput(attrs={
                'step': '0.01',
                'class': 'w-32 px-3 py-2 border border-slate-300 rounded-lg text-right text-xs font-semibold font-mono text-slate-800 bg-white shadow-2xs hover:border-slate-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 focus:outline-none transition',
                'placeholder': '0.00'
            }),
            'chassis_number': forms.TextInput(attrs={
                'placeholder': 'Chassis (if Tractor)',
                'class': 'w-36 px-2.5 py-2 border border-slate-300 rounded-lg text-xs font-mono text-slate-800 bg-white shadow-2xs hover:border-slate-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 focus:outline-none transition'
            }),
            'engine_number': forms.TextInput(attrs={
                'placeholder': 'Engine No.',
                'class': 'w-32 px-2.5 py-2 border border-slate-300 rounded-lg text-xs font-mono text-slate-800 bg-white shadow-2xs hover:border-slate-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 focus:outline-none transition'
            }),
            'color': forms.TextInput(attrs={
                'placeholder': 'Color',
                'class': 'w-24 px-2.5 py-2 border border-slate-300 rounded-lg text-xs text-slate-800 bg-white shadow-2xs hover:border-slate-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 focus:outline-none transition'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(is_active=True).order_by('category', 'name')
        self.fields['chassis_number'].required = False
        self.fields['engine_number'].required = False
        self.fields['color'].required = False


PurchaseBillItemFormSet = inlineformset_factory(
    PurchaseBill,
    PurchaseBillItem,
    form=PurchaseBillItemForm,
    extra=1,
    can_delete=True
)


class TractorStockUnitForm(forms.ModelForm, TailwindFormMixin):
    """Form for serialized tractor units in showroom stockyard."""
    class Meta:
        model = TractorStockUnit
        fields = ['product', 'chassis_number', 'engine_number', 'color', 'status', 'purchase_date', 'purchase_price']
        widgets = {
            'purchase_date': forms.DateInput(attrs={'type': 'date'}),
            'purchase_price': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_tailwind()
        self.fields['product'].queryset = Product.objects.filter(is_active=True).order_by('name')
        self.fields['purchase_date'].required = False
        self.fields['purchase_price'].required = False

class BillForm(forms.ModelForm, TailwindFormMixin):
    """
    Main form for creating and updating showroom bills.
    """
    use_required_attribute = False

    class Meta:
        model = Bill
        fields = [
            'bill_type', 'customer', 'bill_date', 'due_date',
            'supplier_ref', 'other_ref', 'bank_name',
            'is_gst_bill', 'gst_config',
            'accessories_insurance',
            'discount_percentage', 'discount_amount',
            'notes', 'status'
        ]
        widgets = {
            'bill_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'supplier_ref': forms.TextInput(attrs={'placeholder': 'e.g. Showroom Name'}),
            'other_ref': forms.TextInput(attrs={'placeholder': 'e.g. Financer / L&T Finance Ltd.'}),
            'bank_name': forms.TextInput(attrs={'placeholder': 'e.g. State Bank of India'}),
            'accessories_insurance': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '0.00'}),
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
        self.fields['gst_config'].queryset = GSTConfig.objects.filter(is_active=True).order_by('name')
        self.fields['gst_config'].required = False
        self.fields['supplier_ref'].required = False
        self.fields['other_ref'].required = False
        self.fields['bank_name'].required = False
        self.fields['accessories_insurance'].required = False
        self.fields['discount_percentage'].required = False
        self.fields['discount_amount'].required = False
        self.fields['due_date'].required = False
        self.fields['notes'].required = False
        self.fields['discount_percentage'].widget.attrs.setdefault('placeholder', '0.00')
        self.fields['discount_amount'].widget.attrs.setdefault('placeholder', '0.00')


    def clean_discount_percentage(self):
        val = self.cleaned_data.get('discount_percentage')
        if val is None or val == '':
            return Decimal('0.00')
        return val

    def clean_discount_amount(self):
        val = self.cleaned_data.get('discount_amount')
        if val is None or val == '':
            return Decimal('0.00')
        return val

    def clean_accessories_insurance(self):
        val = self.cleaned_data.get('accessories_insurance')
        if val is None or val == '':
            return Decimal('0.00')
        return val


class BillItemForm(forms.ModelForm, TailwindFormMixin):
    """Form for line items on a bill."""
    use_required_attribute = False

    class Meta:
        model = BillItem
        fields = ['sr_no', 'item_description', 'chassis_number', 'engine_number', 'hsn_code', 'quantity', 'unit_price', 'discount']
        widgets = {
            'sr_no': forms.NumberInput(attrs={'class': 'w-14 px-2 py-2 border border-slate-300 rounded-lg text-center text-xs font-bold text-slate-700 bg-white shadow-2xs focus:border-blue-500 focus:ring-2 focus:ring-blue-100 focus:outline-none transition'}),
            'item_description': forms.TextInput(attrs={'placeholder': 'e.g. CAPTAIN 280-DI 4WD OIB', 'class': 'w-full px-3.5 py-2 border border-slate-300 rounded-lg text-xs text-slate-800 bg-white shadow-2xs focus:border-blue-500 focus:ring-2 focus:ring-blue-100 focus:outline-none transition'}),
            'chassis_number': forms.TextInput(attrs={'placeholder': 'Chassis No.', 'class': 'w-36 px-2.5 py-2 border border-slate-300 rounded-lg text-xs font-mono text-slate-800 bg-white shadow-2xs focus:border-blue-500 focus:ring-2 focus:ring-blue-100 focus:outline-none transition'}),
            'engine_number': forms.TextInput(attrs={'placeholder': 'Engine No.', 'class': 'w-36 px-2.5 py-2 border border-slate-300 rounded-lg text-xs font-mono text-slate-800 bg-white shadow-2xs focus:border-blue-500 focus:ring-2 focus:ring-blue-100 focus:outline-none transition'}),
            'hsn_code': forms.TextInput(attrs={'placeholder': '8701', 'class': 'w-24 px-2.5 py-2 border border-slate-300 rounded-lg text-xs font-mono text-slate-800 bg-white shadow-2xs focus:border-blue-500 focus:ring-2 focus:ring-blue-100 focus:outline-none transition'}),
            'quantity': forms.NumberInput(attrs={'class': 'w-20 px-2 py-2 border border-slate-300 rounded-lg text-center text-xs font-semibold text-slate-800 bg-white shadow-2xs focus:border-blue-500 focus:ring-2 focus:ring-blue-100 focus:outline-none transition', 'min': 1}),
            'unit_price': forms.NumberInput(attrs={'class': 'w-32 px-3 py-2 border border-slate-300 rounded-lg text-right text-xs font-semibold font-mono text-slate-800 bg-white shadow-2xs focus:border-blue-500 focus:ring-2 focus:ring-blue-100 focus:outline-none transition', 'step': '0.01'}),
            'discount': forms.NumberInput(attrs={'class': 'w-28 px-3 py-2 border border-slate-300 rounded-lg text-right text-xs font-medium font-mono text-slate-800 bg-white shadow-2xs focus:border-blue-500 focus:ring-2 focus:ring-blue-100 focus:outline-none transition', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sr_no'].required = False
        self.fields['chassis_number'].required = False
        self.fields['engine_number'].required = False
        self.fields['hsn_code'].required = False
        self.fields['discount'].required = False

    def clean_discount(self):
        val = self.cleaned_data.get('discount')
        if val is None or val == '':
            return Decimal('0.00')
        return val

    def clean_quantity(self):
        val = self.cleaned_data.get('quantity')
        if val is None or val == '' or int(val) < 1:
            return 1
        return val

    def has_changed(self):
        """
        An unpersisted item is only considered changed if meaningful item data
        (description, price, chassis, or engine) has been entered.
        Default values for quantity, discount, or auto-populated sr_no will not
        cause an empty extra form to be treated as an entered item.
        """
        if not self.instance.pk:
            desc = str(self.data.get(self.add_prefix('item_description')) or '').strip() if self.is_bound else str(self.initial.get('item_description') or '').strip()
            price = str(self.data.get(self.add_prefix('unit_price')) or '').strip() if self.is_bound else str(self.initial.get('unit_price') or '').strip()
            chassis = str(self.data.get(self.add_prefix('chassis_number')) or '').strip() if self.is_bound else str(self.initial.get('chassis_number') or '').strip()
            engine = str(self.data.get(self.add_prefix('engine_number')) or '').strip() if self.is_bound else str(self.initial.get('engine_number') or '').strip()
            if not desc and not price and not chassis and not engine:
                return False
        return super().has_changed()


class BaseBillItemFormSet(forms.BaseInlineFormSet):
    """
    Custom BaseInlineFormSet that:
    1. Sets extra=0 when editing an existing bill (no phantom extra rows).
    2. Validates that at least one valid line item remains on the bill.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.extra = 0

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        valid_items_count = 0
        items_data = []
        for form in self.forms:
            if not form.is_valid():
                continue
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                desc = (form.cleaned_data.get('item_description') or '').strip()
                if desc:
                    valid_items_count += 1
                    items_data.append(form.cleaned_data)
        if valid_items_count == 0:
            raise forms.ValidationError("Please provide at least one valid line item for the bill.")

        # Enforce stock availability on commercial sales/delivery bills
        bill_type = None
        if self.is_bound and hasattr(self, 'data'):
            bill_type = self.data.get('bill_type')
        if not bill_type:
            bill_type = getattr(self.instance, 'bill_type', None)
        if bill_type in ['TAX_INVOICE', 'DELIVERY_CHALLAN']:
            from .inventory_service import validate_stock_availability
            stock_errors = validate_stock_availability(bill_type, items_data, current_bill=self.instance)
            if stock_errors:
                raise forms.ValidationError(stock_errors)


BillItemFormSet = inlineformset_factory(
    Bill,
    BillItem,
    form=BillItemForm,
    formset=BaseBillItemFormSet,
    extra=1,
    can_delete=True
)


class MarginMoneyDetailForm(forms.ModelForm, TailwindFormMixin):
    """Extra fields for Margin Money bills matching real-world voucher."""
    use_required_attribute = False

    class Meta:
        model = MarginMoneyDetail
        fields = [
            'booking_date', 'reason_for_payment', 'payment_mode',
            'receiver_name', 'hypothecation', 'tractor_model',
            'cheque_number', 'bank_reference', 'expected_delivery_date'
        ]
        widgets = {
            'booking_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'reason_for_payment': forms.TextInput(attrs={'placeholder': 'e.g. Part payment / Advance booking'}),
            'receiver_name': forms.TextInput(attrs={'placeholder': 'e.g. Showroom Name'}),
            'hypothecation': forms.TextInput(attrs={'placeholder': 'e.g. L&T Finance LTD. / SBI'}),
            'tractor_model': forms.TextInput(attrs={'placeholder': 'e.g. CAPTAIN 280-DI 4WD'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_tailwind()
        self.fields['booking_date'].required = False
        self.fields['reason_for_payment'].required = False
        self.fields['receiver_name'].required = False
        self.fields['hypothecation'].required = False
        self.fields['tractor_model'].required = False
        self.fields['cheque_number'].required = False
        self.fields['bank_reference'].required = False
        self.fields['expected_delivery_date'].required = False


class DeliveryChallanDetailForm(forms.ModelForm, TailwindFormMixin):
    """Extra fields for Delivery Challan bills matching real-world delivery memo."""
    use_required_attribute = False

    class Meta:
        model = DeliveryChallanDetail
        fields = [
            'delivered_from', 'financer',
            'chassis_number', 'engine_number', 'vehicle_number',
            'transport_mode', 'delivery_address', 'receiver_name', 'receiver_mobile'
        ]
        widgets = {
            'delivered_from': forms.TextInput(attrs={'placeholder': 'e.g. Showroom Name'}),
            'financer': forms.TextInput(attrs={'placeholder': 'e.g. Indusind Bank Ltd.'}),
            'chassis_number': forms.TextInput(attrs={'placeholder': 'Chassis / Frame No.'}),
            'engine_number': forms.TextInput(attrs={'placeholder': 'Engine Serial No.'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_tailwind()
        self.fields['delivered_from'].required = False
        self.fields['financer'].required = False
        self.fields['chassis_number'].required = False
        self.fields['engine_number'].required = False
        self.fields['vehicle_number'].required = False
        self.fields['transport_mode'].required = False
        self.fields['delivery_address'].required = False
        self.fields['receiver_name'].required = False
        self.fields['receiver_mobile'].required = False
