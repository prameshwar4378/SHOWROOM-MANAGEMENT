"""
Models for the settings_app of Tractor Showroom Management System.

Manages all company configuration that appears on bills, invoices, receipts:
- CompanyProfile (Singleton): Business details, branding logos, address, GSTIN, PAN, declarations.
- BankDetail: Company bank accounts for invoice payment instructions.
- GSTConfig: Applicable GST tax slabs and HSN codes.
- BillNumberSequence: Automatic bill sequence counters by bill type and financial year.
"""

from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone


class CompanyProfile(models.Model):
    """
    Singleton model representing the Tractor Showroom company profile.
    Contains legal, contact, branding, and billing header/footer details.
    Only a single record can exist in the database.
    """
    company_name = models.CharField(
        max_length=200,
        verbose_name="Company Name",
        help_text="Official name of the showroom (e.g., Captain Tractor Showroom)"
    )
    tagline = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Tagline / Slogan",
        help_text="Showroom tagline or brand motto"
    )
    company_logo = models.ImageField(
        upload_to='logos/',
        blank=True,
        null=True,
        verbose_name="Company Logo",
        help_text="Primary showroom logo displayed on headers"
    )
    brand_logo = models.ImageField(
        upload_to='logos/',
        blank=True,
        null=True,
        verbose_name="Brand Logo",
        help_text="Official tractor manufacturer logo (e.g., Captain Tractor)"
    )
    address_line1 = models.CharField(
        max_length=300,
        verbose_name="Address Line 1",
        help_text="Building, shop number, or street name"
    )
    address_line2 = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Address Line 2",
        help_text="Area, landmark, or landmark details"
    )
    city = models.CharField(
        max_length=100,
        verbose_name="City"
    )
    taluka = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Taluka / Tehsil"
    )
    district = models.CharField(
        max_length=100,
        verbose_name="District"
    )
    state = models.CharField(
        max_length=100,
        default='Maharashtra',
        verbose_name="State"
    )
    pin_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="PIN Code"
    )
    mobile_numbers = models.CharField(
        max_length=100,
        verbose_name="Mobile Number(s)",
        help_text="Contact numbers separated by commas (e.g. 9876543210, 9123456780)"
    )
    email = models.EmailField(
        blank=True,
        verbose_name="Email Address"
    )
    gstin_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="GSTIN Number",
        help_text="15-character Goods and Services Tax Identification Number"
    )
    pan_number = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="PAN Number",
        help_text="10-character Permanent Account Number"
    )
    declaration_text = models.TextField(
        blank=True,
        verbose_name="Declaration / Terms",
        help_text="Legal terms and declarations printed on bills and tax invoices"
    )
    footer_text = models.CharField(
        max_length=500,
        default='This is Computer Generated Print',
        verbose_name="Footer Text",
        help_text="Footer notice printed at the bottom of bills"
    )
    signature_image = models.ImageField(
        upload_to='signatures/',
        blank=True,
        null=True,
        verbose_name="Authorized Signature",
        help_text="Digital signature image for authorized signee on invoices"
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
        verbose_name = "Company Profile"
        verbose_name_plural = "Company Profile"

    def __str__(self):
        return self.company_name or "Company Profile"

    def clean(self):
        super().clean()
        if self.gstin_number:
            self.gstin_number = self.gstin_number.strip().upper()
        if self.pan_number:
            self.pan_number = self.pan_number.strip().upper()

    def save(self, *args, **kwargs):
        """
        Enforce Singleton pattern:
        If saving an instance and an existing record exists, update the existing record
        rather than inserting a second row.
        """
        self.clean()
        if not self.pk and CompanyProfile.objects.exists():
            existing = CompanyProfile.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)
        from django.core.cache import cache
        cache.delete('company_profile_instance')

    @classmethod
    def get_instance(cls):
        """
        Return the singleton CompanyProfile instance with 5-minute cache.
        If no record exists, create and return a default profile.
        """
        from django.core.cache import cache
        cached = cache.get('company_profile_instance')
        if cached is not None:
            return cached

        instance = cls.objects.first()
        if not instance:
            instance = cls.objects.create(
                company_name="Showroom Name",
                tagline="Authorized Automobile & Tractor Dealership",
                address_line1="Main Road, Near Market",
                address_line2="",
                city="City",
                taluka="",
                district="District",
                state="Maharashtra",
                pin_code="",
                mobile_numbers="9876543210",
                email="contact@example.com",
                gstin_number="",
                pan_number="",
                declaration_text=(
                    "We declare that this invoice shows the actual price of the goods "
                    "described and that all particulars are true and correct. Subject to local jurisdiction."
                ),
                footer_text="This is Computer Generated Print",
            )
        cache.set('company_profile_instance', instance, 300)
        return instance

    @property
    def full_address(self):
        """Return formatted single-line complete address."""
        parts = [self.address_line1]
        if self.address_line2:
            parts.append(self.address_line2)
        loc = []
        if self.taluka:
            loc.append(f"Tal: {self.taluka}")
        loc.append(f"Dist: {self.district}")
        loc.append(self.state)
        if self.pin_code:
            loc.append(f"PIN: {self.pin_code}")
        parts.append(", ".join(loc))
        return ", ".join(filter(None, parts))

    @property
    def mobile_list(self):
        """Return list of mobile numbers stripped of whitespace."""
        if not self.mobile_numbers:
            return []
        return [m.strip() for m in self.mobile_numbers.split(',') if m.strip()]

    @property
    def brand_logo_path(self):
        """Return absolute filesystem path to brand logo if it exists on disk, else None."""
        try:
            if self.brand_logo and self.brand_logo.name:
                import os
                if os.path.isfile(self.brand_logo.path):
                    return self.brand_logo.path
        except Exception:
            pass
        return None

    @property
    def company_logo_path(self):
        """Return absolute filesystem path to company logo if it exists on disk, else None."""
        try:
            if self.company_logo and self.company_logo.name:
                import os
                if os.path.isfile(self.company_logo.path):
                    return self.company_logo.path
        except Exception:
            pass
        return None

    @property
    def display_logo_path(self):
        """Return primary logo filesystem path (brand logo preferred, then company logo)."""
        return self.brand_logo_path or self.company_logo_path

    @property
    def signature_image_path(self):
        """Return absolute filesystem path to signature image if it exists on disk, else None."""
        try:
            if self.signature_image and self.signature_image.name:
                import os
                if os.path.isfile(self.signature_image.path):
                    return self.signature_image.path
        except Exception:
            pass
        return None

    @property
    def primary_bank(self):
        """Return the primary active bank account or first active account."""
        return self.bank_details.filter(is_active=True).order_by('-is_primary', 'id').first()


class BankDetail(models.Model):
    """
    Bank account details for the company.
    Printed on Quotations and Tax Invoices for customer payments.
    Only one bank account can be marked as primary at a time.
    """
    company = models.ForeignKey(
        CompanyProfile,
        on_delete=models.CASCADE,
        related_name='bank_details',
        verbose_name="Company"
    )
    bank_name = models.CharField(
        max_length=200,
        verbose_name="Bank Name",
        help_text="e.g., State Bank of India, HDFC Bank"
    )
    branch_name = models.CharField(
        max_length=200,
        verbose_name="Branch Name",
        help_text="e.g., Main Branch, Pune"
    )
    account_holder_name = models.CharField(
        max_length=200,
        verbose_name="Account Holder Name",
        help_text="Name registered with the bank"
    )
    account_number = models.CharField(
        max_length=30,
        verbose_name="Account Number"
    )
    ifsc_code = models.CharField(
        max_length=15,
        verbose_name="IFSC Code",
        help_text="11-character Indian Financial System Code"
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name="Is Primary Account",
        help_text="Designates this account as default for invoice prints"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active"
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
        verbose_name = "Bank Detail"
        verbose_name_plural = "Bank Details"
        ordering = ['-is_primary', 'bank_name']

    def __str__(self):
        primary_badge = " [Primary]" if self.is_primary else ""
        return f"{self.bank_name} - {self.account_number} ({self.branch_name}){primary_badge}"

    def clean(self):
        super().clean()
        if self.ifsc_code:
            self.ifsc_code = self.ifsc_code.strip().upper()
        if self.account_number:
            self.account_number = self.account_number.strip()

    def save(self, *args, **kwargs):
        """
        Save BankDetail.
        - Automatically assigns company singleton if not specified.
        - If first bank account, marks as primary automatically.
        - If marked primary, unmarks primary on all other bank records.
        """
        self.clean()
        if not hasattr(self, 'company') or self.company_id is None:
            self.company = CompanyProfile.get_instance()

        # If this is the only bank account, default it to primary
        other_banks = BankDetail.objects.filter(company=self.company)
        if self.pk:
            other_banks = other_banks.exclude(pk=self.pk)
        if not other_banks.exists():
            self.is_primary = True

        super().save(*args, **kwargs)

        # Enforce single primary bank
        if self.is_primary:
            BankDetail.objects.filter(company=self.company).exclude(pk=self.pk).update(is_primary=False)
        else:
            # If saved as non-primary, ensure an active bank remains primary
            has_other_primary = BankDetail.objects.filter(company=self.company, is_primary=True).exclude(pk=self.pk).exists()
            if not has_other_primary:
                other_active = BankDetail.objects.filter(company=self.company, is_active=True).exclude(pk=self.pk).first()
                if other_active:
                    other_active.is_primary = True
                    other_active.save(update_fields=['is_primary'])


@receiver(post_delete, sender=BankDetail)
def ensure_primary_bank_on_delete(sender, instance, **kwargs):
    if instance.is_primary and hasattr(instance, 'company') and instance.company:
        other_active = BankDetail.objects.filter(company=instance.company, is_active=True).first()
        if other_active:
            other_active.is_primary = True
            other_active.save(update_fields=['is_primary'])


class GSTConfig(models.Model):
    """
    GST tax configurations and rates for tractor sales, implements, and spare parts.
    Defines CGST, SGST, IGST percentages and applicable HSN/SAC codes.
    """
    name = models.CharField(
        max_length=100,
        verbose_name="Tax Name / Slab",
        help_text="e.g., GST 12% (Tractor), GST 18% (Spares & Implements), GST 28%"
    )
    hsn_code = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="HSN/SAC Code",
        help_text="Harmonized System of Nomenclature code (e.g., 8701 for Tractors)"
    )
    cgst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('9.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name="CGST Rate (%)",
        help_text="Central GST percentage"
    )
    sgst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('9.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name="SGST Rate (%)",
        help_text="State GST percentage"
    )
    igst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name="IGST Rate (%)",
        help_text="Integrated GST percentage (for inter-state transactions)"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active"
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
        verbose_name = "GST Configuration"
        verbose_name_plural = "GST Configurations"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (CGST: {self.cgst_rate}%, SGST: {self.sgst_rate}%)"

    @property
    def total_rate(self):
        """Combined intra-state GST rate (CGST + SGST)."""
        cgst = self.cgst_rate or Decimal('0.00')
        sgst = self.sgst_rate or Decimal('0.00')
        return cgst + sgst

    @property
    def total_igst_rate(self):
        """Inter-state IGST rate or sum if IGST not explicitly set."""
        if self.igst_rate and self.igst_rate > Decimal('0.00'):
            return self.igst_rate
        return self.total_rate


class BillNumberSequence(models.Model):
    """
    Manages auto-incrementing serial bill numbers for each bill type and financial year.
    Supports Quotation, Tax Invoice, Margin Money, and Delivery Challan.
    """
    BILL_TYPE_CHOICES = [
        ('QUOTATION', 'Quotation'),
        ('TAX_INVOICE', 'Tax Invoice'),
        ('MARGIN_MONEY', 'Margin Money'),
        ('DELIVERY_CHALLAN', 'Delivery Challan'),
    ]

    DEFAULT_PREFIXES = {
        'QUOTATION': 'QT-',
        'TAX_INVOICE': 'TI-',
        'MARGIN_MONEY': 'MM-',
        'DELIVERY_CHALLAN': 'DC-',
    }

    bill_type = models.CharField(
        max_length=20,
        choices=BILL_TYPE_CHOICES,
        verbose_name="Bill Type"
    )
    prefix = models.CharField(
        max_length=10,
        verbose_name="Sequence Prefix",
        help_text="Prefix attached before sequential number (e.g. QT-, TI-)"
    )
    last_number = models.PositiveIntegerField(
        default=0,
        verbose_name="Last Number Used",
        help_text="Current counter value. Next bill will use this number + 1"
    )
    financial_year = models.CharField(
        max_length=10,
        verbose_name="Financial Year",
        help_text="Financial year format (e.g. 2024-25, 2025-26)"
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
        verbose_name = "Bill Number Sequence"
        verbose_name_plural = "Bill Number Sequences"
        unique_together = ('bill_type', 'financial_year')
        ordering = ['bill_type', '-financial_year']

    def __str__(self):
        return f"{self.get_bill_type_display()} ({self.financial_year}) - Current: {self.current_formatted}"

    @property
    def current_formatted(self):
        """Format the current last used number with prefix."""
        return f"{self.prefix}{self.last_number:04d}"

    @property
    def next_formatted(self):
        """Format the preview of the upcoming bill number."""
        return f"{self.prefix}{(self.last_number + 1):04d}"

    @staticmethod
    def calculate_financial_year(dt=None):
        """
        Calculate Indian Financial Year (April 1 to March 31).
        E.g. Oct 2026 -> '2026-27'; Jan 2026 -> '2025-26'.
        """
        if dt is None:
            dt = timezone.now().date()
        elif hasattr(dt, 'date'):
            dt = dt.date()

        if dt.month >= 4:
            start_year = dt.year
            end_year = dt.year + 1
        else:
            start_year = dt.year - 1
            end_year = dt.year
        return f"{start_year}-{str(end_year)[-2:]}"

    @classmethod
    def get_next_number(cls, bill_type, financial_year=None):
        """
        Atomically increment and return the next formatted bill number.
        Uses database select_for_update to prevent race conditions during concurrent bill creation.
        """
        if not financial_year:
            financial_year = cls.calculate_financial_year()

        default_prefix = cls.DEFAULT_PREFIXES.get(bill_type, f"{bill_type[:2]}-")

        with transaction.atomic():
            sequence, created = cls.objects.select_for_update().get_or_create(
                bill_type=bill_type,
                financial_year=financial_year,
                defaults={
                    'prefix': default_prefix,
                    'last_number': 0,
                }
            )
            sequence.last_number += 1
            sequence.save(update_fields=['last_number', 'updated_at'])
            return f"{sequence.prefix}{sequence.last_number:04d}"


class NotificationConfig(models.Model):
    """
    Configuration for automated WhatsApp and SMS alerts for the showroom.
    Singleton pattern: Only 1 active config record exists.
    """
    PROVIDER_CHOICES = [
        ('SIMULATOR', 'Simulator / Dev Logger (No Gateway Required)'),
        ('LOCAL_WHATSAPP', 'Local WhatsApp Gateway (whatsapp-web.js / 100% Free Zero API)'),
        ('WAAPI', 'WaAPI (waapi.app WhatsApp API)'),
        ('WHATSAPP_CLOUD', 'WhatsApp Business Cloud API (Meta)'),
        ('FAST2SMS', 'Fast2SMS Gateway'),
        ('CUSTOM_WEBHOOK', 'Custom HTTP Webhook / UltraMsg'),
    ]

    is_enabled = models.BooleanField(
        default=True,
        verbose_name="Enable Automated Notifications",
        help_text="Master switch to toggle automated messaging on or off."
    )
    provider = models.CharField(
        max_length=30,
        choices=PROVIDER_CHOICES,
        default='SIMULATOR',
        verbose_name="Gateway Provider"
    )
    api_endpoint = models.URLField(
        blank=True,
        verbose_name="API Endpoint / Webhook URL",
        help_text="Gateway endpoint URL (required for Custom Webhook or WhatsApp Cloud API)."
    )
    api_key_or_token = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="API Key / Access Token",
        help_text="Bearer access token or API authorization key."
    )
    sender_phone_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Sender Phone ID / Instance ID",
        help_text="Phone Number ID for Meta WhatsApp Cloud API or Instance ID for UltraMsg."
    )
    auto_send_payment_receipt = models.BooleanField(
        default=True,
        verbose_name="Auto-send Payment Receipts",
        help_text="Automatically send WhatsApp confirmation whenever a customer payment is recorded."
    )
    auto_send_invoice_alert = models.BooleanField(
        default=True,
        verbose_name="Auto-send Invoice Generated Alerts",
        help_text="Automatically alert customer when a Tax Invoice or Delivery Challan is approved."
    )
    auto_send_booking_alert = models.BooleanField(
        default=True,
        verbose_name="Auto-send Margin Money Booking Alerts",
        help_text="Send booking confirmation with tractor specs and delivery schedule."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notification Configuration"
        verbose_name_plural = "Notification Configuration"

    def __str__(self):
        status = "Active" if self.is_enabled else "Disabled"
        return f"Notification Config ({self.get_provider_display()} - {status})"

    def save(self, *args, **kwargs):
        if not self.pk and NotificationConfig.objects.exists():
            existing = NotificationConfig.objects.first()
            self.pk = existing.pk
            if not self.created_at and existing.created_at:
                self.created_at = existing.created_at
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        instance = cls.objects.first()
        if not instance:
            instance = cls.objects.create(
                is_enabled=True,
                provider='SIMULATOR',
                auto_send_payment_receipt=True,
                auto_send_invoice_alert=True,
                auto_send_booking_alert=True,
            )
        return instance


class NotificationLog(models.Model):
    """
    Audit log of all SMS / WhatsApp messages dispatched to customers.
    """
    MESSAGE_TYPE_CHOICES = [
        ('PAYMENT_RECEIPT', 'Payment Receipt Confirmation'),
        ('INVOICE_ALERT', 'Tax Invoice Alert'),
        ('BOOKING_ALERT', 'Margin Money Booking Alert'),
        ('OVERDUE_REMINDER', 'Overdue Payment Reminder'),
        ('CUSTOM', 'Custom Message'),
    ]

    STATUS_CHOICES = [
        ('SENT', 'Sent Successfully'),
        ('FAILED', 'Failed'),
        ('SIMULATED', 'Simulated / Logged'),
    ]

    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notification_logs',
        verbose_name="Customer"
    )
    recipient_name = models.CharField(max_length=200, verbose_name="Recipient Name")
    recipient_mobile = models.CharField(max_length=20, verbose_name="Recipient Mobile")
    message_type = models.CharField(
        max_length=30,
        choices=MESSAGE_TYPE_CHOICES,
        default='PAYMENT_RECEIPT',
        verbose_name="Message Type"
    )
    message_text = models.TextField(verbose_name="Message Content")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='SIMULATED',
        verbose_name="Status"
    )
    response_payload = models.TextField(blank=True, verbose_name="Gateway Response")
    entity_id = models.CharField(max_length=100, blank=True, verbose_name="Entity / Document Reference")
    provider = models.CharField(max_length=30, default='SIMULATOR', verbose_name="Gateway Provider")
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggered_notifications',
        verbose_name="Triggered By"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Sent At")

    @property
    def recipient(self):
        return self.recipient_mobile

    @recipient.setter
    def recipient(self, value):
        self.recipient_mobile = value

    @property
    def message_body(self):
        return self.message_text

    @message_body.setter
    def message_body(self, value):
        self.message_text = value

    @property
    def error_message(self):
        return self.response_payload

    @error_message.setter
    def error_message(self, value):
        self.response_payload = value

    @property
    def notification_type(self):
        return self.message_type

    @notification_type.setter
    def notification_type(self, value):
        self.message_type = value

    class Meta:
        verbose_name = "Notification Audit Log"
        verbose_name_plural = "Notification Audit Logs"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_message_type_display()} to {self.recipient_name} ({self.status})"

