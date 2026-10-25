from decimal import Decimal
from django.db import models
from django.urls import reverse


class Customer(models.Model):
    """
    Customer model representing tractor buyers, agricultural equipment buyers,
    and showroom clients with complete address, contact, identification, and banking details.
    """
    full_name = models.CharField(
        max_length=200,
        verbose_name="Full Name",
        help_text="Customer's complete name (e.g. Ramesh Shankar Patil)"
    )
    father_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Father's / Husband's Name",
        help_text="Father's or husband's name for KYC/loan documents"
    )
    mobile_primary = models.CharField(
        max_length=15,
        verbose_name="Primary Mobile Number",
        help_text="10-digit primary mobile contact number"
    )
    mobile_secondary = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="Secondary Mobile Number",
        help_text="Alternate contact number (optional)"
    )
    email = models.EmailField(
        blank=True,
        verbose_name="Email Address",
        help_text="Customer email for invoices and notices"
    )
    village = models.CharField(
        max_length=100,
        verbose_name="Village / Town",
        help_text="Customer's village, town, or city"
    )
    taluka = models.CharField(
        max_length=100,
        verbose_name="Taluka / Tehsil",
        help_text="Taluka or Tehsil jurisdiction"
    )
    district = models.CharField(
        max_length=100,
        verbose_name="District",
        help_text="District name (e.g. Pune, Kolhapur, Satara)"
    )
    state = models.CharField(
        max_length=100,
        default='Maharashtra',
        blank=True,
        verbose_name="State"
    )
    pin_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="PIN Code"
    )
    aadhar_number = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="Aadhaar Number",
        help_text="12-digit Aadhaar card number"
    )
    pan_number = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="PAN Number",
        help_text="10-character Permanent Account Number"
    )
    bank_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Bank Name",
        help_text="Bank financing the tractor purchase or customer's primary bank"
    )
    bank_branch = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Bank Branch",
        help_text="Branch name and location"
    )
    reference_by = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Referred By",
        help_text="Agent, existing customer, or employee who referred this customer"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes / Remarks",
        help_text="Internal notes regarding preferences, delivery terms, or financing status"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
        help_text="Designates whether this customer is considered active in the system"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
        indexes = [
            models.Index(fields=['full_name']),
            models.Index(fields=['mobile_primary']),
            models.Index(fields=['village']),
            models.Index(fields=['district']),
            models.Index(fields=['is_active']),
            models.Index(fields=['-created_at']),
        ]

    def delete(self, using=None, keep_parents=False):
        if self.pk:
            has_bills = hasattr(self, 'bills') and self.bills.exists()
            has_payments = hasattr(self, 'payments') and self.payments.exists()
            if has_bills or has_payments:
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    "Cannot delete customer with existing bills or payments. Please deactivate (soft-delete) the customer instead."
                )
        return super().delete(using=using, keep_parents=keep_parents)

    def __str__(self):
        return f"{self.full_name} - {self.village}"

    def get_absolute_url(self):
        """Return the URL to access the detail view for this customer."""
        return reverse('customers:customer_detail', kwargs={'pk': self.pk})

    @property
    def total_billed(self):
        """
        Sum of all related active Tax Invoices (commercial sales bills).
        Quotations, Delivery Challans, and Margin Receipts are non-debt documents
        and do not create customer accounts receivable debt.
        Returns Decimal('0.00') if no invoices exist or billing module isn't loaded yet.
        """
        try:
            from billing.models import Bill
            from django.db.models import Sum
            result = Bill.objects.filter(
                customer=self,
                bill_type='TAX_INVOICE'
            ).exclude(status='CANCELLED').aggregate(total=Sum('grand_total'))['total']
            return result if result is not None else Decimal('0.00')
        except Exception:
            return Decimal('0.00')

    @property
    def total_invoiced(self):
        """Alias for total_billed (actual commercial debt)."""
        return self.total_billed

    @property
    def total_quotations(self):
        """Sum of all active Quotations (estimates)."""
        try:
            from billing.models import Bill
            from django.db.models import Sum
            result = Bill.objects.filter(
                customer=self,
                bill_type='QUOTATION'
            ).exclude(status='CANCELLED').aggregate(total=Sum('grand_total'))['total']
            return result if result is not None else Decimal('0.00')
        except Exception:
            return Decimal('0.00')

    @property
    def total_challans(self):
        """Sum of all active Delivery Challans (dispatch memos)."""
        try:
            from billing.models import Bill
            from django.db.models import Sum
            result = Bill.objects.filter(
                customer=self,
                bill_type='DELIVERY_CHALLAN'
            ).exclude(status='CANCELLED').aggregate(total=Sum('grand_total'))['total']
            return result if result is not None else Decimal('0.00')
        except Exception:
            return Decimal('0.00')

    @property
    def total_margin_receipts(self):
        """Sum of all active Margin Money vouchers."""
        try:
            from billing.models import Bill
            from django.db.models import Sum
            result = Bill.objects.filter(
                customer=self,
                bill_type='MARGIN_MONEY'
            ).exclude(status='CANCELLED').aggregate(total=Sum('grand_total'))['total']
            return result if result is not None else Decimal('0.00')
        except Exception:
            return Decimal('0.00')

    @property
    def all_bills_total(self):
        """Sum of all active showroom documents for audit reference."""
        try:
            from billing.models import Bill
            from django.db.models import Sum
            result = Bill.objects.filter(customer=self).exclude(status='CANCELLED').aggregate(total=Sum('grand_total'))['total']
            return result if result is not None else Decimal('0.00')
        except Exception:
            return Decimal('0.00')

    @property
    def total_paid(self):
        """
        Sum of all related payments' amount (from payments.Payment).
        Returns Decimal('0.00') if no payments exist.
        """
        try:
            from payments.models import Payment
            from django.db.models import Sum
            result = Payment.objects.filter(customer=self).aggregate(total=Sum('amount'))['total']
            return result if result is not None else Decimal('0.00')
        except Exception:
            return Decimal('0.00')

    @property
    def outstanding_balance(self):
        """
        Calculates total invoiced minus total paid.
        A positive value indicates customer owes money to the showroom.
        Clamped at 0.00 (never negative).
        """
        return max(Decimal('0.00'), self.total_billed - self.total_paid)

    @property
    def advance_credit(self):
        """
        Calculates total paid minus total invoiced.
        Positive value represents wallet advance credit held with the showroom.
        """
        return max(Decimal('0.00'), self.total_paid - self.total_billed)

    @property
    def unallocated_balance(self):
        """
        Calculates available wallet advance credit not allocated to specific bills.
        If no allocations are recorded, defaults directly to total_paid - total_billed advance.
        """
        try:
            from django.db.models import Sum
            allocations_sum = None

            try:
                from payments.models import PaymentAllocation
                allocations_sum = PaymentAllocation.objects.filter(
                    payment__customer=self
                ).aggregate(total=Sum('allocated_amount'))['total']
            except Exception:
                pass

            if allocations_sum is not None and allocations_sum > Decimal('0.00'):
                unallocated = self.total_paid - allocations_sum
                return max(Decimal('0.00'), unallocated)

            return self.advance_credit
        except Exception:
            return Decimal('0.00')

    @property
    def recent_bills(self):
        """
        Returns the last 5 bills for this customer ordered by bill date.
        """
        if not self.pk:
            return []
        try:
            from billing.models import Bill
            return list(Bill.objects.filter(customer=self).order_by('-bill_date', '-id')[:5])
        except Exception:
            return []

    @property
    def recent_payments(self):
        """
        Returns the last 5 payments for this customer.
        """
        try:
            from payments.models import Payment
            try:
                return list(Payment.objects.filter(customer=self).order_by('-payment_date', '-id')[:5])
            except Exception:
                return list(Payment.objects.filter(customer=self).order_by('-created_at', '-id')[:5])
        except Exception:
            return []
