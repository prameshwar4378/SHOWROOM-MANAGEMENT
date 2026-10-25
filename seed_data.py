"""
Setup script to seed initial showroom data with clean generic placeholders:
- Default CompanyProfile (Generic showroom profile, easily editable in Settings)
- Primary Bank Detail (Configurable in Settings)
- GST Tax Slabs (12% Tractor, 18% Spares, 28%)
- Bill Number Sequences
- Sample Customer
- Default User (admin / admin123)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SHOWROOM_MANAGEMENT.settings')
django.setup()

from django.contrib.auth.models import User
from settings_app.models import CompanyProfile, BankDetail, GSTConfig, BillNumberSequence
from customers.models import Customer
from billing.models import Bill, BillItem

def seed():
    # 1. Admin User
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@showroom.local',
            'first_name': 'Showroom',
            'last_name': 'Admin',
            'is_staff': True,
            'is_superuser': True,
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print("[OK] Created admin user (username: admin / password: admin123)")
    else:
        print("[OK] Admin user already exists")

    # 2. Company Profile (Generic - managed from Settings)
    company = CompanyProfile.get_instance()
    company.company_name = 'Tractor & Machinery Showroom'
    company.tagline = 'Authorized Dealership & Service Center'
    company.address_line1 = 'Plot No. 101, Highway Road, Near Market Yard'
    company.city = 'Pune'
    company.taluka = 'Haveli'
    company.district = 'Pune'
    company.state = 'Maharashtra'
    company.pin_code = '411001'
    company.mobile_numbers = '9876543210, 9822000000'
    company.email = 'contact@dealership.com'
    company.gstin_number = '27AAAAA0000A1Z5'
    company.pan_number = 'AAAAA0000A'
    company.declaration_text = (
        "We declare that this invoice shows the actual price of the goods "
        "described and that all particulars are true and correct. Subject to local jurisdiction."
    )
    company.footer_text = 'This is Computer Generated Print'
    company.save()
    print(f"[OK] Company Profile initialized: {company.company_name} (Editable in Settings)")

    # 3. Bank Details
    bank = BankDetail.objects.filter(company=company).first()
    if not bank:
        bank = BankDetail.objects.create(
            company=company,
            bank_name='State Bank of India',
            branch_name='Main Branch',
            account_holder_name='Tractor & Machinery Showroom',
            account_number='123456789012',
            ifsc_code='SBIN0001234',
            is_primary=True,
            is_active=True,
        )
    else:
        bank.bank_name = 'State Bank of India'
        bank.branch_name = 'Main Branch'
        bank.account_holder_name = company.company_name
        bank.account_number = '123456789012'
        bank.ifsc_code = 'SBIN0001234'
        bank.is_primary = True
        bank.is_active = True
        bank.save()
    print("[OK] Primary Bank Detail initialized (Editable in Settings)")

    # 4. GST Configs
    gst_12, _ = GSTConfig.objects.get_or_create(
        name='GST 12% (Tractor)',
        defaults={
            'hsn_code': '8701',
            'cgst_rate': 6.00,
            'sgst_rate': 6.00,
            'igst_rate': 12.00,
            'is_active': True,
        }
    )
    gst_18, _ = GSTConfig.objects.get_or_create(
        name='GST 18% (Implements & Spares)',
        defaults={
            'hsn_code': '8708',
            'cgst_rate': 9.00,
            'sgst_rate': 9.00,
            'igst_rate': 18.00,
            'is_active': True,
        }
    )
    print("[OK] GST Tax Slabs (12% and 18%)")

    # 5. Bill Sequences
    fy = BillNumberSequence.calculate_financial_year()
    qt_seq, _ = BillNumberSequence.objects.get_or_create(
        bill_type='QUOTATION',
        financial_year=fy,
        defaults={'prefix': 'QT-', 'last_number': 100}
    )
    ti_seq, _ = BillNumberSequence.objects.get_or_create(
        bill_type='TAX_INVOICE',
        financial_year=fy,
        defaults={'prefix': 'TI-', 'last_number': 0}
    )
    mm_seq, _ = BillNumberSequence.objects.get_or_create(
        bill_type='MARGIN_MONEY',
        financial_year=fy,
        defaults={'prefix': 'MM-', 'last_number': 0}
    )
    dc_seq, _ = BillNumberSequence.objects.get_or_create(
        bill_type='DELIVERY_CHALLAN',
        financial_year=fy,
        defaults={'prefix': 'DC-', 'last_number': 0}
    )
    print(f"[OK] Bill Sequences initialized for FY {fy}")

    # 6. Sample Customer
    customer = Customer.objects.first()
    if not customer:
        customer = Customer.objects.create(
            full_name='Rajesh Ramesh Patil',
            village='Shivaji Nagar',
            taluka='Haveli',
            district='Pune',
            state='Maharashtra',
            mobile_primary='9876543210',
            bank_name='State Bank of India',
            bank_branch='Main Branch',
            reference_by='Direct Walk-in',
        )
    print(f"[OK] Sample Customer: {customer.full_name}")

    # 7. Sample Bill
    if not Bill.objects.exists():
        q_bill = Bill.objects.create(
            bill_type='QUOTATION',
            customer=customer,
            is_gst_bill=False,
            created_by=admin_user,
            status='FINAL',
        )
        BillItem.objects.create(
            bill=q_bill,
            sr_no=1,
            item_description='Utility Tractor 45 HP 4WD',
            hsn_code='8701',
            quantity=1,
            unit_price=595000.00,
            discount=0.00,
            amount=595000.00
        )
        q_bill.calculate_totals(save=True)
        print(f"[OK] Sample Quotation created: #{q_bill.bill_number} totaling Rs. {q_bill.grand_total}")

if __name__ == '__main__':
    seed()
