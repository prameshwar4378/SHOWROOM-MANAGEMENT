"""
Context processors for settings_app.

Exposes company profile information globally to all templates in the Tractor Showroom Management System.
"""

import logging
from django.db import OperationalError, ProgrammingError
from .models import CompanyProfile

logger = logging.getLogger(__name__)


def company_info(request):
    """
    Context processor that injects the singleton CompanyProfile into template context.
    Safely handles unmigrated or initial database state.
    """
    try:
        company = CompanyProfile.get_instance()
    except (OperationalError, ProgrammingError, Exception) as exc:
        logger.debug("CompanyProfile not yet available in database: %s", exc)
        company = None

    return {
        'company': company,
    }
