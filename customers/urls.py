from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('', views.CustomerListView.as_view(), name='customer_list'),
    path('add/', views.CustomerCreateView.as_view(), name='customer_add'),
    path('quick-create/', views.customer_quick_create, name='customer_quick_create'),
    path('<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_edit'),
    path('<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
    path('search/', views.customer_search, name='customer_search'),
    path('api/<int:pk>/', views.customer_api_detail, name='customer_api_detail'),
    path('api/<int:pk>/update/', views.customer_api_update, name='customer_api_update'),
]

