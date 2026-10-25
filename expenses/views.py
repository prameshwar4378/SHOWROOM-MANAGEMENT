import csv
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)

from .forms import ExpenseForm, ExpenseCategoryForm
from .models import Expense, ExpenseCategory
from billing.utils import number_to_words_indian
from settings_app.models import CompanyProfile


class ExpenseListView(LoginRequiredMixin, ListView):
    """
    Advanced list view for showroom operating expenses with KPI metrics,
    multilingual search, category/date filters, and pagination.
    """
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 25

    def get_paginate_by(self, queryset):
        page_size = self.request.GET.get('page_size')
        if page_size and page_size.isdigit():
            size = int(page_size)
            if 10 <= size <= 200:
                return size
        return self.paginate_by

    def get_queryset(self):
        qs = Expense.objects.select_related('category', 'recorded_by').all().order_by('-expense_date', '-id')

        # 1. Search Query
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(expense_number__icontains=q) |
                Q(title__icontains=q) |
                Q(payee_name__icontains=q) |
                Q(payment_reference__icontains=q) |
                Q(notes__icontains=q) |
                Q(category__name__icontains=q)
            )

        # 2. Category Filter
        cat_id = self.request.GET.get('category', '').strip()
        if cat_id and cat_id.isdigit():
            qs = qs.filter(category_id=int(cat_id))

        # 3. Payment Mode Filter
        mode = self.request.GET.get('mode', '').strip()
        if mode:
            qs = qs.filter(payment_mode=mode)

        # 4. Date Range Filter
        date_range = self.request.GET.get('date_range', '').strip()
        today = timezone.now().date()

        if date_range == 'today':
            qs = qs.filter(expense_date=today)
        elif date_range == 'yesterday':
            yesterday = today - timedelta(days=1)
            qs = qs.filter(expense_date=yesterday)
        elif date_range == 'this_week':
            start_of_week = today - timedelta(days=today.weekday())
            qs = qs.filter(expense_date__gte=start_of_week, expense_date__lte=today)
        elif date_range == 'this_month':
            start_of_month = today.replace(day=1)
            qs = qs.filter(expense_date__gte=start_of_month, expense_date__lte=today)
        elif date_range == 'last_month':
            first_this_month = today.replace(day=1)
            last_day_last_month = first_this_month - timedelta(days=1)
            first_last_month = last_day_last_month.replace(day=1)
            qs = qs.filter(expense_date__gte=first_last_month, expense_date__lte=last_day_last_month)
        elif date_range == 'this_fy':
            if today.month >= 4:
                fy_start = today.replace(month=4, day=1)
            else:
                fy_start = today.replace(year=today.year - 1, month=4, day=1)
            qs = qs.filter(expense_date__gte=fy_start, expense_date__lte=today)
        elif date_range == 'custom':
            start_date = self.request.GET.get('start_date', '').strip()
            end_date = self.request.GET.get('end_date', '').strip()
            if start_date:
                qs = qs.filter(expense_date__gte=start_date)
            if end_date:
                qs = qs.filter(expense_date__lte=end_date)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        filtered_qs = self.get_queryset()

        # All-time / Monthly / Daily Totals
        first_of_month = today.replace(day=1)
        month_qs = Expense.objects.filter(expense_date__gte=first_of_month, expense_date__lte=today)
        today_qs = Expense.objects.filter(expense_date=today)

        total_filtered = filtered_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        month_total = month_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        today_total = today_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        cash_total = filtered_qs.filter(payment_mode='CASH').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        bank_total = filtered_qs.filter(
            payment_mode__in=['UPI', 'BANK_TRANSFER', 'CHEQUE', 'CARD']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Top Categories breakdown for current filter
        top_categories = (
            filtered_qs.values('category__name', 'category__icon', 'category__color')
            .annotate(cat_total=Sum('amount'))
            .order_by('-cat_total')[:5]
        )

        context.update({
            'kpi_total': total_filtered,
            'kpi_month': month_total,
            'kpi_today': today_total,
            'kpi_cash': cash_total,
            'kpi_bank': bank_total,
            'top_categories': top_categories,
            'categories': ExpenseCategory.objects.filter(is_active=True).order_by('name'),
            'current_q': self.request.GET.get('q', ''),
            'current_category': self.request.GET.get('category', ''),
            'current_mode': self.request.GET.get('mode', ''),
            'current_range': self.request.GET.get('date_range', ''),
            'start_date': self.request.GET.get('start_date', ''),
            'end_date': self.request.GET.get('end_date', ''),
            'payment_modes': Expense.PAYMENT_MODE_CHOICES,
        })
        return context


class ExpenseCreateView(LoginRequiredMixin, CreateView):
    """
    Record a new operating showroom expense with auto-assigned recorded_by.
    """
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expenses:expense_list')

    def form_valid(self, form):
        form.instance.recorded_by = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Expense voucher recorded successfully: {self.object.expense_number} - ₹{self.object.amount}"
        )
        return response


class ExpenseUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update existing showroom expense details.
    """
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expenses:expense_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"Expense voucher {self.object.expense_number} updated successfully."
        )
        return response


class ExpenseDetailView(LoginRequiredMixin, DetailView):
    """
    Full view of an individual expense voucher and audit details.
    """
    model = Expense
    template_name = 'expenses/expense_detail.html'
    context_object_name = 'expense'


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete an expense voucher.
    """
    model = Expense
    template_name = 'expenses/expense_confirm_delete.html'
    success_url = reverse_lazy('expenses:expense_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        exp_no = self.object.expense_number
        amt = self.object.amount
        response = super().delete(request, *args, **kwargs)
        messages.warning(request, f"Expense voucher {exp_no} (₹{amt}) removed successfully.")
        return response


class ExpenseVoucherView(LoginRequiredMixin, View):
    """
    Printable Payment / Debit Voucher (खर्च पावती) in official A4 / half-page layout
    with showroom branding and authorized signature blocks.
    """
    def get(self, request, pk):
        expense = get_object_or_404(Expense.objects.select_related('category', 'recorded_by'), pk=pk)
        company = CompanyProfile.objects.first()
        amount_words = number_to_words_indian(expense.amount)

        context = {
            'expense': expense,
            'company': company,
            'amount_words': amount_words,
        }
        return render(request, 'expenses/expense_voucher.html', context)


class ExpenseCategoryListView(LoginRequiredMixin, ListView):
    """
    Manage expense categories with total spending metrics per category.
    """
    model = ExpenseCategory
    template_name = 'expenses/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return ExpenseCategory.objects.annotate(
            total_spent=Sum('expenses__amount')
        ).order_by('name')


class ExpenseCategoryCreateView(LoginRequiredMixin, CreateView):
    """
    Add a new expense category.
    """
    model = ExpenseCategory
    form_class = ExpenseCategoryForm
    template_name = 'expenses/category_form.html'
    success_url = reverse_lazy('expenses:category_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Expense category '{self.object.name}' created successfully.")
        return response


class ExpenseCategoryUpdateView(LoginRequiredMixin, UpdateView):
    """
    Edit an existing expense category.
    """
    model = ExpenseCategory
    form_class = ExpenseCategoryForm
    template_name = 'expenses/category_form.html'
    success_url = reverse_lazy('expenses:category_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Expense category '{self.object.name}' updated successfully.")
        return response


class ExpenseCategoryDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete an expense category if it has no associated expenses.
    """
    model = ExpenseCategory
    template_name = 'expenses/category_confirm_delete.html'
    success_url = reverse_lazy('expenses:category_list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.expenses.exists():
            messages.error(
                request,
                f"Cannot delete category '{self.object.name}' because it has existing expense vouchers."
            )
            return redirect('expenses:category_list')
        messages.warning(request, f"Expense category '{self.object.name}' deleted successfully.")
        return super().post(request, *args, **kwargs)


class ExpenseExportExcelView(LoginRequiredMixin, View):
    """
    Export showroom expenses register to CSV format with UTF-8 BOM for Microsoft Excel.
    """
    def get(self, request):
        view = ExpenseListView()
        view.request = request
        qs = view.get_queryset()

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        timestamp = timezone.now().strftime('%Y%m%d_%H%M')
        response['Content-Disposition'] = f'attachment; filename="showroom_expenses_{timestamp}.csv"'

        # Write UTF-8 BOM so Excel opens Marathi and Hindi scripts correctly
        response.write('\ufeff')

        writer = csv.writer(response)
        writer.writerow([
            'Voucher No',
            'Date',
            'Category',
            'Title / Particulars',
            'Paid To / Payee',
            'Payment Mode',
            'Reference / UTR / Cheque',
            'Amount (INR)',
            'Recorded By',
            'Notes',
        ])

        for exp in qs:
            writer.writerow([
                exp.expense_number,
                exp.expense_date.strftime('%d-%m-%Y'),
                exp.category.name if exp.category else '',
                exp.title,
                exp.payee_name or '-',
                exp.get_payment_mode_display(),
                exp.payment_reference or '-',
                f"{exp.amount:.2f}",
                exp.recorded_by.get_full_name() or exp.recorded_by.username if exp.recorded_by else '-',
                exp.notes.replace('\n', ' ') if exp.notes else '',
            ])

        return response
