from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from customers.models import Customer
from billing.models import Bill, BillItem, Product, TractorStockUnit
from settings_app.models import CompanyProfile, GSTConfig, BillNumberSequence

User = get_user_model()


class BillingSystemTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testadmin',
            password='testpassword123',
            is_staff=True
        )
        self.client = Client()
        self.client.force_login(self.user)

        self.company = CompanyProfile.get_instance()
        self.company.company_name = "Showroom Management ERP"
        self.company.state = "Maharashtra"
        self.company.save()

        self.customer = Customer.objects.create(
            full_name="Santosh Jadhav",
            mobile_primary="9876543210",
            village="Baramati",
            taluka="Baramati",
            district="Pune",
            state="Maharashtra"
        )

        self.interstate_customer = Customer.objects.create(
            full_name="Karan Verma",
            mobile_primary="9876543211",
            village="Surat",
            taluka="Choryasi",
            district="Surat",
            state="Gujarat"
        )

        self.gst_config = GSTConfig.objects.create(
            name="Tractor GST 12%",
            hsn_code="8701",
            cgst_rate=Decimal("6.00"),
            sgst_rate=Decimal("6.00"),
            igst_rate=Decimal("12.00"),
            is_active=True
        )

        self.product = Product.objects.create(
            name="Captain 283 4WD",
            category="TRACTOR",
            hsn_code="8701",
            default_price=Decimal("525000.00"),
            stock_quantity=5,
            is_active=True
        )

    def test_quotation_creation_and_totals(self):
        """Test creating a quotation with items and verifying subtotal and words."""
        data = {
            'bill_type': 'QUOTATION',
            'customer': self.customer.id,
            'bill_date': '2026-10-23',
            'status': 'DRAFT',
            'discount_percentage': '',
            'discount_amount': '',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-sr_no': '1',
            'items-0-item_description': 'Captain 283 4WD Tractor',
            'items-0-hsn_code': '8701',
            'items-0-quantity': '1',
            'items-0-unit_price': '525000.00',
            'items-0-discount': '0.00',
        }
        resp = self.client.post(reverse('billing:bill_create') + '?type=QUOTATION', data)
        self.assertEqual(resp.status_code, 302)

        bill = Bill.objects.filter(bill_type='QUOTATION').latest('id')
        self.assertEqual(bill.subtotal, Decimal('525000.00'))
        self.assertEqual(bill.grand_total, Decimal('525000.00'))
        self.assertIn('Five Lakh Twenty Five Thousand', bill.amount_in_words)

    def test_tax_invoice_with_gst_and_roundoff(self):
        """Test Tax Invoice calculation with intra-state CGST + SGST."""
        data = {
            'bill_type': 'TAX_INVOICE',
            'customer': self.customer.id,
            'bill_date': '2026-10-23',
            'status': 'FINAL',
            'is_gst_bill': 'on',
            'gst_config': self.gst_config.id,
            'discount_percentage': '5.00',
            'discount_amount': '',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-sr_no': '1',
            'items-0-item_description': 'Captain 283 4WD Tractor',
            'items-0-hsn_code': '8701',
            'items-0-quantity': '1',
            'items-0-unit_price': '500000.00',
            'items-0-discount': '0.00',
        }
        resp = self.client.post(reverse('billing:bill_create') + '?type=TAX_INVOICE', data)
        self.assertEqual(resp.status_code, 302)

        bill = Bill.objects.filter(bill_type='TAX_INVOICE').latest('id')
        self.assertEqual(bill.subtotal, Decimal('500000.00'))
        self.assertEqual(bill.discount_amount, Decimal('25000.00'))
        self.assertEqual(bill.taxable_amount, Decimal('475000.00'))
        self.assertEqual(bill.cgst_amount, Decimal('28500.00'))
        self.assertEqual(bill.sgst_amount, Decimal('28500.00'))
        self.assertEqual(bill.igst_amount, Decimal('0.00'))
        self.assertEqual(bill.grand_total, Decimal('532000.00'))

    def test_interstate_igst_calculation(self):
        """Test inter-state customer gets IGST applied."""
        bill = Bill.objects.create(
            bill_type='TAX_INVOICE',
            customer=self.interstate_customer,
            is_gst_bill=True,
            gst_config=self.gst_config,
            created_by=self.user,
        )
        BillItem.objects.create(
            bill=bill,
            sr_no=1,
            item_description="Implement Rotavator",
            hsn_code="8432",
            quantity=1,
            unit_price=Decimal("100000.00"),
            discount=Decimal("0.00"),
        )
        bill.calculate_totals(save=True)
        self.assertEqual(bill.cgst_amount, Decimal('0.00'))
        self.assertEqual(bill.sgst_amount, Decimal('0.00'))
        self.assertEqual(bill.igst_amount, Decimal('12000.00'))
        self.assertEqual(bill.grand_total, Decimal('112000.00'))

    def test_margin_money_creation(self):
        """Test Margin Money document with booking details."""
        data = {
            'bill_type': 'MARGIN_MONEY',
            'customer': self.customer.id,
            'bill_date': '2026-10-23',
            'status': 'FINAL',
            'booking_date': '2026-10-23',
            'tractor_model': 'Captain 283 4WD',
            'payment_mode': 'CASH',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-sr_no': '1',
            'items-0-item_description': 'Booking Deposit for Tractor',
            'items-0-quantity': '1',
            'items-0-unit_price': '25000.00',
            'items-0-discount': '0.00',
        }
        resp = self.client.post(reverse('billing:bill_create') + '?type=MARGIN_MONEY', data)
        self.assertEqual(resp.status_code, 302)
        bill = Bill.objects.filter(bill_type='MARGIN_MONEY').latest('id')
        self.assertEqual(bill.grand_total, Decimal('25000.00'))
        self.assertEqual(bill.margin_detail.tractor_model, 'Captain 283 4WD')

    def test_delivery_challan_creation(self):
        """Test Delivery Challan with chassis and engine numbers."""
        data = {
            'bill_type': 'DELIVERY_CHALLAN',
            'customer': self.customer.id,
            'bill_date': '2026-10-23',
            'status': 'FINAL',
            'chassis_number': 'CAPT-CH-9988',
            'engine_number': 'ENG-7766',
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            'items-0-sr_no': '1',
            'items-0-item_description': 'Captain 283 Tractor Unit',
            'items-0-quantity': '1',
            'items-0-unit_price': '525000.00',
            'items-0-discount': '0.00',
        }
        resp = self.client.post(reverse('billing:bill_create') + '?type=DELIVERY_CHALLAN', data)
        self.assertEqual(resp.status_code, 302)
        bill = Bill.objects.filter(bill_type='DELIVERY_CHALLAN').latest('id')
        self.assertEqual(bill.challan_detail.chassis_number, 'CAPT-CH-9988')
        self.assertEqual(bill.challan_detail.engine_number, 'ENG-7766')

    def test_bill_duplicate_action(self):
        """Test duplicating an existing bill."""
        bill = Bill.objects.create(
            bill_type='QUOTATION',
            customer=self.customer,
            created_by=self.user,
        )
        BillItem.objects.create(
            bill=bill,
            sr_no=1,
            item_description="Cultivator 7 Tyne",
            quantity=1,
            unit_price=Decimal("45000.00"),
        )
        bill.calculate_totals(save=True)

        resp = self.client.get(reverse('billing:bill_duplicate', kwargs={'pk': bill.pk}))
        self.assertEqual(resp.status_code, 302)
        new_bill = Bill.objects.order_by('-id').first()
        self.assertNotEqual(new_bill.pk, bill.pk)
        self.assertEqual(new_bill.items.count(), 1)
        self.assertEqual(new_bill.grand_total, Decimal('45000.00'))

    def test_bill_convert_quotation_to_tax_invoice(self):
        """Test converting a Quotation into a Tax Invoice."""
        quotation = Bill.objects.create(
            bill_type='QUOTATION',
            customer=self.customer,
            created_by=self.user,
        )
        BillItem.objects.create(
            bill=quotation,
            sr_no=1,
            item_description="Tractor Unit",
            quantity=1,
            unit_price=Decimal("500000.00"),
        )
        quotation.calculate_totals(save=True)

        resp = self.client.get(reverse('billing:bill_convert', kwargs={'pk': quotation.pk}))
        self.assertEqual(resp.status_code, 302)
        invoice = Bill.objects.order_by('-id').first()
        self.assertEqual(invoice.bill_type, 'TAX_INVOICE')
        self.assertTrue(invoice.is_gst_bill)
        self.assertEqual(invoice.items.count(), 1)

    def test_quick_customer_ajax(self):
        """Test the AJAX customer quick-create modal endpoint."""
        data = {
            'full_name': 'Vinayak More',
            'mobile_primary': '9988776655',
            'village': 'Indapur',
            'taluka': 'Indapur',
            'district': 'Pune',
            'state': 'Maharashtra',
        }
        resp = self.client.post(reverse('customers:customer_quick_create'), data)
        self.assertEqual(resp.status_code, 200)
        json_data = resp.json()
        self.assertTrue(json_data['success'])
        self.assertEqual(json_data['customer']['full_name'], 'Vinayak More')
        self.assertTrue(Customer.objects.filter(full_name='Vinayak More').exists())

    def test_self_dependent_bills_accounting(self):
        """
        Verify that Quotations, Delivery Challans, and Margin Money are self-dependent
        documents that do NOT falsely inflate customer receivables debt.
        Only Tax Invoices create commercial accounts receivable balance.
        """
        from payments.models import Payment

        # 1. Create a Quotation of Rs. 5,00,000
        quote = Bill.objects.create(
            bill_type='QUOTATION',
            customer=self.customer,
            created_by=self.user,
        )
        BillItem.objects.create(
            bill=quote,
            sr_no=1,
            item_description="Tractor Estimate",
            quantity=1,
            unit_price=Decimal("500000.00"),
        )
        quote.calculate_totals(save=True)

        self.assertEqual(self.customer.total_quotations, Decimal('500000.00'))
        self.assertEqual(self.customer.total_billed, Decimal('0.00'))
        self.assertEqual(self.customer.outstanding_balance, Decimal('0.00'))

        # 2. Create a Delivery Challan of Rs. 5,00,000
        challan = Bill.objects.create(
            bill_type='DELIVERY_CHALLAN',
            customer=self.customer,
            created_by=self.user,
        )
        BillItem.objects.create(
            bill=challan,
            sr_no=1,
            item_description="Tractor Delivery",
            quantity=1,
            unit_price=Decimal("500000.00"),
        )
        challan.calculate_totals(save=True)

        self.assertEqual(self.customer.total_challans, Decimal('500000.00'))
        self.assertEqual(self.customer.total_billed, Decimal('0.00'))
        self.assertEqual(self.customer.outstanding_balance, Decimal('0.00'))

        # 3. Create a Margin Money voucher of Rs. 50,000
        margin = Bill.objects.create(
            bill_type='MARGIN_MONEY',
            customer=self.customer,
            created_by=self.user,
        )
        BillItem.objects.create(
            bill=margin,
            sr_no=1,
            item_description="Booking Margin",
            quantity=1,
            unit_price=Decimal("50000.00"),
        )
        margin.calculate_totals(save=True)

        self.assertEqual(self.customer.total_margin_receipts, Decimal('50000.00'))
        self.assertEqual(self.customer.total_billed, Decimal('0.00'))
        self.assertEqual(self.customer.outstanding_balance, Decimal('0.00'))

        # 4. Create an actual Tax Invoice of Rs. 5,00,000 (Commercial Sale)
        invoice = Bill.objects.create(
            bill_type='TAX_INVOICE',
            customer=self.customer,
            created_by=self.user,
        )
        BillItem.objects.create(
            bill=invoice,
            sr_no=1,
            item_description="Tractor Commercial Sale",
            quantity=1,
            unit_price=Decimal("500000.00"),
        )
        invoice.calculate_totals(save=True)

        # Now total_billed is exactly the invoice amount, not 500k + 500k + 50k + 500k = 1.55M!
        self.assertEqual(self.customer.total_billed, Decimal('500000.00'))
        self.assertEqual(self.customer.outstanding_balance, Decimal('500000.00'))

        # 5. Customer pays Rs. 2,00,000 manually into their account
        Payment.objects.create(
            customer=self.customer,
            amount=Decimal('200000.00'),
            payment_mode='CASH',
        )
        self.assertEqual(self.customer.total_paid, Decimal('200000.00'))
        self.assertEqual(self.customer.outstanding_balance, Decimal('300000.00'))

        # 6. Customer pays Rs. 4,00,000 (creating an advance credit)
        Payment.objects.create(
            customer=self.customer,
            amount=Decimal('400000.00'),
            payment_mode='BANK_TRANSFER',
        )
        self.assertEqual(self.customer.total_paid, Decimal('600000.00'))
        self.assertEqual(self.customer.outstanding_balance, Decimal('0.00'))
        self.assertEqual(self.customer.advance_credit, Decimal('100000.00'))
        self.assertEqual(self.customer.unallocated_balance, Decimal('100000.00'))

    def test_temporary_bill_workspace_view(self):
        """Verify Temporary / Scratch Bill workspace renders cleanly with zero database footprint."""
        url = reverse('billing:temporary_bill')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Temporary / Non-Record Bill")
        self.assertContains(response, "IN-MEMORY &bull; NO DB FOOTPRINT")
        self.assertContains(response, "tempBillApp()")

