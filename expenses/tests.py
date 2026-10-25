from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from .models import ExpenseCategory, Expense
from settings_app.models import CompanyProfile

User = get_user_model()


class ExpenseModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testmanager',
            password='testpassword123',
            email='manager@tractor.com'
        )
        self.category = ExpenseCategory.objects.create(
            name='Diesel & Fuel Test',
            code='diesel-fuel-test',
            icon='fas fa-gas-pump',
            color='amber'
        )

    def test_category_slug_auto_generation(self):
        cat = ExpenseCategory.objects.create(name='Showroom Electricity')
        self.assertEqual(cat.code, 'showroom-electricity')

    def test_expense_voucher_number_sequencing(self):
        now = timezone.now().date()
        year_month = now.strftime('%Y%m')

        exp1 = Expense.objects.create(
            category=self.category,
            title='Diesel 20 Litres',
            amount=Decimal('1950.00'),
            expense_date=now,
            payment_mode='CASH',
            recorded_by=self.user
        )
        self.assertEqual(exp1.expense_number, f"EXP-{year_month}-0001")

        exp2 = Expense.objects.create(
            category=self.category,
            title='Showroom Floor Cleaning Supplies',
            amount=Decimal('450.00'),
            expense_date=now,
            payment_mode='UPI',
            recorded_by=self.user
        )
        self.assertEqual(exp2.expense_number, f"EXP-{year_month}-0002")

    def test_expense_str_representation(self):
        exp = Expense.objects.create(
            category=self.category,
            title='Tea and Refreshments',
            amount=Decimal('120.00'),
            recorded_by=self.user
        )
        self.assertIn('Tea and Refreshments', str(exp))
        self.assertIn('120.00', str(exp))


class ExpenseViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='adminuser',
            password='adminpassword123',
            email='admin@tractor.com'
        )
        self.client.force_login(self.user)

        self.company = CompanyProfile.objects.create(
            company_name='Mahindra Tractor Authorized Dealership',
            address_line1='Station Road',
            city='Pandharpur',
            district='Solapur',
            mobile_numbers='9876543210',
            email='info@mahindratractor.com',
            gstin_number='27ABCDE1234F1Z5'
        )

        self.cat1 = ExpenseCategory.objects.create(
            name='Showroom Rent Test',
            code='showroom-rent-test'
        )
        self.cat2 = ExpenseCategory.objects.create(
            name='Staff Wages Test',
            code='staff-wages-test'
        )

        self.exp1 = Expense.objects.create(
            category=self.cat1,
            title='October Showroom Rent',
            amount=Decimal('25000.00'),
            expense_date=timezone.now().date(),
            payment_mode='BANK_TRANSFER',
            payee_name='Landlord Shri Patil',
            payment_reference='HDFC001234987',
            recorded_by=self.user
        )
        self.exp2 = Expense.objects.create(
            category=self.cat2,
            title='Daily Helper Wages',
            amount=Decimal('1500.00'),
            expense_date=timezone.now().date(),
            payment_mode='CASH',
            payee_name='Suresh Pawar',
            recorded_by=self.user
        )

    def test_expense_list_view(self):
        response = self.client.get(reverse('expenses:expense_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Showroom Expenses Register')
        self.assertContains(response, 'EXP-')
        self.assertContains(response, '25,000')

    def test_expense_list_search_filter(self):
        response = self.client.get(reverse('expenses:expense_list') + '?q=Landlord')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'October Showroom Rent')
        self.assertNotContains(response, 'Daily Helper Wages')

    def test_expense_list_category_filter(self):
        response = self.client.get(reverse('expenses:expense_list') + f'?category={self.cat2.id}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Daily Helper Wages')
        self.assertNotContains(response, 'October Showroom Rent')

    def test_expense_create_view(self):
        post_data = {
            'category': self.cat1.id,
            'title': 'Electricity Bill October',
            'amount': '3200.00',
            'expense_date': timezone.now().date().strftime('%Y-%m-%d'),
            'payment_mode': 'UPI',
            'payee_name': 'MSEDCL',
            'payment_reference': 'UPI-987654321',
            'notes': 'Online electricity payment receipt',
        }
        response = self.client.post(reverse('expenses:expense_create'), post_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Expense.objects.filter(title='Electricity Bill October').exists())
        created_exp = Expense.objects.get(title='Electricity Bill October')
        self.assertEqual(created_exp.recorded_by, self.user)

    def test_expense_update_view(self):
        post_data = {
            'category': self.cat1.id,
            'title': 'October Showroom Rent Updated',
            'amount': '26000.00',
            'expense_date': self.exp1.expense_date.strftime('%Y-%m-%d'),
            'payment_mode': 'BANK_TRANSFER',
            'payee_name': 'Landlord Shri Patil',
            'payment_reference': 'HDFC001234987',
            'notes': 'Revised rent with yard charges',
        }
        response = self.client.post(reverse('expenses:expense_edit', args=[self.exp1.id]), post_data)
        self.assertEqual(response.status_code, 302)
        self.exp1.refresh_from_db()
        self.assertEqual(self.exp1.amount, Decimal('26000.00'))
        self.assertEqual(self.exp1.title, 'October Showroom Rent Updated')

    def test_expense_voucher_view(self):
        response = self.client.get(reverse('expenses:expense_voucher', args=[self.exp1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'DEBIT VOUCHER')
        self.assertContains(response, self.exp1.expense_number)
        self.assertContains(response, 'Mahindra Tractor')
        self.assertContains(response, 'Twenty Five Thousand')

    def test_expense_export_excel_csv(self):
        response = self.client.get(reverse('expenses:export_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        content = response.content.decode('utf-8')
        self.assertIn('Voucher No', content)
        self.assertIn('October Showroom Rent', content)
        self.assertIn('25000.00', content)

    def test_category_delete_protection_when_has_expenses(self):
        response = self.client.post(reverse('expenses:category_delete', args=[self.cat1.id]))
        self.assertEqual(response.status_code, 302)
        # Category should NOT be deleted because it has linked expenses
        self.assertTrue(ExpenseCategory.objects.filter(id=self.cat1.id).exists())

    def test_category_delete_success_when_empty(self):
        empty_cat = ExpenseCategory.objects.create(name='Unused Head', code='unused-head')
        response = self.client.post(reverse('expenses:category_delete', args=[empty_cat.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ExpenseCategory.objects.filter(id=empty_cat.id).exists())
