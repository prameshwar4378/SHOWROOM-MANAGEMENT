import io
import logging
import re
import urllib.parse
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q, Sum, Count, Subquery, OuterRef, Value, DecimalField, F
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import ListView, DetailView, DeleteView
from xhtml2pdf import pisa

from .forms import PaymentForm, PaymentAllocationForm
from .models import Payment, PaymentAllocation
from customers.models import Customer
from billing.models import Bill
from billing.utils import number_to_words_indian, link_callback
from settings_app.models import CompanyProfile, NotificationConfig
from settings_app.notification_service import (
    normalize_indian_mobile,
    build_payment_receipt_message,
    build_overdue_reminder_message,
    send_notification,
)

logger = logging.getLogger(__name__)


class PaymentListView(LoginRequiredMixin, ListView):
    """
    Paginated list of all customer payments with search and filtering.
    """
    model = Payment
    template_name = 'payments/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 15

    def get_paginate_by(self, queryset):
        page_size = self.request.GET.get('page_size')
        if page_size and page_size.isdigit():
            size = int(page_size)
            if 5 <= size <= 100:
                return size
        return self.paginate_by

    def get_queryset(self):
        qs = Payment.objects.select_related('customer').all().order_by('-payment_date', '-created_at')
        q = self.request.GET.get('q', '').strip()
        mode = self.request.GET.get('mode', '').strip()
        purpose = self.request.GET.get('purpose', '').strip()

        if q:
            qs = qs.filter(
                Q(receipt_number__icontains=q) |
                Q(customer__full_name__icontains=q) |
                Q(customer__mobile_primary__icontains=q) |
                Q(reference_number__icontains=q) |
                Q(cheque_number__icontains=q)
            )
        if mode:
            qs = qs.filter(payment_mode=mode)
        if purpose:
            qs = qs.filter(purpose=purpose)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['current_page_size'] = self.get_paginate_by(self.get_queryset())
        context['search_query'] = self.request.GET.get('q', '')
        context['current_mode'] = self.request.GET.get('mode', '')
        context['current_purpose'] = self.request.GET.get('purpose', '')
        context['modes'] = Payment.PAYMENT_MODE_CHOICES
        context['purposes'] = Payment.PURPOSE_CHOICES

        # KPI Metrics optimized via single database aggregate query
        stats = Payment.objects.aggregate(
            total_count=Count('id'),
            total_collected_sum=Sum('amount'),
            cash_count=Count('id', filter=Q(payment_mode='CASH')),
            cash_sum=Sum('amount', filter=Q(payment_mode='CASH')),
            upi_count=Count('id', filter=Q(payment_mode='UPI')),
            upi_sum=Sum('amount', filter=Q(payment_mode='UPI')),
            bank_count=Count('id', filter=Q(payment_mode__in=['BANK_TRANSFER', 'NEFT_RTGS'])),
            bank_sum=Sum('amount', filter=Q(payment_mode__in=['BANK_TRANSFER', 'NEFT_RTGS'])),
        )

        alloc_sq = PaymentAllocation.objects.filter(
            payment=OuterRef('pk')
        ).values('payment').annotate(tot=Sum('allocated_amount')).values('tot')

        unalloc_stats = (
            Payment.objects.annotate(
                allocated=Coalesce(Subquery(alloc_sq), Value(Decimal('0.00')), output_field=DecimalField())
            )
            .annotate(unallocated=F('amount') - F('allocated'))
            .filter(unallocated__gt=Decimal('0.00'))
            .aggregate(cnt=Count('id'), total=Sum('unallocated'))
        )

        context['total_payments_count'] = stats['total_count'] or 0
        context['total_collected_sum'] = stats['total_collected_sum'] or Decimal('0.00')
        context['cash_count'] = stats['cash_count'] or 0
        context['cash_sum'] = stats['cash_sum'] or Decimal('0.00')
        context['upi_count'] = stats['upi_count'] or 0
        context['upi_sum'] = stats['upi_sum'] or Decimal('0.00')
        context['bank_count'] = stats['bank_count'] or 0
        context['bank_sum'] = stats['bank_sum'] or Decimal('0.00')
        context['unallocated_count'] = unalloc_stats['cnt'] or 0
        context['unallocated_sum'] = unalloc_stats['total'] or Decimal('0.00')

        return context


class PaymentDeletePermissionMixin(UserPassesTestMixin):
    """Restricts payment and allocation deletion to Administrators and Managers."""
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return hasattr(user, 'profile') and (user.profile.is_admin or user.profile.is_manager)

    def handle_no_permission(self):
        messages.error(self.request, "Administrator or Manager privileges are required to delete payment records.")
        return redirect('payments:payment_list')


class PaymentCreateView(LoginRequiredMixin, View):
    """
    Manually add/receive money into a customer's account.
    """
    template_name = 'payments/payment_form.html'

    def get(self, request, *args, **kwargs):
        initial = {}
        customer_id = request.GET.get('customer')
        if customer_id:
            try:
                initial['customer'] = Customer.objects.get(pk=customer_id)
            except Customer.DoesNotExist:
                pass

        form = PaymentForm(initial=initial)
        return render(request, self.template_name, {
            'form': form,
            'is_edit': False,
            'page_title': 'Receive / Add Payment',
        })

    def post(self, request, *args, **kwargs):
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.received_by = request.user
            payment.save()
            messages.success(request, f"Payment '{payment.receipt_number}' of ₹{payment.amount} recorded for {payment.customer.full_name} successfully!")

            # Auto-send WhatsApp/SMS payment receipt if enabled
            config = NotificationConfig.get_instance()
            if config.is_enabled and config.auto_send_payment_receipt:
                try:
                    recipient, message = build_payment_receipt_message(payment)
                    log_entry = send_notification(
                        recipient=recipient,
                        message=message,
                        notification_type='PAYMENT_RECEIPT',
                        user=request.user,
                        entity_id=payment.receipt_number
                    )
                    if log_entry and log_entry.status in ('SENT', 'SIMULATED'):
                        messages.info(request, f"WhatsApp / SMS receipt sent to {recipient}.")
                except Exception as e:
                    logger.warning(f"Could not auto-send payment receipt: {e}")

            # Safe redirect check
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect('payments:payment_detail', pk=payment.pk)

        return render(request, self.template_name, {
            'form': form,
            'is_edit': False,
            'page_title': 'Receive / Add Payment',
        })


class PaymentDetailView(LoginRequiredMixin, DetailView):
    """
    View payment receipt and manage allocations to customer's bills.
    """
    model = Payment
    template_name = 'payments/payment_detail.html'
    context_object_name = 'payment'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment = self.object
        context['company'] = CompanyProfile.get_instance()
        context['allocations'] = payment.allocations.select_related('bill').all()
        context['allocation_form'] = PaymentAllocationForm(payment=payment)

        # Customer's unpaid tax invoices for easy allocation
        context['unpaid_bills'] = [
            b for b in Bill.objects.filter(customer=payment.customer, bill_type='TAX_INVOICE').exclude(status='CANCELLED')
            if b.balance_due > Decimal('0.00')
        ]
        return context


class PaymentSendNotificationView(LoginRequiredMixin, View):
    """
    Manual trigger to send or re-send payment receipt via WhatsApp / SMS.
    """
    def post(self, request, pk, *args, **kwargs):
        payment = get_object_or_404(Payment, pk=pk)
        try:
            recipient, message = build_payment_receipt_message(payment)
            log_entry = send_notification(
                recipient=recipient,
                message=message,
                notification_type='PAYMENT_RECEIPT',
                user=request.user,
                entity_id=payment.receipt_number
            )
            if log_entry.status == 'SENT':
                messages.success(request, f"Payment receipt sent to {recipient} via WhatsApp/SMS successfully!")
            elif log_entry.status == 'SIMULATED':
                messages.info(request, f"Payment receipt simulated for {recipient} (Simulator mode active).")
            else:
                messages.warning(request, f"Delivery warning: {log_entry.error_message}")
        except ValueError as ve:
            messages.error(request, str(ve))
        except Exception as e:
            logger.error(f"Error dispatching payment receipt notification: {e}", exc_info=True)
            messages.error(request, f"Failed to send notification: {e}")

        return redirect('payments:payment_detail', pk=payment.pk)


class PaymentDeleteView(LoginRequiredMixin, PaymentDeletePermissionMixin, DeleteView):
    """Delete a payment entry."""
    model = Payment
    template_name = 'payments/payment_confirm_delete.html'
    success_url = reverse_lazy('payments:payment_list')

    def form_valid(self, form):
        payment = self.get_object()
        messages.success(self.request, f"Payment receipt '{payment.receipt_number}' was deleted.")
        return super().form_valid(form)


class PaymentAllocationCreateView(LoginRequiredMixin, View):
    """
    Allocate payment amount to a specific bill.
    """
    def post(self, request, pk, *args, **kwargs):
        payment = get_object_or_404(Payment, pk=pk)
        form = PaymentAllocationForm(request.POST, payment=payment)

        if form.is_valid():
            alloc = form.save(commit=False)
            alloc.payment = payment
            alloc.allocated_by = request.user
            try:
                alloc.save()
                messages.success(request, f"Successfully allocated ₹{alloc.allocated_amount} to Bill '{alloc.bill.bill_number}'!")
            except Exception as e:
                messages.error(request, f"Could not allocate: {e}")
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, f"{err}")

        return redirect('payments:payment_detail', pk=payment.pk)


class PaymentAllocationDeleteView(LoginRequiredMixin, PaymentDeletePermissionMixin, View):
    """
    Remove an existing allocation.
    """
    def post(self, request, pk, *args, **kwargs):
        alloc = get_object_or_404(PaymentAllocation, pk=pk)
        payment_pk = alloc.payment_id
        alloc.delete()
        messages.success(request, "Allocation removed successfully.")
        return redirect('payments:payment_detail', pk=payment_pk)


class PendingPaymentsView(LoginRequiredMixin, ListView):
    """
    Lists all customers with outstanding balances, sorted by amount due.
    Provides comprehensive KPI overview metrics, quick status tabs, search & filters,
    and Zoho Books-grade high-density data representation.
    """
    model = Customer
    template_name = 'payments/pending_payments.html'
    context_object_name = 'pending_list'
    paginate_by = 25

    def get_paginate_by(self, queryset):
        page_size = self.request.GET.get('page_size')
        if page_size and page_size.isdigit():
            size = int(page_size)
            if 5 <= size <= 100:
                return size
        return self.paginate_by

    def get_annotated_pending_queryset(self):
        b_sq = Bill.objects.filter(
            customer=OuterRef('pk'),
            bill_type='TAX_INVOICE'
        ).exclude(status='CANCELLED').values('customer').annotate(tot=Sum('grand_total')).values('tot')

        p_sq = Payment.objects.filter(
            customer=OuterRef('pk')
        ).values('customer').annotate(tot=Sum('amount')).values('tot')

        return (
            Customer.objects.filter(is_active=True)
            .annotate(
                db_billed=Coalesce(Subquery(b_sq), Value(Decimal('0.00')), output_field=DecimalField()),
                db_paid=Coalesce(Subquery(p_sq), Value(Decimal('0.00')), output_field=DecimalField()),
            )
            .annotate(db_due=F('db_billed') - F('db_paid'))
            .filter(db_due__gt=Decimal('0.00'))
        )

    def get_queryset(self):
        qs = self.get_annotated_pending_queryset()
        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip().lower()
        village = self.request.GET.get('village', '').strip()

        if q:
            qs = qs.filter(
                Q(full_name__icontains=q) |
                Q(mobile_primary__icontains=q) |
                Q(village__icontains=q) |
                Q(taluka__icontains=q) |
                Q(district__icontains=q)
            )

        if village:
            qs = qs.filter(village__iexact=village)

        if status == 'overdue':
            qs = qs.filter(Q(db_due__gte=Decimal('50000.00')) | Q(db_paid=Decimal('0.00')))
        elif status == 'partial':
            qs = qs.filter(db_paid__gt=Decimal('0.00'))
        elif status == 'unpaid':
            qs = qs.filter(db_paid=Decimal('0.00'))
        elif status == 'high':
            qs = qs.filter(db_due__gte=Decimal('50000.00'))

        qs = qs.order_by('-db_due')

        pending = []
        for c in qs:
            is_partial = c.db_paid > Decimal('0.00')
            is_unpaid = c.db_paid == Decimal('0.00')
            is_overdue = c.db_due >= Decimal('50000.00') or is_unpaid
            clean_phone = normalize_indian_mobile(c.mobile_primary)
            wa_url = "#"
            if clean_phone:
                try:
                    _, wa_msg = build_overdue_reminder_message(c, c.db_due)
                    wa_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(wa_msg)}"
                except Exception:
                    wa_url = f"https://wa.me/{clean_phone}"
            status_label = 'OVERDUE' if is_overdue else ('PARTIAL' if is_partial else 'UNPAID')
            status_color = 'red' if is_overdue else ('blue' if is_partial else 'amber')
            pending.append({
                'customer': c,
                'total_billed': c.db_billed,
                'total_paid': c.db_paid,
                'outstanding': c.db_due,
                'unallocated': Decimal('0.00'),
                'status_label': status_label,
                'status_color': status_color,
                'is_partial': is_partial,
                'is_unpaid': is_unpaid,
                'is_overdue': is_overdue,
                'wa_url': wa_url,
            })

        return pending

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_size = self.request.GET.get('page_size')
        if page_size and page_size.isdigit() and 5 <= int(page_size) <= 100:
            context['current_page_size'] = int(page_size)
        else:
            context['current_page_size'] = self.paginate_by

        base_qs = self.get_annotated_pending_queryset()
        kpis = base_qs.aggregate(
            total_outstanding=Sum('db_due'),
            total_billed=Sum('db_billed'),
            total_paid=Sum('db_paid'),
            total_count=Count('id'),
            overdue_count=Count('id', filter=Q(db_due__gte=Decimal('50000.00')) | Q(db_paid=Decimal('0.00'))),
            overdue_amount=Sum('db_due', filter=Q(db_due__gte=Decimal('50000.00')) | Q(db_paid=Decimal('0.00'))),
            partial_count=Count('id', filter=Q(db_paid__gt=Decimal('0.00'))),
            partial_amount=Sum('db_paid', filter=Q(db_paid__gt=Decimal('0.00'))),
            unpaid_count=Count('id', filter=Q(db_paid=Decimal('0.00'))),
            unpaid_amount=Sum('db_due', filter=Q(db_paid=Decimal('0.00'))),
            high_count=Count('id', filter=Q(db_due__gte=Decimal('50000.00'))),
            high_amount=Sum('db_due', filter=Q(db_due__gte=Decimal('50000.00'))),
        )

        context['total_outstanding_sum'] = kpis['total_outstanding'] or Decimal('0.00')
        context['total_billed_sum'] = kpis['total_billed'] or Decimal('0.00')
        context['total_paid_sum'] = kpis['total_paid'] or Decimal('0.00')
        context['all_pending_count'] = kpis['total_count'] or 0
        context['overdue_count'] = kpis['overdue_count'] or 0
        context['overdue_amount'] = kpis['overdue_amount'] or Decimal('0.00')
        context['partially_paid_count'] = kpis['partial_count'] or 0
        context['partially_paid_amount'] = kpis['partial_amount'] or Decimal('0.00')
        context['unpaid_count'] = kpis['unpaid_count'] or 0
        context['unpaid_amount'] = kpis['unpaid_amount'] or Decimal('0.00')
        context['high_pending_count'] = kpis['high_count'] or 0
        context['high_pending_amount'] = kpis['high_amount'] or Decimal('0.00')

        # Filter parameters
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['current_status'] = self.request.GET.get('status', '').strip().lower()
        context['current_village'] = self.request.GET.get('village', '').strip()
        context['villages'] = Customer.objects.filter(is_active=True).exclude(
            village__isnull=True
        ).exclude(village='').values_list('village', flat=True).distinct().order_by('village')

        return context


class CustomerLedgerView(LoginRequiredMixin, View):
    """
    Full financial ledger for a specific customer.
    Supports date range filtering, computes opening balance prior to date_from,
    and calculates running balance and closing balance.
    """
    template_name = 'payments/customer_ledger.html'

    def get(self, request, pk, *args, **kwargs):
        import urllib.parse
        import re
        customer = get_object_or_404(Customer, pk=pk)
        company = CompanyProfile.get_instance()

        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()

        all_bills = Bill.objects.filter(
            customer=customer,
            bill_type='TAX_INVOICE'
        ).exclude(status='CANCELLED')
        all_payments = Payment.objects.filter(customer=customer)

        opening_balance = Decimal('0.00')

        if date_from:
            prior_debits = sum((b.grand_total for b in all_bills.filter(bill_date__lt=date_from)), Decimal('0.00'))
            prior_credits = sum((p.amount for p in all_payments.filter(payment_date__lt=date_from)), Decimal('0.00'))
            opening_balance = prior_debits - prior_credits

        period_bills = all_bills
        period_payments = all_payments

        if date_from:
            period_bills = period_bills.filter(bill_date__gte=date_from)
            period_payments = period_payments.filter(payment_date__gte=date_from)
        if date_to:
            period_bills = period_bills.filter(bill_date__lte=date_to)
            period_payments = period_payments.filter(payment_date__lte=date_to)

        # Combine into unified ledger entries
        ledger = []
        for b in period_bills:
            ledger.append({
                'date': b.bill_date,
                'type': 'DEBIT',
                'description': f"{b.get_bill_type_display()} #{b.bill_number}",
                'ref_url': reverse('billing:bill_detail', kwargs={'pk': b.pk}),
                'debit': b.grand_total,
                'credit': Decimal('0.00'),
                'raw_date': b.bill_date,
                'created_at': b.created_at,
            })
        for p in period_payments:
            ledger.append({
                'date': p.payment_date,
                'type': 'CREDIT',
                'description': f"Payment Receipt #{p.receipt_number} ({p.get_payment_mode_display()} - {p.get_purpose_display()})",
                'ref_url': reverse('payments:payment_detail', kwargs={'pk': p.pk}),
                'debit': Decimal('0.00'),
                'credit': p.amount,
                'raw_date': p.payment_date,
                'created_at': p.created_at,
            })

        # Sort chronologically
        ledger.sort(key=lambda x: (x['raw_date'], x['created_at']))

        # Calculate running balance starting from opening_balance
        running_bal = opening_balance
        period_debits = Decimal('0.00')
        period_credits = Decimal('0.00')

        for entry in ledger:
            period_debits += entry['debit']
            period_credits += entry['credit']
            running_bal += entry['debit'] - entry['credit']
            entry['balance'] = running_bal

        closing_balance = running_bal

        # WhatsApp Reminder URL
        clean_phone = re.sub(r'\D', '', customer.mobile_primary or '')
        if clean_phone and len(clean_phone) == 10:
            clean_phone = f"91{clean_phone}"
        wa_msg = (
            f"Dear {customer.full_name},\n"
            f"Greetings from {company.company_name}.\n"
            f"This is a gentle reminder that your current outstanding showroom balance is Rs. {customer.outstanding_balance:,.2f}.\n"
            f"For inquiries or payment settlement, kindly contact us at {company.mobile_numbers}.\n"
            f"Thank you!"
        )
        whatsapp_url = f"https://api.whatsapp.com/send?phone={clean_phone}&text={urllib.parse.quote(wa_msg)}" if clean_phone else ""

        return render(request, self.template_name, {
            'customer': customer,
            'company': company,
            'ledger': ledger,
            'date_from': date_from,
            'date_to': date_to,
            'opening_balance': opening_balance,
            'period_debits': period_debits,
            'period_credits': period_credits,
            'closing_balance': closing_balance,
            'total_billed': customer.total_billed,
            'total_paid': customer.total_paid,
            'outstanding': customer.outstanding_balance,
            'unallocated': customer.unallocated_balance,
            'whatsapp_url': whatsapp_url,
        })


class PaymentPDFView(LoginRequiredMixin, View):
    """
    Renders high-fidelity downloadable / printable A4 Money Receipt Voucher using xhtml2pdf.
    """
    def get(self, request, pk, *args, **kwargs):
        payment = get_object_or_404(Payment.objects.select_related('customer'), pk=pk)
        company = CompanyProfile.get_instance()
        allocations = payment.allocations.select_related('bill').all()
        amount_words = number_to_words_indian(payment.amount)

        context = {
            'payment': payment,
            'customer': payment.customer,
            'company': company,
            'allocations': allocations,
            'amount_words': amount_words,
        }

        html = render_to_string('payments/payment_pdf.html', context)
        result = io.BytesIO()
        pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result, link_callback=link_callback)
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            disposition = 'attachment' if request.GET.get('download') == '1' else 'inline'
            filename = f"Receipt_{payment.receipt_number}.pdf".replace(' ', '_').replace('/', '_')
            response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
            return response

        messages.error(request, "Could not generate Payment Receipt PDF.")
        return redirect('payments:payment_detail', pk=payment.pk)


class CustomerSendReminderView(LoginRequiredMixin, View):
    """
    Directly dispatch an overdue balance reminder via WhatsApp/SMS gateway for a single customer.
    """
    def post(self, request, customer_id, *args, **kwargs):
        customer = get_object_or_404(Customer, pk=customer_id)
        due = customer.outstanding_balance
        if due <= Decimal('0.00'):
            messages.info(request, f"Customer '{customer.full_name}' has no outstanding dues.")
            return redirect('payments:pending_payments')

        try:
            recipient, message = build_overdue_reminder_message(customer, due)
            log_entry = send_notification(
                recipient=recipient,
                message=message,
                notification_type='OVERDUE_REMINDER',
                user=request.user,
                entity_id=f"CUST-{customer.pk:04d}"
            )
            if log_entry.status == 'SENT':
                messages.success(request, f"Reminder dispatched to {recipient} ({customer.full_name}) successfully.")
            elif log_entry.status == 'SIMULATED':
                messages.info(request, f"Reminder simulated for {recipient} ({customer.full_name}). (Simulator active)")
            else:
                messages.warning(request, f"Could not send reminder: {log_entry.error_message}")
        except Exception as e:
            logger.error(f"Failed to send overdue reminder: {e}", exc_info=True)
            messages.error(request, f"Failed to send reminder: {e}")

        # Redirect back to referring page or pending list
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure()
        ):
            return redirect(next_url)
        return redirect('payments:pending_payments')


class BatchSendRemindersView(LoginRequiredMixin, View):
    """
    Batch send overdue payment reminders to all pending accounts with outstanding dues.
    """
    def post(self, request, *args, **kwargs):
        active_invoices = Bill.objects.filter(
            customer=OuterRef('pk'),
            bill_type='TAX_INVOICE'
        ).exclude(status='CANCELLED')

        billed_sub = active_invoices.values('customer').annotate(
            tot=Sum('grand_total')
        ).values('tot')

        paid_sub = Payment.objects.filter(
            customer=OuterRef('pk')
        ).values('customer').annotate(
            tot=Sum('amount')
        ).values('tot')

        qs = Customer.objects.filter(is_active=True).annotate(
            db_billed=Coalesce(Subquery(billed_sub), Value(Decimal('0.00')), output_field=DecimalField()),
            db_paid=Coalesce(Subquery(paid_sub), Value(Decimal('0.00')), output_field=DecimalField()),
        ).annotate(
            db_due=F('db_billed') - F('db_paid')
        ).filter(db_due__gt=Decimal('0.00'))

        success_count = 0
        skipped_count = 0
        for customer in qs:
            try:
                recipient, message = build_overdue_reminder_message(customer, customer.db_due)
                log_entry = send_notification(
                    recipient=recipient,
                    message=message,
                    notification_type='OVERDUE_REMINDER',
                    user=request.user,
                    entity_id=f"CUST-{customer.pk:04d}"
                )
                if log_entry and log_entry.status in ('SENT', 'SIMULATED'):
                    success_count += 1
                else:
                    skipped_count += 1
            except Exception:
                skipped_count += 1

        messages.success(request, f"Batch reminder execution completed: {success_count} notifications processed ({skipped_count} skipped or invalid phone).")
        return redirect('payments:pending_payments')


