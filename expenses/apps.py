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
            {'name': 'Showroom & Yard Rent', 'code': 'showroom-rent', 'icon': 'fas fa-building', 'color': 'indigo'},
            {'name': 'Staff Salaries & Wages', 'code': 'staff-salaries', 'icon': 'fas fa-users', 'color': 'emerald'},
            {'name': 'Diesel & Fuel', 'code': 'diesel-fuel', 'icon': 'fas fa-gas-pump', 'color': 'amber'},
            {'name': 'Electricity & Power', 'code': 'electricity-bill', 'icon': 'fas fa-bolt', 'color': 'yellow'},
            {'name': 'Vehicle Transport & Freight', 'code': 'transport-freight', 'icon': 'fas fa-truck-moving', 'color': 'blue'},
            {'name': 'Tea, Hospitality & Office', 'code': 'tea-hospitality', 'icon': 'fas fa-coffee', 'color': 'rose'},
            {'name': 'Marketing & Advertising', 'code': 'marketing-banners', 'icon': 'fas fa-bullhorn', 'color': 'purple'},
            {'name': 'Workshop Consumables & Tools', 'code': 'workshop-consumables', 'icon': 'fas fa-tools', 'color': 'teal'},
            {'name': 'Maintenance & Repairs', 'code': 'maintenance-repairs', 'icon': 'fas fa-wrench', 'color': 'cyan'},
            {'name': 'Bank Charges & Interest', 'code': 'bank-charges', 'icon': 'fas fa-university', 'color': 'slate'},
            {'name': 'Printing & Stationery', 'code': 'stationery-courier', 'icon': 'fas fa-print', 'color': 'orange'},
            {'name': 'Miscellaneous Expenses', 'code': 'miscellaneous', 'icon': 'fas fa-receipt', 'color': 'slate'},
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
