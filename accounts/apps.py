"""
App configuration for accounts application.
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration for accounts app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'Accounts & User Management'

    def ready(self):
        """Import signal handlers on app readiness."""
        try:
            import accounts.models  # noqa: F401
        except ImportError:
            pass
