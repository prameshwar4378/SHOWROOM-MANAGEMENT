from django import template
from decimal import Decimal
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def param_replace(context, **kwargs):
    """
    Preserves all current GET query parameters while replacing or removing specific keys.
    Usage:
        href="?{% param_replace page=page_obj.next_page_number %}"
        href="?{% param_replace page=1 page_size=25 %}"
    """
    request = context.get('request')
    if not request or not hasattr(request, 'GET'):
        return ''
    query_params = request.GET.copy()
    for key, value in kwargs.items():
        if value is None or value == '':
            query_params.pop(key, None)
        else:
            query_params[key] = str(value)
    return mark_safe(query_params.urlencode())


@register.filter
def indian_number_format(value):
    """
    Formats a numeric value into the Indian comma formatting (Lakhs, Crores).
    E.g. 1250000 -> 12,50,000.00
    """
    if value is None or value == '':
        return '0.00'
    try:
        val = Decimal(str(value))
        is_negative = val < 0
        val = abs(val)
        parts = f"{val:.2f}".split('.')
        integer_part = parts[0]
        decimal_part = parts[1]

        if len(integer_part) <= 3:
            res = integer_part
        else:
            last_three = integer_part[-3:]
            remaining = integer_part[:-3]
            # Group in 2s
            chunks = []
            while remaining:
                chunks.append(remaining[-2:])
                remaining = remaining[:-2]
            chunks.reverse()
            res = ",".join(chunks) + "," + last_three

        formatted = f"{'-' if is_negative else ''}{res}.{decimal_part}"
        return formatted
    except Exception:
        return str(value)
