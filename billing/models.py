"""
Models for the billing application of Tractor Showroom Management System.
Supports Quotation, Tax Invoice, Margin Money, and Delivery Challan bills.
"""
from decimal import Decimal, ROUND_HALF_UP
from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from .utils import number_to_words_indian


from settings_app.models import BillNumberSequence


class Bill(models.Model):
    """
    Core Bill model representing all four types of showroom documents:
    Quotation, Tax Invoice, Margin Money receipt, and Delivery Challan.
    """
    BILL_TYPE_CHOICES = [
        ('QUOTATION', 'Quotation'),
        ('TAX_INVOICE', 'Tax Invoice'),
        ('MARGIN_MONEY', 'Margin Money'),
        ('DELIVERY_CHALLAN', 'Delivery Challan'),
    ]

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('FINAL', 'Final'),
        ('CANCELLED', 'Cancelled'),
    ]

    bill_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        help_text="Auto-generated sequential bill number"
    )
    bill_type = models.CharField(
        max_length=20,
        choices=BILL_TYPE_CHOICES,
        help_text="Type of bill"
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='bills',
        help_text="Customer associated with this bill"
    )
    bill_date = models.DateField(
        default=timezone.now,
        help_text="Date of bill issuance"
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Payment due date (if applicable)"
    )
    supplier_ref = models.CharField(
        max_length=150,
        blank=True,
        help_text="Supplier reference (defaults to Showroom Name)"
    )
    other_ref = models.CharField(
        max_length=150,
        blank=True,
        help_text="Other Reference / Financer (e.g. L&T Finance Ltd.)"
    )
    bank_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Financing Bank name (for Quotations / Invoices)"
    )
    is_gst_bill = models.BooleanField(
        default=False,
        help_text="Enable GST calculations and tax invoice breakdown"
    )
    gst_config = models.ForeignKey(
        'settings_app.GSTConfig',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bills',
        help_text="Applicable GST configuration"
    )
    accessories_insurance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        blank=True,
        help_text="Accessories and insurance charges"
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Sum of line item amounts before discounts and tax"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        blank=True,
        help_text="Overall discount percentage"
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        blank=True,
        help_text="Total discount in currency"
    )
    taxable_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount subject to tax (subtotal - discount)"
    )
    cgst_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Central GST amount"
    )
    sgst_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="State GST amount"
    )
    igst_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Integrated GST amount (interstate)"
    )
    total_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total tax amount (CGST + SGST + IGST)"
    )
    round_off_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Commercial round-off to nearest integer rupee"
    )
    grand_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Final payable amount"
    )
    amount_in_words = models.CharField(
        max_length=500,
        blank=True,
        help_text="Grand total formatted in Indian currency words"
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional remarks, terms, or conditions"
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='DRAFT',
        help_text="Current state of the bill"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_bills',
        help_text="User who created this bill"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Bill"
        verbose_name_plural = "Bills"

    def __str__(self):
        customer_name = getattr(self.customer, 'full_name', str(self.customer)) if self.customer_id else "No Customer"
        return f"{self.bill_number or 'Draft'} - {customer_name}"

    def save(self, *args, **kwargs):
        """Auto-generate bill_number on first save using BillNumberSequence."""
        if not self.bill_number:
            fy = BillNumberSequence.calculate_financial_year(self.bill_date) if self.bill_date else None
            self.bill_number = BillNumberSequence.get_next_number(self.bill_type, financial_year=fy)
        super().save(*args, **kwargs)

    def calculate_totals(self, save=False):
        """
        Recalculates subtotal from items, applies discount, calculates GST
        (intra-state CGST+SGST vs inter-state IGST), computes commercial round-off
        to nearest integer rupee, sets grand_total and amount_in_words.
        """
        from settings_app.models import CompanyProfile

        if self.pk:
            items = list(self.items.all())
            subtotal = sum((item.amount or Decimal('0.00')) for item in items)
        else:
            subtotal = self.subtotal or Decimal('0.00')

        self.subtotal = Decimal(str(subtotal)).quantize(Decimal('0.01'))

        # Calculate discount
        if self.discount_percentage and self.discount_percentage > Decimal('0.00'):
            self.discount_amount = ((self.subtotal * self.discount_percentage) / Decimal('100')).quantize(Decimal('0.01'))
        elif self.discount_amount is None:
            self.discount_amount = Decimal('0.00')

        # Taxable amount
        self.taxable_amount = max(Decimal('0.00'), self.subtotal - self.discount_amount).quantize(Decimal('0.01'))

        # GST Calculation
        if self.is_gst_bill and self.taxable_amount > Decimal('0.00') and self.gst_config:
            company = CompanyProfile.get_instance()
            company_state = (company.state or '').strip().lower()
            customer_state = ''
            if self.customer and hasattr(self.customer, 'state'):
                customer_state = (self.customer.state or '').strip().lower()

            is_interstate = bool(customer_state and company_state and customer_state != company_state)

            cgst_rate = Decimal(str(self.gst_config.cgst_rate or 0))
            sgst_rate = Decimal(str(self.gst_config.sgst_rate or 0))
            igst_rate = Decimal(str(self.gst_config.igst_rate or (cgst_rate + sgst_rate)))

            if is_interstate:
                self.cgst_amount = Decimal('0.00')
                self.sgst_amount = Decimal('0.00')
                self.igst_amount = ((self.taxable_amount * igst_rate) / Decimal('100')).quantize(Decimal('0.01'))
            else:
                self.cgst_amount = ((self.taxable_amount * cgst_rate) / Decimal('100')).quantize(Decimal('0.01'))
                self.sgst_amount = ((self.taxable_amount * sgst_rate) / Decimal('100')).quantize(Decimal('0.01'))
                self.igst_amount = Decimal('0.00')

            self.total_tax = (self.cgst_amount + self.sgst_amount + self.igst_amount).quantize(Decimal('0.01'))
        else:
            if not self.is_gst_bill:
                self.gst_config = None
            self.cgst_amount = Decimal('0.00')
            self.sgst_amount = Decimal('0.00')
            self.igst_amount = Decimal('0.00')
            self.total_tax = Decimal('0.00')

        extra_charges = self.accessories_insurance or Decimal('0.00')
        unrounded_total = self.taxable_amount + self.total_tax + extra_charges
        # Indian commercial rounding to nearest whole rupee using ROUND_HALF_UP
        rounded_grand_total = unrounded_total.quantize(Decimal('1'), rounding=ROUND_HALF_UP).quantize(Decimal('0.01'))
        self.round_off_amount = (rounded_grand_total - unrounded_total).quantize(Decimal('0.01'))
        self.grand_total = rounded_grand_total
        self.amount_in_words = self.get_amount_in_words()

        if save and self.pk:
            self.save(update_fields=[
                'subtotal', 'discount_percentage', 'discount_amount',
                'taxable_amount', 'cgst_amount', 'sgst_amount', 'igst_amount',
                'total_tax', 'accessories_insurance', 'round_off_amount', 'grand_total', 'amount_in_words',
                'is_gst_bill', 'gst_config'
            ])

    def get_hsn_summary(self):
        """
        Groups bill items by HSN code and returns list of dictionaries
        with taxable value, tax rates, tax amounts, and total tax.
        Compliant with Indian Tax Invoice HSN summary.
        """
        if not self.is_gst_bill or not self.gst_config or not self.pk:
            return []

        from settings_app.models import CompanyProfile
        company = CompanyProfile.get_instance()
        company_state = (company.state or '').strip().lower()
        customer_state = ''
        if self.customer and hasattr(self.customer, 'state'):
            customer_state = (self.customer.state or '').strip().lower()

        is_interstate = bool(customer_state and company_state and customer_state != company_state)

        cgst_pct = Decimal(str(self.gst_config.cgst_rate or 0))
        sgst_pct = Decimal(str(self.gst_config.sgst_rate or 0))
        igst_pct = Decimal(str(self.gst_config.igst_rate or (cgst_pct + sgst_pct)))

        summary = {}
        items = list(self.items.all())
        total_subtotal = sum(((item.amount or Decimal('0.00')) for item in items), Decimal('0.00'))

        for item in items:
            code = (item.hsn_code or (self.gst_config.hsn_code if self.gst_config else '') or '8701').strip()
            item_amt = item.amount or Decimal('0.00')
            discount_base = self.discount_amount or Decimal('0.00')
            if total_subtotal > Decimal('0.00'):
                item_discount = (discount_base * (item_amt / total_subtotal)).quantize(Decimal('0.01'))
            else:
                item_discount = Decimal('0.00')
            taxable = max(Decimal('0.00'), item_amt - item_discount)

            if code not in summary:
                summary[code] = {
                    'hsn_code': code,
                    'taxable_value': Decimal('0.00'),
                    'cgst_rate': Decimal('0.00') if is_interstate else cgst_pct,
                    'cgst_amount': Decimal('0.00'),
                    'sgst_rate': Decimal('0.00') if is_interstate else sgst_pct,
                    'sgst_amount': Decimal('0.00'),
                    'igst_rate': igst_pct if is_interstate else Decimal('0.00'),
                    'igst_amount': Decimal('0.00'),
                    'total_tax': Decimal('0.00'),
                }
            summary[code]['taxable_value'] += taxable

        summary_list = []
        for code, data in summary.items():
            taxable = data['taxable_value']
            if is_interstate:
                data['igst_amount'] = ((taxable * igst_pct) / Decimal('100')).quantize(Decimal('0.01'))
            else:
                data['cgst_amount'] = ((taxable * cgst_pct) / Decimal('100')).quantize(Decimal('0.01'))
                data['sgst_amount'] = ((taxable * sgst_pct) / Decimal('100')).quantize(Decimal('0.01'))
            data['total_tax'] = (data['cgst_amount'] + data['sgst_amount'] + data['igst_amount']).quantize(Decimal('0.01'))
            summary_list.append(data)

        return summary_list

    def get_amount_in_words(self):
        """Converts grand_total to words like 'Rupees Five Lakh Ninety Five Thousand Only'."""
        return number_to_words_indian(self.grand_total)

    @property
    def total_paid(self):
        """Sum of allocated payments for this bill."""
        from django.db.models import Sum
        try:
            if hasattr(self, 'payment_allocations'):
                total = self.payment_allocations.aggregate(t=Sum('allocated_amount'))['t']
                if total is not None:
                    return Decimal(str(total)).quantize(Decimal('0.01'))
        except Exception:
            pass
        return Decimal('0.00')

    @property
    def balance_due(self):
        """Grand total minus total_paid."""
        grand = self.grand_total or Decimal('0.00')
        due = grand - self.total_paid
        return max(Decimal('0.00'), due).quantize(Decimal('0.01'))

    @property
    def payment_status(self):
        """Returns 'PAID', 'PARTIAL', or 'UNPAID' based on total_paid vs grand_total."""
        grand = self.grand_total or Decimal('0.00')
        paid = self.total_paid
        if grand <= Decimal('0.00'):
            return 'PAID'
        if paid >= grand:
            return 'PAID'
        elif paid > Decimal('0.00'):
            return 'PARTIAL'
        return 'UNPAID'


class Product(models.Model):
    """
    Tractor, implement, or accessory catalog item for showroom inventory.
    Provides foundational support for inventory tracking.
    """
    CATEGORY_CHOICES = [
        ('TRACTOR', 'Tractor'),
        ('IMPLEMENT', 'Implement / Attachment'),
        ('TROLLEY', 'Trolley / Trailer'),
        ('SPARE', 'Spare Part'),
        ('ACCESSORY', 'Accessory'),
    ]

    name = models.CharField(
        max_length=200,
        help_text="Model name or product description (e.g. Captain 283 4WD, Rotavator 5ft)"
    )
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default='TRACTOR'
    )
    hsn_code = models.CharField(
        max_length=20,
        default='8701',
        help_text="HSN code (8701 for tractors, 8432 for implements)"
    )
    default_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Standard ex-showroom retail price"
    )
    part_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Part Number / SKU (especially for spare parts & implements)"
    )
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Dealer procurement cost per unit"
    )
    min_stock_level = models.PositiveIntegerField(
        default=2,
        help_text="Threshold for low stock warnings"
    )
    stock_quantity = models.PositiveIntegerField(
        default=0,
        help_text="Current available inventory quantity in showroom"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this item is currently available for billing"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Product / Tractor Model"
        verbose_name_plural = "Products & Models"

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    @property
    def is_in_stock(self):
        return self.stock_quantity > 0

    @property
    def is_low_stock(self):
        return 0 < self.stock_quantity <= self.min_stock_level

    @property
    def stock_status(self):
        if self.stock_quantity <= 0:
            return 'OUT_OF_STOCK'
        elif self.stock_quantity <= self.min_stock_level:
            return 'LOW_STOCK'
        return 'IN_STOCK'

    @property
    def total_stock_value(self):
        """Total valuation of available inventory at procurement price or retail price."""
        cost = (self.purchase_price if self.purchase_price and self.purchase_price > Decimal('0.00') else (self.default_price or Decimal('0.00')))
        qty = self.stock_quantity or 0
        return (Decimal(str(qty)) * cost).quantize(Decimal('0.01'))


class PurchaseBill(models.Model):
    """
    Inward stock / purchase invoice from manufacturers or parts vendors.
    Automatically increments product stock quantities upon recording.
    """
    PURCHASE_TYPE_CHOICES = [
        ('TRACTOR', 'Tractors (Serialized)'),
        ('IMPLEMENT', 'Implements / Attachments'),
        ('SPARE', 'Spare Parts / Lubricants'),
        ('MIXED', 'General / Mixed Stock Inward'),
    ]

    invoice_number = models.CharField(
        max_length=50,
        help_text="Supplier / Manufacturer Invoice or Challan Number"
    )
    supplier_name = models.CharField(
        max_length=200,
        help_text="Manufacturer or vendor name (e.g. Captain Tractors Pvt Ltd)"
    )
    supplier_gstin = models.CharField(
        max_length=20,
        blank=True,
        help_text="Supplier GSTIN (optional)"
    )
    invoice_date = models.DateField(
        default=timezone.now,
        help_text="Date on purchase invoice"
    )
    received_date = models.DateField(
        default=timezone.now,
        help_text="Date stock was physically received in showroom"
    )
    purchase_type = models.CharField(
        max_length=20,
        choices=PURCHASE_TYPE_CHOICES,
        default='MIXED'
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total invoice procurement value"
    )
    notes = models.TextField(
        blank=True,
        help_text="Remarks, transporter details, or batch notes"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_bills'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-invoice_date', '-created_at']
        verbose_name = "Purchase / Inward Bill"
        verbose_name_plural = "Purchase / Inward Bills"

    def __str__(self):
        return f"Purchase Inv #{self.invoice_number} - {self.supplier_name}"


class PurchaseBillItem(models.Model):
    """
    Line item for Inward Stock / Purchase Bill.
    """
    purchase_bill = models.ForeignKey(
        PurchaseBill,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='purchase_items'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Quantity received"
    )
    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Unit procurement cost"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Line total: quantity * unit_cost"
    )
    chassis_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Chassis number (for tractors)"
    )
    engine_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Engine number (for tractors)"
    )
    color = models.CharField(
        max_length=50,
        blank=True,
        default='Red'
    )

    class Meta:
        verbose_name = "Purchase Bill Item"
        verbose_name_plural = "Purchase Bill Items"

    def save(self, *args, **kwargs):
        self.amount = (Decimal(str(self.quantity or 1)) * Decimal(str(self.unit_cost or 0))).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)


class TractorStockUnit(models.Model):
    """
    Individual tractor vehicle tracking chassis & engine serial numbers.
    Foundational unit for dealership stockyard management.
    """
    STATUS_CHOICES = [
        ('IN_STOCK', 'In Stock (Available)'),
        ('BOOKED', 'Booked (Margin Received)'),
        ('DELIVERED', 'Delivered to Customer'),
        ('RETURNED', 'Returned / Replaced'),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stock_units',
        help_text="Product model"
    )
    chassis_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique Chassis / Frame Number"
    )
    engine_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique Engine Serial Number"
    )
    color = models.CharField(
        max_length=50,
        blank=True,
        default='Red',
        help_text="Vehicle paint color"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='IN_STOCK'
    )
    purchase_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date vehicle was received from manufacturer"
    )
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Dealer procurement cost"
    )
    allocated_bill = models.ForeignKey(
        Bill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='allocated_tractors',
        help_text="Bill or Delivery Challan this unit is allocated to"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tractor Stock Unit"
        verbose_name_plural = "Tractor Stock Units"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} - Chassis: {self.chassis_number} ({self.get_status_display()})"


class BillItem(models.Model):
    """
    Line item for a Bill. Auto-calculates amount = (quantity * unit_price) - discount.
    """
    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Bill this item belongs to"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bill_items',
        help_text="Optional link to inventory catalog product"
    )
    tractor_unit = models.ForeignKey(
        TractorStockUnit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bill_items',
        help_text="Optional link to specific serialized tractor in stock"
    )
    sr_no = models.PositiveIntegerField(
        help_text="Serial number / item order"
    )
    item_description = models.CharField(
        max_length=500,
        help_text="Description of the tractor, implement, or service"
    )
    chassis_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Chassis / Frame serial number"
    )
    engine_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Engine serial number"
    )
    hsn_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="Harmonized System of Nomenclature code (e.g., 8701 for tractors)"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Number of units"
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Price per unit before discount and tax"
    )
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Line item discount in currency"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Calculated line amount: (quantity * unit_price) - discount"
    )

    class Meta:
        ordering = ['sr_no']
        verbose_name = "Bill Item"
        verbose_name_plural = "Bill Items"

    def __str__(self):
        return f"{self.sr_no}. {self.item_description}"

    @property
    def quotation_description(self):
        """
        Return clean item description for Quotations.
        Quotations are pre-sale estimates and should not display
        specific vehicle chassis or engine numbers.
        """
        import re
        desc = self.item_description or ""
        desc = re.sub(r'\s*\([Cc]hassis:[^\)]*\)', '', desc)
        desc = re.sub(r'\s*\([Ee]ngine:[^\)]*\)', '', desc)
        return desc.strip()

    def save(self, *args, **kwargs):
        """Auto-calculate amount = (quantity * unit_price) - discount."""
        qty = Decimal(str(self.quantity or 1))
        price = Decimal(str(self.unit_price or 0))
        disc = Decimal(str(self.discount or 0))
        self.amount = max(Decimal('0.00'), (qty * price) - disc).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)


class MarginMoneyDetail(models.Model):
    """
    OneToOne extension for Margin Money receipt bills.
    Records booking details, expected delivery, and payment mode.
    """
    PAYMENT_MODE_CHOICES = [
        ('CASH', 'Cash'),
        ('CHEQUE', 'Cheque'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('UPI', 'UPI'),
    ]

    bill = models.OneToOneField(
        Bill,
        on_delete=models.CASCADE,
        related_name='margin_detail',
        help_text="Associated Margin Money bill"
    )
    booking_date = models.DateField(
        default=timezone.now,
        help_text="Date the booking was accepted"
    )
    expected_delivery_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expected delivery date of the vehicle"
    )
    tractor_model = models.CharField(
        max_length=200,
        blank=True,
        help_text="Model and make of the tractor booked"
    )
    reason_for_payment = models.CharField(
        max_length=200,
        blank=True,
        default="Part payment",
        help_text="Region of Rs / Purpose of payment (e.g. Part payment)"
    )
    payment_mode = models.CharField(
        max_length=50,
        choices=PAYMENT_MODE_CHOICES,
        default='CASH',
        help_text="Mode of margin payment"
    )
    receiver_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Receiver name (defaults to showroom name)"
    )
    hypothecation = models.CharField(
        max_length=200,
        blank=True,
        help_text="HYP / Financer (e.g. L&T Finance LTD.)"
    )
    cheque_number = models.CharField(
        max_length=30,
        blank=True,
        help_text="Cheque number (if paid by cheque)"
    )
    bank_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Bank reference / transaction UTR number"
    )

    class Meta:
        verbose_name = "Margin Money Detail"
        verbose_name_plural = "Margin Money Details"

    def __str__(self):
        return f"Margin Detail: {self.bill.bill_number} - {self.tractor_model or 'Booking'}"


class DeliveryChallanDetail(models.Model):
    """
    OneToOne extension for Delivery Challan bills.
    Records chassis, engine, vehicle registration, and transporter details.
    """
    bill = models.OneToOneField(
        Bill,
        on_delete=models.CASCADE,
        related_name='challan_detail',
        help_text="Associated Delivery Challan bill"
    )
    delivered_from = models.CharField(
        max_length=200,
        blank=True,
        help_text="Delivered From showroom"
    )
    financer = models.CharField(
        max_length=200,
        blank=True,
        help_text="Financer Bank (e.g. Indusind Bank Ltd.)"
    )
    chassis_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Chassis / Frame serial number"
    )
    engine_number = models.CharField(
        max_length=50,
        blank=True,
        help_text="Engine serial number"
    )
    vehicle_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Temporary or permanent vehicle registration number"
    )
    transport_mode = models.CharField(
        max_length=100,
        blank=True,
        help_text="Mode of transport (e.g. Self-Driven, Trolley, Flatbed Truck)"
    )
    delivery_address = models.TextField(
        blank=True,
        help_text="Destination address for delivery"
    )
    receiver_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Name of the person receiving the vehicle"
    )
    receiver_mobile = models.CharField(
        max_length=15,
        blank=True,
        help_text="Mobile number of the receiver"
    )

    class Meta:
        verbose_name = "Delivery Challan Detail"
        verbose_name_plural = "Delivery Challan Details"

    def __str__(self):
        return f"Delivery Challan: {self.bill.bill_number} - Chassis: {self.chassis_number}"
