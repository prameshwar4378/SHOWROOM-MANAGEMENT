from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import UserProfile
from customers.models import Customer
from billing.models import Bill, BillItem
from payments.models import Payment
from settings_app.models import CompanyProfile, NotificationConfig, NotificationLog
from settings_app.notification_service import (
    normalize_indian_mobile,
    format_inr,
    build_payment_receipt_message,
    build_invoice_alert_message,
    build_overdue_reminder_message,
    send_notification,
)


class NotificationEngineTests(TestCase):
    """
    Test suite for Track D: Automated WhatsApp & SMS Notification Engine.
    """
    def setUp(self):
        self.company = CompanyProfile.get_instance()
        self.company.company_name = "Super Tractor Showroom"
        self.company.save()

        self.config = NotificationConfig.get_instance()
        self.config.is_enabled = True
        self.config.provider = 'SIMULATOR'
        self.config.auto_send_payment_receipt = True
        self.config.auto_send_invoice_alert = True
        self.config.save()

        self.user = User.objects.create_superuser(
            username='admin_test',
            email='admin@example.com',
            password='Password123!'
        )
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.role = 'ADMIN'
        profile.mobile_number = '9876543210'
        profile.save()

        self.customer = Customer.objects.create(
            full_name="Balasaheb Patil",
            mobile_primary="9876543210",
            village="Baramati",
            taluka="Baramati",
            district="Pune",
            state="Maharashtra"
        )

        self.bill = Bill.objects.create(
            customer=self.customer,
            bill_type='TAX_INVOICE',
            bill_number='TI-0099',
            grand_total=Decimal('650000.00'),
            created_by=self.user,
            status='PENDING'
        )
        BillItem.objects.create(
            bill=self.bill,
            sr_no=1,
            item_description="Captain 280 DI 4WD",
            quantity=1,
            unit_price=Decimal('650000.00'),
            amount=Decimal('650000.00')
        )

        self.payment = Payment.objects.create(
            customer=self.customer,
            receipt_number='REC-0088',
            amount=Decimal('150000.00'),
            payment_mode='NEFT_RTGS',
            purpose='PART_PAYMENT',
            received_by=self.user
        )

        self.client = Client()
        self.client.force_login(self.user)

    def test_normalize_indian_mobile(self):
        """Test Indian mobile number sanitization and standard +91 E.164 normalization."""
        self.assertEqual(normalize_indian_mobile("9876543210"), "919876543210")
        self.assertEqual(normalize_indian_mobile("09876543210"), "919876543210")
        self.assertEqual(normalize_indian_mobile("919876543210"), "919876543210")
        self.assertEqual(normalize_indian_mobile("+91 98765-43210"), "919876543210")
        self.assertIsNone(normalize_indian_mobile("12345"))
        self.assertIsNone(normalize_indian_mobile(""))
        self.assertIsNone(normalize_indian_mobile(None))

    def test_message_builders(self):
        """Test template generation for receipts, invoices, and overdue reminders."""
        # Payment Receipt
        recipient, msg = build_payment_receipt_message(self.payment)
        self.assertEqual(recipient, "919876543210")
        self.assertIn("REC-0088", msg)
        self.assertIn("Balasaheb Patil", msg)
        self.assertIn("Super Tractor Showroom", msg)

        # Tax Invoice Alert
        rec_inv, msg_inv = build_invoice_alert_message(self.bill)
        self.assertEqual(rec_inv, "919876543210")
        self.assertIn("TI-0099", msg_inv)
        self.assertIn("6,50,000", msg_inv)

        # Overdue Reminder
        rec_rem, msg_rem = build_overdue_reminder_message(self.customer, Decimal('500000.00'))
        self.assertEqual(rec_rem, "919876543210")
        self.assertIn("5,00,000", msg_rem)

    def test_simulator_dispatch_creates_audit_log(self):
        """Test that in SIMULATOR mode, messages are cleanly persisted to NotificationLog without throwing."""
        log = send_notification(
            recipient="919876543210",
            message="Test Greeting Message",
            notification_type='CUSTOM',
            user=self.user,
            entity_id='TEST-001'
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.status, 'SIMULATED')
        self.assertEqual(log.recipient, '919876543210')
        self.assertEqual(log.entity_id, 'TEST-001')
        self.assertEqual(NotificationLog.objects.filter(entity_id='TEST-001').count(), 1)

    def test_service_disabled_toggle(self):
        """When notification master switch is disabled, send_notification aborts safely."""
        self.config.is_enabled = False
        self.config.save()

        log = send_notification(
            recipient="919876543210",
            message="Test Message",
            notification_type='CUSTOM',
            user=self.user
        )
        self.assertIsNone(log)

    def test_notification_settings_view(self):
        """Test GET and POST on NotificationSettingsView."""
        url = reverse('settings_app:notification_settings')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WhatsApp & SMS Notifications")

        # Test Ping Action
        post_data = {
            'action_test_send': '1',
            'test_recipient': '9876543210',
            'is_enabled': 'on',
            'provider': 'SIMULATOR',
            'auto_send_payment_receipt': 'on',
            'auto_send_invoice_alert': 'on',
            'auto_send_booking_alert': 'on',
        }
        resp = self.client.post(url, post_data)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(NotificationLog.objects.filter(entity_id='SYSTEM_TEST').exists())

    def test_notification_log_list_view(self):
        """Test NotificationLogListView with filtering."""
        NotificationLog.objects.create(
            recipient_mobile="919876543210",
            recipient_name="Balasaheb Patil",
            message_type='PAYMENT_RECEIPT',
            provider='SIMULATOR',
            message_text="Test payment body",
            status='SIMULATED',
            entity_id='REC-TEST-99',
            sent_by=self.user
        )
        url = reverse('settings_app:notification_logs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "REC-TEST-99")

        # Search filter
        resp_filter = self.client.get(f"{url}?q=REC-TEST-99")
        self.assertContains(resp_filter, "REC-TEST-99")

    def test_payment_manual_notification_trigger(self):
        """Test manual resend endpoint for payment receipt."""
        url = reverse('payments:payment_send_notification', kwargs={'pk': self.payment.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(NotificationLog.objects.filter(entity_id=self.payment.receipt_number).exists())

    def test_bill_manual_notification_trigger(self):
        """Test manual resend endpoint for bill invoice."""
        url = reverse('billing:bill_send_notification', kwargs={'pk': self.bill.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(NotificationLog.objects.filter(entity_id=self.bill.bill_number).exists())

    def test_customer_send_reminder_view(self):
        """Test single customer balance reminder dispatch view."""
        url = reverse('payments:customer_send_reminder', kwargs={'customer_id': self.customer.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(NotificationLog.objects.filter(entity_id=f"CUST-{self.customer.pk:04d}").exists())

    def test_settings_pages_render_bilingual_help_popover(self):
        """Test that settings pages render the (i) button and bilingual English & Marathi help popover."""
        pages = [
            reverse('settings_app:company_profile'),
            reverse('settings_app:bank_list'),
            reverse('settings_app:gst_list'),
            reverse('settings_app:sequence_list'),
            reverse('settings_app:notification_settings'),
            reverse('settings_app:notification_logs'),
            reverse('settings_app:bank_add'),
            reverse('settings_app:gst_add'),
        ]
        for page_url in pages:
            response = self.client.get(page_url)
            self.assertEqual(response.status_code, 200, f"Failed on {page_url}")
            # Verify bilingual indicator and trigger
            self.assertContains(response, "Feature Help | वैशिष्ट्य माहिती")
            self.assertContains(response, "Language / भाषा:")
            self.assertContains(response, "दोन्ही (Both)")
            self.assertContains(response, "मराठी")
            self.assertContains(response, "English")

    def test_local_whatsapp_provider_config(self):
        """Test configuring and saving LOCAL_WHATSAPP gateway provider."""
        self.config.provider = 'LOCAL_WHATSAPP'
        self.config.api_endpoint = 'http://localhost:3000/send'
        self.config.save()
        self.assertEqual(self.config.provider, 'LOCAL_WHATSAPP')
        self.assertEqual(self.config.get_provider_display(), 'Local WhatsApp Gateway (whatsapp-web.js / 100% Free Zero API)')

    def test_local_whatsapp_dispatch_success(self):
        """Test dispatching an alert through Local WhatsApp bridge endpoint with mock."""
        from unittest.mock import patch, MagicMock
        self.config.provider = 'LOCAL_WHATSAPP'
        self.config.api_endpoint = 'http://localhost:3000/send'
        self.config.save()

        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"success": true, "status": "SENT", "messageId": "msg-123"}'
        mock_resp.__enter__.return_value = mock_resp

        with patch('urllib.request.urlopen', return_value=mock_resp) as mock_urlopen:
            log = send_notification(
                recipient='9876543210',
                message='Test Local WhatsApp Bridge',
                notification_type='CUSTOM',
                user=self.user,
                entity_id='LOCAL_TEST_01'
            )
            self.assertEqual(log.status, 'SENT')
            self.assertEqual(log.provider, 'LOCAL_WHATSAPP')
            self.assertIn('msg-123', log.response_payload)
            mock_urlopen.assert_called_once()

