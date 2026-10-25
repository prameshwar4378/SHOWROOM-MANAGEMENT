from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date


class Payment(models.Model):
    """
    Payment model representing money manually added to a customer's account.
    Payments are independent of bills, recorded first in customer's account
    and optionally allocated to outstanding bills later.
    """
    PAYMENT_MODE_CHOICES = [
        ('CASH', 'Cash'),
        ('CHEQUE', 'Cheque'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('UPI', 'UPI'),
        ('LOAN', 'Loan Disbursement'),
        ('OTHER', 'Other'),
    ]

    PURPOSE_CHOICES = [
        ('MARGIN', 'Margin Money'),
        ('INSTALLMENT', 'Installment'),
        ('FULL_PAYMENT', 'Full Payment'),
        ('ADVANCE', 'Advance'),
        ('OTHER', 'Other'),
    ]

    receipt_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        verbose_name="Receipt Number",
        help_text="Auto-generated sequential receipt number (RCP-YYYYMMDD-NNN)"
    )
    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name="Customer",
        help_text="Customer making the payment"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Payment Amount (₹)",
        help_text="Total payment amount in INR"
    )
    payment_date = models.DateField(
        default=timezone.localdate,
        verbose_name="Payment Date",
        help_text="Date when payment was received"
    )
    payment_mode = models.CharField(
        max_length=20,
        choices=PAYMENT_MODE_CHOICES,
        default='CASH',
        verbose_name="Payment Mode"
    )
    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
        default='OTHER',
        verbose_name="Payment Purpose"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description / Notes",
        help_text="Optional remarks or notes about this payment"
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Reference Number",
        help_text="UPI UTR number, bank transfer reference, or loan transaction ref"
    )
    cheque_number = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Cheque Number",
        help_text="Cheque leaf number if paid via cheque"
    )
    cheque_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Cheque Date",
        help_text="Date printed on the cheque"
    )
    bank_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Bank Name",
        help_text="Issuing bank or payment receiving bank"
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_payments',
        verbose_name="Received By",
        help_text="Showroom staff member who recorded this payment"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )

    class Meta:
        ordering = ['-payment_date', '-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        indexes = [
            models.Index(fields=['receipt_number']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['payment_mode']),
            models.Index(fields=['purpose']),
            models.Index(fields=['customer', '-payment_date']),
        ]

    def __str__(self):
        rec = self.receipt_number or "PENDING"
        if not rec.startswith('RCP-'):
            rec = f"RCP-{rec}"
        customer_name = self.customer.full_name if (self.customer_id and hasattr(self, 'customer') and self.customer) else "No Customer"
        amt = self.amount or Decimal('0.00')
        return f"{rec} - {customer_name} - ₹{amt}"

    def get_absolute_url(self):
        """Return the URL to access the detail view for this payment."""
        return reverse('payments:payment_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        """
        Auto-generates receipt_number in format 'RCP-YYYYMMDD-NNN'
        sequential per day if not already set.
        """
        if not self.receipt_number:
            p_date = self.payment_date or timezone.localdate()
            if isinstance(p_date, str):
                p_date = parse_date(p_date) or timezone.localdate()
            date_str = p_date.strftime('%Y%m%d')
            prefix = f"RCP-{date_str}-"

            last_payment = (
                Payment.objects.filter(receipt_number__startswith=prefix)
                .order_by('-receipt_number')
                .first()
            )
            highest_seq = 0
            if last_payment and last_payment.receipt_number:
                try:
                    highest_seq = int(last_payment.receipt_number.split('-')[-1])
                except (ValueError, IndexError):
                    highest_seq = 0

            self.receipt_number = f"{prefix}{highest_seq + 1:03d}"

        super().save(*args, **kwargs)

    @property
    def allocated_amount(self):
        """
        Sum of all related PaymentAllocation amounts.
        """
        if not self.pk:
            return Decimal('0.00')
        total = self.allocations.aggregate(
            total=models.Sum('allocated_amount')
        )['total']
        return total if total is not None else Decimal('0.00')

    @property
    def unallocated_amount(self):
        """
        self.amount - allocated_amount.
        """
        return (self.amount or Decimal('0.00')) - self.allocated_amount

    @property
    def is_fully_allocated(self):
        """Check if payment has been completely allocated to bills."""
        return self.unallocated_amount <= Decimal('0.00')

    @property
    def is_partially_allocated(self):
        """Check if payment has partial allocations."""
        return Decimal('0.00') < self.unallocated_amount < self.amount

    @property
    def allocation_percentage(self):
        """Calculate allocation percentage for progress display."""
        if not self.amount or self.amount <= Decimal('0.00'):
            return 0
        pct = (self.allocated_amount / self.amount) * 100
        return min(100, int(round(pct)))


class PaymentAllocation(models.Model):
    """
    PaymentAllocation connects a Payment to a Bill.
    Money is manually allocated from a payment to settle all or part of a bill.
    """
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='allocations',
        verbose_name="Payment Receipt"
    )
    bill = models.ForeignKey(
        'billing.Bill',
        on_delete=models.CASCADE,
        related_name='payment_allocations',
        verbose_name="Bill / Invoice"
    )
    allocated_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Allocated Amount (₹)",
        help_text="Portion of payment amount allocated to this bill"
    )
    allocated_date = models.DateField(
        auto_now_add=True,
        verbose_name="Allocated Date"
    )
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='allocated_payments',
        verbose_name="Allocated By"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Allocation Notes",
        help_text="Optional remarks for this allocation"
    )

    class Meta:
        unique_together = ('payment', 'bill')
        ordering = ['-allocated_date', '-id']
        verbose_name = 'Payment Allocation'
        verbose_name_plural = 'Payment Allocations'

    def __str__(self):
        rcp = self.payment.receipt_number if (self.payment_id and hasattr(self, 'payment') and self.payment) else "No Receipt"
        bill_num = self.bill.bill_number if (self.bill_id and hasattr(self, 'bill') and self.bill) else "No Bill"
        amt = self.allocated_amount or Decimal('0.00')
        return f"Alloc: {rcp} → {bill_num} = ₹{amt}"

    def clean(self):
        """
        Validate allocation constraints:
        1. allocated_amount cannot exceed payment's unallocated_amount (considering existing allocations).
        2. allocated_amount cannot exceed bill's balance_due.
        3. payment and bill must belong to the same customer.
        """
        super().clean()
        errors = {}

        if self.allocated_amount is not None and self.allocated_amount <= Decimal('0.00'):
            errors['allocated_amount'] = "Allocated amount must be greater than zero."

        # Validate that payment and bill belong to the same customer
        if hasattr(self, 'payment') and self.payment and hasattr(self, 'bill') and self.bill:
            if self.payment.customer_id != self.bill.customer_id:
                errors['bill'] = "Payment and Bill must belong to the same customer."

            # 1. allocated_amount cannot exceed payment's available amount
            if self.payment.pk:
                other_allocations_total = self.payment.allocations.exclude(pk=self.pk).aggregate(
                    total=models.Sum('allocated_amount')
                )['total'] or Decimal('0.00')
            else:
                other_allocations_total = Decimal('0.00')
            max_payment_allocatable = self.payment.amount - other_allocations_total

            if self.allocated_amount and self.allocated_amount > max_payment_allocatable:
                errors['allocated_amount'] = (
                    f"Allocated amount (₹{self.allocated_amount}) cannot exceed available "
                    f"unallocated payment amount (₹{max_payment_allocatable})."
                )

            # 2. allocated_amount cannot exceed bill's balance_due
            bill_balance = None
            if hasattr(self.bill, 'balance_due'):
                bill_balance = self.bill.balance_due
                # If editing an existing allocation, add back its previous value
                if self.pk:
                    prev_alloc = PaymentAllocation.objects.filter(pk=self.pk).values_list('allocated_amount', flat=True).first()
                    if prev_alloc:
                        bill_balance += prev_alloc
            elif hasattr(self.bill, 'grand_total') or hasattr(self.bill, 'total_amount'):
                bill_total = getattr(self.bill, 'grand_total', getattr(self.bill, 'total_amount', Decimal('0.00')))
                other_bill_allocs = self.bill.payment_allocations.exclude(pk=self.pk).aggregate(
                    total=models.Sum('allocated_amount')
                )['total'] or Decimal('0.00')
                bill_balance = bill_total - other_bill_allocs

            if bill_balance is not None and self.allocated_amount and self.allocated_amount > bill_balance:
                errors['allocated_amount'] = (
                    f"Allocated amount (₹{self.allocated_amount}) cannot exceed the bill's "
                    f"balance due (₹{bill_balance})."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
