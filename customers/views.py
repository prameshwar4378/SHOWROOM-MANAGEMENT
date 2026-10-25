import json
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, F, Value, DecimalField
from django.db.models.functions import Coalesce
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)

from .forms import CustomerForm, CustomerSearchForm
from .models import Customer


class CustomerListView(LoginRequiredMixin, ListView):
    """
    Displays a paginated list of customers with search and filter capabilities.
    Supports standard rendering and HTMX partial responses.
    """
    model = Customer
    context_object_name = 'customers'
    paginate_by = 20
    template_name = 'customers/customer_list.html'

    def get_queryset(self):
        queryset = Customer.objects.all()
        q = self.request.GET.get('q', '').strip()
        status = self.request.GET.get('status', '').strip()

        if q:
            queryset = queryset.filter(
                Q(full_name__icontains=q)
                | Q(father_name__icontains=q)
                | Q(mobile_primary__icontains=q)
                | Q(mobile_secondary__icontains=q)
                | Q(village__icontains=q)
                | Q(taluka__icontains=q)
                | Q(district__icontains=q)
                | Q(aadhar_number__icontains=q)
                | Q(pan_number__icontains=q)
            )

        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_paginate_by(self, queryset):
        page_size = self.request.GET.get('page_size')
        if page_size and page_size.isdigit():
            size = int(page_size)
            if 5 <= size <= 100:
                return size
        return self.paginate_by

    def get_template_names(self):
        # Support HTMX partial requests
        if getattr(self.request, 'htmx', False) or self.request.headers.get('HX-Request') == 'true':
            return ['customers/customer_list_partial.html']
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_page_size'] = self.get_paginate_by(None)
        context['search_query'] = self.request.GET.get('q', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['search_form'] = CustomerSearchForm(self.request.GET)
        context['total_customers_count'] = Customer.objects.count()
        context['active_customers_count'] = Customer.objects.filter(is_active=True).count()
        context['inactive_customers_count'] = Customer.objects.filter(is_active=False).count()

        pending_customers_qs = (
            Customer.objects.filter(is_active=True)
            .annotate(
                db_billed=Coalesce(
                    Sum('bills__grand_total', filter=Q(bills__bill_type='TAX_INVOICE') & ~Q(bills__status='CANCELLED')),
                    Value(Decimal('0.00')),
                    output_field=DecimalField()
                ),
                db_paid=Coalesce(
                    Sum('payments__amount'),
                    Value(Decimal('0.00')),
                    output_field=DecimalField()
                )
            )
            .annotate(db_due=F('db_billed') - F('db_paid'))
            .filter(db_due__gt=Decimal('0.00'))
        )
        pending_stats = pending_customers_qs.aggregate(
            cnt=Count('id'),
            total_due=Coalesce(Sum('db_due'), Value(Decimal('0.00')), output_field=DecimalField())
        )
        context['with_pending_count'] = pending_stats['cnt']
        context['with_pending_amount'] = pending_stats['total_due']
        return context


class CustomerCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """
    Creates a new customer profile.
    """
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_message = "Customer '%(full_name)s' was registered successfully."

    def get_success_url(self):
        return reverse('customers:customer_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = False
        context['page_title'] = 'Add New Customer'
        return context


class CustomerUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Updates an existing customer profile.
    """
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_message = "Customer '%(full_name)s' details were updated successfully."

    def get_success_url(self):
        return reverse('customers:customer_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        context['page_title'] = f"Edit Customer - {self.object.full_name}"
        return context


class CustomerDetailView(LoginRequiredMixin, DetailView):
    """
    Customer dashboard displaying customer particulars, financial summary
    (total billed, total paid, outstanding balance, unallocated balance),
    recent bills, recent payments, and quick action shortcuts.
    """
    model = Customer
    context_object_name = 'customer'
    template_name = 'customers/customer_detail.html'

    def get_context_data(self, **kwargs):
        import urllib.parse
        import re
        from settings_app.models import CompanyProfile
        context = super().get_context_data(**kwargs)
        customer = self.object

        context['total_billed'] = customer.total_billed
        context['total_paid'] = customer.total_paid
        context['outstanding_balance'] = customer.outstanding_balance
        context['unallocated_balance'] = customer.unallocated_balance
        context['recent_bills'] = customer.recent_bills
        context['recent_payments'] = customer.recent_payments

        clean_phone = re.sub(r'\D', '', customer.mobile_primary or '')
        if clean_phone.startswith('0') and len(clean_phone) == 11:
            clean_phone = clean_phone[1:]
        if clean_phone and len(clean_phone) == 10:
            clean_phone = f"91{clean_phone}"
        company = CompanyProfile.get_instance()
        wa_msg = (
            f"Dear {customer.full_name},\n"
            f"Greetings from {company.company_name}.\n"
            f"Your current outstanding showroom balance is Rs. {customer.outstanding_balance:,.2f}.\n"
            f"For details or payment, contact us at {company.mobile_numbers}."
        )
        context['whatsapp_url'] = f"https://api.whatsapp.com/send?phone={clean_phone}&text={urllib.parse.quote(wa_msg)}" if clean_phone else ""
        return context


class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    """
    Soft deletes a customer by setting `is_active = False`.
    Prevents accidental data loss while hiding the customer from active views.
    """
    model = Customer
    context_object_name = 'customer'
    template_name = 'customers/customer_confirm_delete.html'
    success_url = reverse_lazy('customers:customer_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save(update_fields=['is_active'])
        messages.success(
            request,
            f"Customer '{self.object.full_name}' was deactivated successfully."
        )
        return HttpResponseRedirect(self.get_success_url())

    def form_valid(self, form):
        return self.delete(self.request)


@login_required
def customer_search(request):
    """
    HTMX live search endpoint returning customer_list_partial.html.
    Filters customers based on search term 'q' and 'status'.
    """
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    page_number = request.GET.get('page', 1)

    queryset = Customer.objects.all()

    if q:
        queryset = queryset.filter(
            Q(full_name__icontains=q)
            | Q(father_name__icontains=q)
            | Q(mobile_primary__icontains=q)
            | Q(mobile_secondary__icontains=q)
            | Q(village__icontains=q)
            | Q(taluka__icontains=q)
            | Q(district__icontains=q)
            | Q(aadhar_number__icontains=q)
            | Q(pan_number__icontains=q)
        )

    if status == 'active':
        queryset = queryset.filter(is_active=True)
    elif status == 'inactive':
        queryset = queryset.filter(is_active=False)

    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        'customers/customer_list_partial.html',
        {
            'customers': page_obj.object_list,
            'page_obj': page_obj,
            'search_query': q,
            'current_status': status,
        }
    )


@login_required
def customer_quick_create(request):
    """
    AJAX endpoint to quickly register a new customer from a modal dialog
    and return JSON with the new customer's details for instant auto-selection.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    if request.content_type == 'application/json':
        try:
            post_data = json.loads(request.body.decode('utf-8'))
        except Exception:
            post_data = {}
    else:
        post_data = request.POST.copy() if hasattr(request.POST, 'copy') else dict(request.POST)

    post_data['is_active'] = True

    form = CustomerForm(post_data)
    if form.is_valid():
        customer = form.save(commit=False)
        customer.is_active = True
        customer.save()
        return JsonResponse({
            'success': True,
            'customer': {
                'id': customer.id,
                'full_name': customer.full_name,
                'father_name': customer.father_name,
                'mobile': customer.mobile_primary,
                'mobile_primary': customer.mobile_primary,
                'village': customer.village,
                'taluka': customer.taluka,
                'district': customer.district,
                'state': customer.state or 'Maharashtra',
                'display_text': str(customer),
            },
            'message': f"Customer '{customer.full_name}' registered successfully!"
        })
    else:
        errors = {}
        for field, errs in form.errors.items():
            errors[field] = [str(e) for e in errs]
        return JsonResponse({
            'success': False,
            'errors': errors
        }, status=400)


@login_required
def customer_api_detail(request, pk):
    """
    JSON API endpoint returning complete profile information for a customer.
    Used by modal dialogs in the billing interface for instant viewing and editing
    without leaving the page.
    """
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    try:
        customer = Customer.objects.get(pk=pk)
    except Customer.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Customer not found'}, status=404)

    return JsonResponse({
        'success': True,
        'customer': {
            'id': customer.id,
            'full_name': customer.full_name or '',
            'father_name': customer.father_name or '',
            'mobile_primary': customer.mobile_primary or '',
            'mobile_secondary': customer.mobile_secondary or '',
            'email': customer.email or '',
            'village': customer.village or '',
            'taluka': customer.taluka or '',
            'district': customer.district or '',
            'state': customer.state or 'Maharashtra',
            'pin_code': customer.pin_code or '',
            'aadhar_number': customer.aadhar_number or '',
            'pan_number': customer.pan_number or '',
            'bank_name': customer.bank_name or '',
            'bank_branch': customer.bank_branch or '',
            'reference_by': customer.reference_by or '',
            'notes': customer.notes or '',
            'is_active': customer.is_active,
            'total_billed': float(customer.total_billed),
            'total_paid': float(customer.total_paid),
            'outstanding_balance': float(customer.outstanding_balance),
            'display_text': str(customer),
            'created_at': customer.created_at.strftime('%d-%m-%Y') if customer.created_at else '',
        }
    })


@login_required
def customer_api_update(request, pk):
    """
    AJAX endpoint to update customer profile details in-place from modal dialog
    without page redirection, preserving bill form state.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    try:
        customer = Customer.objects.get(pk=pk)
    except Customer.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Customer not found'}, status=404)

    import json
    data = {}
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = {}
    else:
        data = request.POST.dict() if hasattr(request.POST, 'dict') else dict(request.POST)

    # Ensure is_active status is preserved if not explicitly submitted
    if 'is_active' not in data:
        data['is_active'] = customer.is_active

    form = CustomerForm(data, instance=customer)
    if form.is_valid():
        customer = form.save()
        return JsonResponse({
            'success': True,
            'customer': {
                'id': customer.id,
                'full_name': customer.full_name or '',
                'father_name': customer.father_name or '',
                'mobile_primary': customer.mobile_primary or '',
                'mobile_secondary': customer.mobile_secondary or '',
                'email': customer.email or '',
                'village': customer.village or '',
                'taluka': customer.taluka or '',
                'district': customer.district or '',
                'state': customer.state or 'Maharashtra',
                'pin_code': customer.pin_code or '',
                'aadhar_number': customer.aadhar_number or '',
                'pan_number': customer.pan_number or '',
                'bank_name': customer.bank_name or '',
                'bank_branch': customer.bank_branch or '',
                'reference_by': customer.reference_by or '',
                'notes': customer.notes or '',
                'is_active': customer.is_active,
                'total_billed': float(customer.total_billed),
                'total_paid': float(customer.total_paid),
                'outstanding_balance': float(customer.outstanding_balance),
                'display_text': str(customer),
            },
            'message': f"Customer '{customer.full_name}' updated successfully!"
        })
    else:
        errors = {}
        for field, errs in form.errors.items():
            errors[field] = [str(e) for e in errs]
        return JsonResponse({
            'success': False,
            'errors': errors
        }, status=400)


