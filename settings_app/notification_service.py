"""
Core notification engine for Tractor Showroom Management System.
Handles automated WhatsApp and SMS generation, Indian phone number normalization,
and multi-gateway dispatch (Simulator, WhatsApp Cloud API, Webhooks) with audit logging.
"""

import json
import logging
import re
import urllib.parse
import urllib.request
from decimal import Decimal
from django.utils import timezone

from .models import CompanyProfile, NotificationConfig, NotificationLog

logger = logging.getLogger(__name__)


def normalize_indian_mobile(mobile_str):
    """
    Standardize Indian mobile numbers to 12-digit format with '91' country code.
    Examples:
        '9876543210'      -> '919876543210'
        '+91 98765 43210' -> '919876543210'
        '09876543210'     -> '919876543210'
        '919876543210'    -> '919876543210'
    Returns normalized string, or None if invalid.
    """
    if not mobile_str:
        return None
    digits = re.sub(r'\D', '', str(mobile_str))
    if len(digits) == 10 and digits[0] in '6789':
        return f"91{digits}"
    elif len(digits) == 11 and digits.startswith('0') and digits[1] in '6789':
        return f"91{digits[1:]}"
    elif len(digits) == 12 and digits.startswith('91') and digits[2] in '6789':
        return digits
    return None


def format_currency_in(amount):
    """Format decimal amount into Indian rupee string with Indian comma grouping (lakhs, crores)."""
    try:
        val = Decimal(str(amount or 0)).quantize(Decimal('0.01'))
        is_neg = val < Decimal('0.00')
        abs_val = abs(val)
        parts = f"{abs_val:.2f}".split('.')
        integer_part, decimal_part = parts[0], parts[1]

        if len(integer_part) > 3:
            last3 = integer_part[-3:]
            rest = integer_part[:-3]
            groups = []
            while len(rest) > 2:
                groups.insert(0, rest[-2:])
                rest = rest[:-2]
            if rest:
                groups.insert(0, rest)
            groups.append(last3)
            formatted = f"{','.join(groups)}.{decimal_part}"
        else:
            formatted = f"{integer_part}.{decimal_part}"

        return f"-{formatted}" if is_neg else formatted
    except Exception:
        return "0.00"

format_inr = format_currency_in


def build_payment_receipt_message(payment):
    """
    Generate WhatsApp text for payment receipt acknowledgment.
    Returns tuple: (recipient_mobile, message_text)
    """
    company = CompanyProfile.get_instance()
    cust = payment.customer
    showroom_phone = company.mobile_numbers or "our showroom"
    balance_due = cust.outstanding_balance if cust else Decimal('0.00')
    recipient = normalize_indian_mobile(cust.mobile_primary if cust else '')

    msg = (
        f"🙏 Namaskar {cust.full_name if cust else 'Customer'} ji,\n"
        f"Greetings from {company.company_name or 'Showroom Management'}.\n\n"
        f"✅ Your payment has been received successfully!\n"
        f"• Receipt No: {payment.receipt_number}\n"
        f"• Amount Received: ₹{format_currency_in(payment.amount)}\n"
        f"• Date: {payment.payment_date.strftime('%d-%b-%Y') if payment.payment_date else ''}\n"
        f"• Payment Mode: {payment.get_payment_mode_display()}\n"
        f"• Remaining Balance Due: ₹{format_currency_in(balance_due)}\n\n"
        f"Thank you for your trust and business!\n"
        f"📞 Contact: {showroom_phone}"
    )
    return recipient, msg


def build_invoice_alert_message(bill):
    """
    Generate WhatsApp text for approved invoice or delivery challan.
    Returns tuple: (recipient_mobile, message_text)
    """
    company = CompanyProfile.get_instance()
    cust = bill.customer
    showroom_phone = company.mobile_numbers or "our showroom"
    items_desc = ", ".join(item.item_description for item in bill.items.all()[:2]) or "Tractor & Equipment"
    recipient = normalize_indian_mobile(cust.mobile_primary if cust else '')

    msg = (
        f"🙏 Namaskar {cust.full_name if cust else 'Customer'} ji,\n"
        f"Greetings from {company.company_name or 'Showroom Management'}.\n\n"
        f"🚜 Your {bill.get_bill_type_display()} has been generated.\n"
        f"• Document No: {bill.bill_number}\n"
        f"• Date: {bill.bill_date.strftime('%d-%b-%Y') if bill.bill_date else ''}\n"
        f"• Description: {items_desc}\n"
        f"• Total Invoice Value: ₹{format_currency_in(bill.grand_total)}\n\n"
        f"Thank you for choosing {company.company_name}!\n"
        f"📞 Inquiries: {showroom_phone}"
    )
    return recipient, msg


def build_overdue_reminder_message(customer, due=None):
    """
    Generate friendly and respectful reminder message for pending dues.
    Returns tuple: (recipient_mobile, message_text)
    """
    company = CompanyProfile.get_instance()
    showroom_phone = company.mobile_numbers or "our showroom office"
    if due is None:
        due = customer.outstanding_balance
    recipient = normalize_indian_mobile(customer.mobile_primary if customer else '')

    msg = (
        f"🙏 Namaskar {customer.full_name} ji,\n"
        f"Greetings from {company.company_name or 'Showroom Management'}.\n\n"
        f"⚠️ This is a gentle reminder regarding your outstanding showroom account balance.\n"
        f"• Total Billed: ₹{format_currency_in(customer.total_billed)}\n"
        f"• Total Paid: ₹{format_currency_in(customer.total_paid)}\n"
        f"• Current Balance Due: ₹{format_currency_in(due)}\n\n"
        f"Kindly arrange for payment settlement at your earliest convenience.\n"
        f"If payment has already been remitted, please disregard this message.\n\n"
        f"📞 For queries: {showroom_phone}"
    )
    return recipient, msg


def send_notification(
    recipient=None,
    message=None,
    notification_type="CUSTOM",
    user=None,
    entity_id="",
    customer=None,
    recipient_name="",
    recipient_mobile="",
    message_type=None,
    message_text="",
    sent_by=None
):
    """
    Central dispatcher for customer communications.
    Safely dispatches message through configured provider and records audit log.
    Never raises unhandled exceptions to calling business views.
    Returns NotificationLog instance or None if service disabled.
    """
    config = NotificationConfig.get_instance()
    if not config.is_enabled:
        return None

    # Unify polymorphic argument names
    raw_mobile = recipient or recipient_mobile or (customer.mobile_primary if customer else "")
    norm_mobile = normalize_indian_mobile(raw_mobile)
    name = recipient_name or (customer.full_name if customer else "Customer")
    final_msg = message or message_text or ""
    final_type = message_type or notification_type or "CUSTOM"
    final_user = user or sent_by
    provider_name = config.provider

    if not norm_mobile:
        log = NotificationLog.objects.create(
            customer=customer,
            recipient_name=name,
            recipient_mobile=raw_mobile or "UNKNOWN",
            message_type=final_type,
            message_text=final_msg,
            status='FAILED',
            response_payload="Invalid mobile number format (must be 10-digit Indian mobile number).",
            entity_id=entity_id or "",
            provider=provider_name,
            sent_by=final_user
        )
        return log

    try:
        if config.provider == 'SIMULATOR':
            log = NotificationLog.objects.create(
                customer=customer,
                recipient_name=name,
                recipient_mobile=norm_mobile,
                message_type=final_type,
                message_text=final_msg,
                status='SIMULATED',
                response_payload="Successfully simulated in test/development mode without gateway charges.",
                entity_id=entity_id or "",
                provider=provider_name,
                sent_by=final_user
            )
            return log

        if config.provider == 'LOCAL_WHATSAPP':
            endpoint = (config.api_endpoint or 'http://localhost:3000/send').strip()
            if not endpoint:
                endpoint = 'http://localhost:3000/send'
            payload = {
                "to": norm_mobile,
                "message": final_msg
            }
            req_data = json.dumps(payload).encode('utf-8')
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            req = urllib.request.Request(endpoint, data=req_data, headers=headers, method='POST')
            try:
                with urllib.request.urlopen(req, timeout=15) as response:
                    resp_text = response.read().decode('utf-8')
            except urllib.error.URLError as err:
                if "refused" in str(err).lower() or "10061" in str(err):
                    raise ConnectionError(
                        "Local WhatsApp Bridge is not running on your PC. Please run 'start_whatsapp_bridge.bat' to start the bridge, or check port 3000."
                    )
                raise

            log = NotificationLog.objects.create(
                customer=customer,
                recipient_name=name,
                recipient_mobile=norm_mobile,
                message_type=final_type,
                message_text=final_msg,
                status='SENT',
                response_payload=resp_text,
                entity_id=entity_id or "",
                provider='LOCAL_WHATSAPP',
                sent_by=final_user
            )
            return log

        is_waapi = (config.provider == 'WAAPI') or (config.api_endpoint and 'waapi.app' in config.api_endpoint.lower())

        if is_waapi:
            if not config.api_endpoint or not config.api_key_or_token:
                raise ValueError("WaAPI endpoint URL and API Access Token are required in settings.")

            # WaAPI format: chatId is '<number>@c.us'
            # If sending to the registered trial number, match exact trial format
            if norm_mobile.endswith("7776824564") or raw_mobile == "7776824564":
                chat_id = "7776824564@c.us"
            else:
                chat_id = f"{norm_mobile}@c.us"

            payload = {
                "chatId": chat_id,
                "message": final_msg
            }
            req_data = json.dumps(payload).encode('utf-8')
            headers = {
                "Authorization": f"Bearer {config.api_key_or_token.strip()}",
                "Content-Type": "application/json",
                "accept": "application/json"
            }
            req = urllib.request.Request(config.api_endpoint.strip(), data=req_data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=12) as response:
                resp_text = response.read().decode('utf-8')

            log = NotificationLog.objects.create(
                customer=customer,
                recipient_name=name,
                recipient_mobile=norm_mobile,
                message_type=final_type,
                message_text=final_msg,
                status='SENT',
                response_payload=resp_text,
                entity_id=entity_id or "",
                provider='WAAPI' if config.provider == 'WAAPI' else provider_name,
                sent_by=final_user
            )
            return log

        elif config.provider == 'WHATSAPP_CLOUD':
            if not config.api_endpoint or not config.api_key_or_token:
                raise ValueError("WhatsApp Cloud API endpoint or access token missing in configuration.")

            payload = {
                "messaging_product": "whatsapp",
                "to": norm_mobile,
                "type": "text",
                "text": {"preview_url": False, "body": final_msg}
            }
            req_data = json.dumps(payload).encode('utf-8')
            headers = {
                "Authorization": f"Bearer {config.api_key_or_token}",
                "Content-Type": "application/json"
            }
            req = urllib.request.Request(config.api_endpoint, data=req_data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=10) as response:
                resp_text = response.read().decode('utf-8')

            log = NotificationLog.objects.create(
                customer=customer,
                recipient_name=name,
                recipient_mobile=norm_mobile,
                message_type=final_type,
                message_text=final_msg,
                status='SENT',
                response_payload=resp_text,
                entity_id=entity_id or "",
                provider=provider_name,
                sent_by=final_user
            )
            return log

        elif config.provider in ('CUSTOM_WEBHOOK', 'FAST2SMS'):
            if not config.api_endpoint:
                raise ValueError("Webhook API endpoint missing in configuration.")

            payload = {
                "phone": norm_mobile,
                "name": name,
                "message": final_msg,
                "type": final_type,
                "token": config.api_key_or_token or ""
            }
            req_data = urllib.parse.urlencode(payload).encode('utf-8')
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            req = urllib.request.Request(config.api_endpoint, data=req_data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=10) as response:
                resp_text = response.read().decode('utf-8')

            log = NotificationLog.objects.create(
                customer=customer,
                recipient_name=name,
                recipient_mobile=norm_mobile,
                message_type=final_type,
                message_text=final_msg,
                status='SENT',
                response_payload=resp_text,
                entity_id=entity_id or "",
                provider=provider_name,
                sent_by=final_user
            )
            return log

        else:
            raise ValueError(f"Unsupported gateway provider: {config.provider}")

    except urllib.error.HTTPError as exc:
        raw_error = ""
        try:
            raw_error = exc.read().decode('utf-8', errors='ignore')
            data = json.loads(raw_error)
            detail = data.get('message') or data.get('error', {}).get('message') or raw_error
            if "The trial phone number of your account does not match" in str(detail):
                err_msg = (
                    "WaAPI Trial Limitation: Your WaAPI trial instance can only send messages to the registered trial number (7776824564). "
                    "Please upgrade your WaAPI plan on waapi.app to send messages to any customer number."
                )
            else:
                err_msg = f"HTTP {exc.code}: {detail}"
        except Exception:
            err_msg = f"HTTP {exc.code}: {exc.reason} ({raw_error or 'No response'})"

        logger.warning("Notification dispatch failed to %s: %s", norm_mobile, err_msg)
        log = NotificationLog.objects.create(
            customer=customer,
            recipient_name=name,
            recipient_mobile=norm_mobile,
            message_type=final_type,
            message_text=final_msg,
            status='FAILED',
            response_payload=f"Error: {err_msg}",
            entity_id=entity_id or "",
            provider=provider_name,
            sent_by=final_user
        )
        return log

    except Exception as exc:
        err_msg = str(exc)
        logger.warning("Notification dispatch failed to %s: %s", norm_mobile, err_msg)
        log = NotificationLog.objects.create(
            customer=customer,
            recipient_name=name,
            recipient_mobile=norm_mobile,
            message_type=final_type,
            message_text=final_msg,
            status='FAILED',
            response_payload=f"Error: {err_msg}",
            entity_id=entity_id or "",
            provider=provider_name,
            sent_by=final_user
        )
        return log
