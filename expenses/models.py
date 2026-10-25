from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


class ExpenseCategory(models.Model):
    """
    Categories for showroom operating expenses (e.g. Rent, Electricity, Diesel, Salaries).
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Category Name"
    )
    code = models.SlugField(
        max_length=60,
        blank=True,
        unique=True,
        verbose_name="Category Code"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description / Details"
    )
    icon = models.CharField(
        max_length=50,
        default='fas fa-receipt',
        verbose_name="Icon Class (FontAwesome)"
    )
    color = models.CharField(
        max_length=30,
        default='blue',
        verbose_name="Theme Color"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active Status"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Expense Category"
        verbose_name_plural = "Expense Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = slugify(self.name)
        super().save(*args, **kwargs)


class Expense(models.Model):
    """
    Operational showroom expense / payment voucher.
    """
    PAYMENT_MODE_CHOICES = [
        ('CASH', 'Cash'),
        ('UPI', 'UPI (GooglePay / PhonePe / Paytm)'),
        ('BANK_TRANSFER', 'Bank Transfer (NEFT / RTGS / IMPS)'),
        ('CHEQUE', 'Cheque'),
        ('CARD', 'Debit / Credit Card'),
        ('OTHER', 'Other'),
    ]

    expense_number = models.CharField(
        max_length=40,
        unique=True,
        blank=True,
        verbose_name="Voucher No.",
        help_text="Auto-generated expense voucher reference (e.g. EXP-202610-0001)"
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name="Expense Category"
    )
    title = models.CharField(
        max_length=200,
        verbose_name="Description / Title",
        help_text="Brief summary of the expense (e.g. Showroom Electricity Bill, Tractor Demo Diesel)"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Amount (₹)"
    )
    expense_date = models.DateField(
        default=timezone.now,
        verbose_name="Expense Date"
    )
    payment_mode = models.CharField(
        max_length=25,
        choices=PAYMENT_MODE_CHOICES,
        default='CASH',
        verbose_name="Payment Mode"
    )
    payee_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Paid To / Payee / Vendor",
        help_text="Name of the person, supplier, or entity receiving payment"
    )
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ref / UTR / Cheque No.",
        help_text="Cheque number, UPI transaction ID, or bank UTR"
    )
    receipt_voucher = models.FileField(
        upload_to='expenses/%Y/%m/',
        blank=True,
        null=True,
        verbose_name="Voucher / Bill Attachment",
        help_text="Optional scanned invoice, cash receipt, or bill photo"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Internal Remarks"
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_expenses',
        verbose_name="Recorded By"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        ordering = ['-expense_date', '-created_at']

    def __str__(self):
        return f"{self.expense_number} - {self.title} (₹{self.amount})"

    def save(self, *args, **kwargs):
        if not self.expense_number:
            year_month = (self.expense_date or timezone.now().date()).strftime('%Y%m')
            prefix = f"EXP-{year_month}-"
            latest = Expense.objects.filter(expense_number__startswith=prefix).order_by('-id').first()
            if latest and latest.expense_number:
                try:
                    last_seq = int(latest.expense_number.split('-')[-1])
                    new_seq = last_seq + 1
                except (ValueError, IndexError):
                    new_seq = 1
            else:
                new_seq = 1
            self.expense_number = f"{prefix}{new_seq:04d}"

        super().save(*args, **kwargs)
