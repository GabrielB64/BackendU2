from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Company, Product, Cart, CartItem, Order, OrderItem

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("rut", "email", "user_type", "is_active", "is_staff")
    search_fields = ("rut", "email")
    ordering = ("rut",)
    fieldsets = UserAdmin.fieldsets + (
        ("Datos de tienda", {
            "fields": ("rut", "phone_country_code", "phone_number", "user_type")
        }),
    )

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "rut", "owner", "active")
    search_fields = ("name", "rut")
    list_filter = ("active",)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "price", "stock", "active", "created_at")
    search_fields = ("name", "company__name")
    list_filter = ("active", "company")

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "updated_at")
    list_filter = ("status",)

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "product", "quantity", "price_at_addition", "reserved_at")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "total", "created_at")
    list_filter = ("status",)

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "company", "quantity", "price")
    list_filter = ("company",)
