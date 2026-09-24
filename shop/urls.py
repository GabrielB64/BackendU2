from .views import admin_dashboard
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    # HTML
    path("", views.index_page, name="index"),
    path("login/client/", views.client_login_page, name="client-login"),
    path("login/company/", views.company_login_page, name="company-login"),
    path("register/client/", views.client_register_page, name="client-register"),
    path("register/company/", views.company_register_page, name="company-register"),
    path("cart/", views.cart_page, name="cart"),
    path("company/dashboard/", views.company_dashboard_page, name="company-dashboard"),
    path("company/products/", views.company_products_page, name="company-products"),
    path("company/products/new/", views.company_product_form_page, name="company-product-new"),

    # Auth API
    path("api/auth/token/", views.ClientTokenView.as_view(), name="client-token"),
    path("api/auth/company/token/", views.CompanyTokenView.as_view(), name="company-token"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/auth/register/client/", views.client_register, name="client-register-api"),
    path("api/auth/register/company/", views.company_register, name="company-register-api"),

    # Public product API
    path("api/products/", views.public_products, name="public-products"),

    # Cart API
    path("api/cart/", views.cart_detail, name="cart-detail"),
    path("api/cart/items/", views.cart_add_item, name="cart-add"),
    path("api/cart/items/<int:item_id>/", views.cart_update_item, name="cart-update"),
    path("api/cart/items/<int:item_id>/delete/", views.cart_remove_item, name="cart-remove"),

    # Checkout
    path("api/checkout/", views.checkout, name="checkout"),

    # Company API
    path("api/company/products/", views.company_products, name="company-products-api"),
    path("api/company/products/create/", views.company_product_create, name="company-product-create"),
    path("api/company/products/<int:product_id>/", views.company_product_detail, name="company-product-detail"),
    path("api/company/dashboard/", views.company_dashboard, name="company-dashboard-api"),
    path("api/company/orders/", views.company_orders, name="company-orders"),
]
