from django.apps import AppConfig
from django.db.models.signals import post_migrate


def seed_default_categories(sender, **kwargs):
    if sender.name != 'expenses':
        return
    try:
        from .models import ExpenseCategory
        if ExpenseCategory.objects.exists():
            return

        defaults = [
            {'name': 'Showroom & Yard Rent (भाडे)', 'code': 'showroom-rent', 'icon': 'fas fa-building', 'color': 'indigo'},
            {'name': 'Staff Salaries & Wages (पगार व मजुरी)', 'code': 'staff-salaries', 'icon': 'fas fa-users', 'color': 'emerald'},
            {'name': 'Diesel & Fuel (डिझेल व इंधन खर्च)', 'code': 'diesel-fuel', 'icon': 'fas fa-gas-pump', 'color': 'amber'},
            {'name': 'Electricity & Power (वीज बिल)', 'code': 'electricity-bill', 'icon': 'fas fa-bolt', 'color': 'yellow'},
            {'name': 'Vehicle Transport & Freight (वाहतूक खर्च)', 'code': 'transport-freight', 'icon': 'fas fa-truck-moving', 'color': 'blue'},
            {'name': 'Tea, Hospitality & Office (चहापान व ऑफिस खर्च)', 'code': 'tea-hospitality', 'icon': 'fas fa-coffee', 'color': 'rose'},
            {'name': 'Marketing & Banners (जाहिरात व बॅनर)', 'code': 'marketing-banners', 'icon': 'fas fa-bullhorn', 'color': 'purple'},
            {'name': 'Workshop Consumables & Tools (वर्कशॉप साहित्य)', 'code': 'workshop-consumables', 'icon': 'fas fa-tools', 'color': 'teal'},
            {'name': 'Maintenance & Repairs (दुरुस्ती व मेंटेनन्स)', 'code': 'maintenance-repairs', 'icon': 'fas fa-wrench', 'color': 'cyan'},
            {'name': 'Bank Charges & Interest (बँक व्याज व चार्जेस)', 'code': 'bank-charges', 'icon': 'fas fa-university', 'color': 'slate'},
            {'name': 'Printing & Stationery (स्टेशनरी व कुरिअर)', 'code': 'stationery-courier', 'icon': 'fas fa-print', 'color': 'orange'},
            {'name': 'Miscellaneous Expenses (इतर किरकोळ खर्च)', 'code': 'miscellaneous', 'icon': 'fas fa-receipt', 'color': 'slate'},
        ]

        for item in defaults:
            ExpenseCategory.objects.get_or_create(
                code=item['code'],
                defaults={
                    'name': item['name'],
                    'icon': item['icon'],
                    'color': item['color'],
                }
            )
    except Exception:
        # Avoid crashing during migrations if tables are not ready yet
        pass


class ExpensesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'expenses'
    verbose_name = 'Showroom Expenses'

    def ready(self):
        post_migrate.connect(seed_default_categories, sender=self)
