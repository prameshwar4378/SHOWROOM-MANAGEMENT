from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from customers.models import Customer
from billing.models import Bill, BillItem
from payments.models import Payment, PaymentAllocation
from settings_app.models import CompanyProfile

User = get_user_model()


class PaymentSystemTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='payadmin',
            password='testpassword123',
            is_staff=True
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.company = CompanyProfile.get_instance()
        self.company.company_name = "Showroom Management ERP"
        self.company.save()

        self.customer = Customer.objects.create(
            full_name="Rajendra Gaikwad",
            mobile_primary="9822001122",
            village="Saswad",
            taluka="Purandar",
            district="Pune",
            state="Maharashtra"
        )

        self.bill = Bill.objects.create(
            bill_type='TAX_INVOICE',
            customer=self.customer,
            created_by=self.user,
        )
        BillItem.objects.create(
            bill=self.bill,
            sr_no=1,
            item_description="Rotavator Implement",
            quantity=1,
            unit_price=Decimal("100000.00"),
        )
        self.bill.calculate_totals(save=True)

    def test_record_manual_payment(self):
        """Test manually recording a payment into customer's account."""
        data = {
            'customer': self.customer.id,
            'amount': '50000.00',
            'payment_date': '2026-10-23',
            'payment_mode': 'BANK_TRANSFER',
            'purpose': 'MARGIN',
            'reference_number': 'UTR123456789',
        }
        resp = self.client.post(reverse('payments:payment_add'), data)
        self.assertEqual(resp.status_code, 302)

        payment = Payment.objects.latest('id')
        self.assertEqual(payment.amount, Decimal('50000.00'))
        self.assertEqual(payment.customer, self.customer)
        self.assertTrue(payment.receipt_number.startswith('RCP-'))
        self.assertEqual(payment.unallocated_amount, Decimal('50000.00'))

    def test_payment_allocation_to_bill(self):
        """Test allocating an existing payment to a customer's bill."""
        payment = Payment.objects.create(
            customer=self.customer,
            amount=Decimal('40000.00'),
            payment_mode='CASH',
            purpose='PART_PAYMENT',
        )
        data = {
            'bill': self.bill.id,
            'allocated_amount': '40000.00',
            'notes': 'Advance margin payment',
        }
        resp = self.client.post(
            reverse('payments:payment_allocate', kwargs={'pk': payment.pk}),
            data
        )
        self.assertEqual(resp.status_code, 302)

        self.assertEqual(payment.allocated_amount, Decimal('40000.00'))
        self.assertEqual(payment.unallocated_amount, Decimal('0.00'))
        self.assertEqual(self.bill.total_paid, Decimal('40000.00'))
        self.assertEqual(self.bill.balance_due, Decimal('60000.00'))

    def test_payment_allocation_over_limit_prevented(self):
        """Test that allocating more than the bill balance or payment amount is rejected."""
        payment = Payment.objects.create(
            customer=self.customer,
            amount=Decimal('150000.00'),
            payment_mode='UPI',
        )
        # Bill balance is 100,000, trying to allocate 120,000 should fail
        data = {
            'bill': self.bill.id,
            'allocated_amount': '120000.00',
        }
        resp = self.client.post(
            reverse('payments:payment_allocate', kwargs={'pk': payment.pk}),
            data
        )
        self.assertEqual(resp.status_code, 302)
        # Allocation was rejected
        self.assertEqual(payment.allocations.count(), 0)

    def test_customer_ledger_view(self):
        """Test customer financial ledger calculations."""
        Payment.objects.create(
            customer=self.customer,
            amount=Decimal('30000.00'),
            payment_mode='CASH',
        )
        resp = self.client.get(reverse('payments:customer_ledger', kwargs={'pk': self.customer.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Saswad')
        self.assertEqual(self.customer.total_billed, Decimal('100000.00'))
        self.assertEqual(self.customer.total_paid, Decimal('30000.00'))
        self.assertEqual(self.customer.outstanding_balance, Decimal('70000.00'))

    def test_payment_receipt_pdf(self):
        """Test payment receipt PDF view returns valid PDF."""
        payment = Payment.objects.create(
            customer=self.customer,
            amount=Decimal('25000.00'),
            payment_mode='CASH',
        )
        resp = self.client.get(reverse('payments:payment_pdf', kwargs={'pk': payment.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertGreater(len(resp.content), 1000)
