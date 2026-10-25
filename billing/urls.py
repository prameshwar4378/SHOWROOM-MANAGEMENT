"""
URL patterns for the billing application.
"""
from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.BillListView.as_view(), name='bill_list'),
    path('create/', views.BillCreateView.as_view(), name='bill_create'),
    path('<int:pk>/', views.BillDetailView.as_view(), name='bill_detail'),
    path('<int:pk>/edit/', views.BillUpdateView.as_view(), name='bill_edit'),
    path('<int:pk>/delete/', views.BillDeleteView.as_view(), name='bill_delete'),
    path('<int:pk>/duplicate/', views.bill_duplicate, name='bill_duplicate'),
    path('<int:pk>/convert/', views.bill_convert, name='bill_convert'),
    path('<int:pk>/pdf/', views.BillPDFView.as_view(), name='bill_pdf'),
    path('<int:pk>/send-notification/', views.BillSendNotificationView.as_view(), name='bill_send_notification'),
    # Temporary / Instant Print Bill (Zero Database Footprint)
    path('temporary-bill/', views.TemporaryBillView.as_view(), name='temporary_bill'),
    # Inventory & Stock Management Routes
    path('inventory/', views.InventoryDashboardView.as_view(), name='inventory_dashboard'),
    path('inventory/export/', views.ExportInventoryExcelView.as_view(), name='inventory_export'),
    path('inventory/import/', views.ImportInventoryExcelView.as_view(), name='inventory_import'),
    path('inventory/import/sample/', views.DownloadSampleInventoryView.as_view(), name='inventory_sample_download'),
    path('inventory/sample-template/', views.DownloadSampleInventoryView.as_view(), name='inventory_sample_template'),
    # Purchase / Inward Stock Bills
    path('inventory/purchases/', views.PurchaseBillListView.as_view(), name='purchase_list'),
    path('inventory/purchases/add/', views.PurchaseBillCreateView.as_view(), name='purchase_add'),
    path('inventory/purchases/<int:pk>/', views.PurchaseBillDetailView.as_view(), name='purchase_detail'),
    # Serialized Tractor Inventory Units
    path('inventory/units/add/', views.TractorStockUnitCreateView.as_view(), name='stock_unit_add'),
    path('inventory/units/<int:pk>/edit/', views.TractorStockUnitUpdateView.as_view(), name='stock_unit_edit'),
    path('inventory/units/<int:pk>/delete/', views.TractorStockUnitDeleteView.as_view(), name='stock_unit_delete'),
    # Products & Spares Catalog
    path('inventory/products/', views.ProductListView.as_view(), name='product_list'),
    path('inventory/products/add/', views.ProductCreateView.as_view(), name='product_add'),
    path('inventory/products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_edit'),
]
