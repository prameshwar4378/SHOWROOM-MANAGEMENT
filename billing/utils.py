"""
Utility functions for the billing application.
Includes custom Indian currency number-to-words converter.
"""
from decimal import Decimal, ROUND_HALF_UP


def number_to_words_indian(number):
    """
    Converts a number (int, float, Decimal) into Indian currency words.

    Examples:
        595000 -> "Rupees Five Lakh Ninety Five Thousand Only"
        125500.50 -> "Rupees One Lakh Twenty Five Thousand Five Hundred and Fifty Paise Only"
        1000000 -> "Rupees Ten Lakh Only"
        0 -> "Rupees Zero Only"

    Handles: ones, tens, hundreds, thousands, lakhs, crores.
    Prefix: "Rupees ", Suffix: " Only".
    """
    if number is None:
        return "Rupees Zero Only"

    try:
        dec_val = Decimal(str(number)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except Exception:
        return "Rupees Zero Only"

    if dec_val < Decimal('0.00'):
        return "Minus " + number_to_words_indian(-dec_val)

    ones = [
        "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
        "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
        "Seventeen", "Eighteen", "Nineteen"
    ]
    tens = [
        "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"
    ]

    def two_digits_to_words(n):
        if n < 20:
            return ones[n]
        t = tens[n // 10]
        o = ones[n % 10]
        return f"{t} {o}".strip()

    def three_digits_to_words(n):
        h = n // 100
        rem = n % 100
        parts = []
        if h > 0:
            parts.append(f"{ones[h]} Hundred")
        if rem > 0:
            parts.append(two_digits_to_words(rem))
        return " ".join(parts)

    def whole_number_to_words(n):
        if n == 0:
            return "Zero"

        parts = []
        crores = n // 10000000
        rem = n % 10000000
        lakhs = rem // 100000
        rem = rem % 100000
        thousands = rem // 1000
        rem = rem % 1000
        hundreds = rem // 100
        rest = rem % 100

        if crores > 0:
            parts.append(f"{whole_number_to_words(crores)} Crore")
        if lakhs > 0:
            parts.append(f"{two_digits_to_words(lakhs)} Lakh")
        if thousands > 0:
            parts.append(f"{two_digits_to_words(thousands)} Thousand")
        if hundreds > 0:
            parts.append(f"{ones[hundreds]} Hundred")
        if rest > 0:
            parts.append(two_digits_to_words(rest))

        return " ".join(parts)

    rupees = int(dec_val)
    paise = int((dec_val - Decimal(rupees)) * 100)

    rupees_str = whole_number_to_words(rupees) if rupees > 0 else ("Zero" if paise == 0 else "")
    paise_str = two_digits_to_words(paise) if paise > 0 else ""

    if rupees_str and paise_str:
        return f"Rupees {rupees_str} and {paise_str} Paise Only"
    elif rupees_str:
        return f"Rupees {rupees_str} Only"
    elif paise_str:
        return f"{paise_str} Paise Only"
    else:
        return "Rupees Zero Only"


def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access
    static and media files directly from the local file system.
    """
    import os
    from django.conf import settings
    from django.contrib.staticfiles import finders

    if not uri:
        return ""

    # If already an existing absolute filesystem path
    try:
        if os.path.isfile(uri):
            return uri
    except Exception:
        pass

    # Media files (e.g., /media/logos/image.png)
    if settings.MEDIA_URL and uri.startswith(settings.MEDIA_URL):
        rel_path = uri.replace(settings.MEDIA_URL, "", 1).lstrip('/\\')
        path = os.path.normpath(os.path.join(settings.MEDIA_ROOT, rel_path))
        if os.path.isfile(path):
            return path

    # Static files (e.g., /static/img/logo.png)
    if settings.STATIC_URL and uri.startswith(settings.STATIC_URL):
        rel_path = uri.replace(settings.STATIC_URL, "", 1).lstrip('/\\')
        path = os.path.normpath(os.path.join(settings.STATIC_ROOT, rel_path)) if settings.STATIC_ROOT else None
        if not path or not os.path.isfile(path):
            found = finders.find(rel_path)
            if found:
                path = found
        if path and os.path.isfile(path):
            return path

    return uri

