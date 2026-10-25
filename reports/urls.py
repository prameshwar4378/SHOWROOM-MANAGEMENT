from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('export/sales/', views.ExportSalesExcelView.as_view(), name='export_sales_excel'),
    path('export/dues/', views.ExportPendingDuesExcelView.as_view(), name='export_dues_excel'),
]
