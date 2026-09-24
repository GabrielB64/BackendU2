from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction, models
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Company, Product, Cart, CartItem, Order, OrderItem
from .serializers import (
    LoginTokenSerializer, CompanyTokenSerializer,
    ClientRegisterSerializer, CompanyRegisterSerializer,
    ProductSerializer, CartSerializer, OrderSerializer
)
from .validators import normalize_rut


# ---------- HTML pages ----------

def index_page(request):
    return render(request, "index.html")

def client_login_page(request):
    return render(request, "auth/client_login.html")

def company_login_page(request):
    return render(request, "auth/company_login.html")

def client_register_page(request):
    return render(request, "auth/client_register.html")

def company_register_page(request):
    return render(request, "auth/company_register.html")

def cart_page(request):
    return render(request, "cart/cart.html")

def company_dashboard_page(request):
    return render(request, "company/dashboard.html")

def company_products_page(request):
    return render(request, "company/products.html")

def company_product_form_page(request):
    return render(request, "company/product_form.html")


# ---------- JWT ----------

class ClientTokenView(TokenObtainPairView):
    serializer_class = LoginTokenSerializer


class CompanyTokenView(TokenObtainPairView):
    serializer_class = CompanyTokenSerializer


# ---------- Registration ----------

@api_view(["POST"])
@permission_classes([AllowAny])
def client_register(request):
    serializer = ClientRegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response({
        "message": "Cuenta creada correctamente.",
        "user": {
            "id": user.id,
            "rut": user.rut,
            "email": user.email,
            "user_type": user.user_type,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def company_register(request):
    serializer = CompanyRegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response({
        "message": "Empresa creada correctamente.",
        "company": {
            "id": user.company.id,
            "name": user.company.name,
            "rut": user.company.rut,
        }
    }, status=status.HTTP_201_CREATED)


# ---------- Public products ----------

@api_view(["GET"])
@permission_classes([AllowAny])
def public_products(request):
    products = Product.objects.filter(
        active=True,
        company__active=True
    ).select_related("company")

    return Response(ProductSerializer(products, many=True, context={"request": request}).data)


# ---------- Cart ----------

def get_active_cart(user):
    cart, _ = Cart.objects.get_or_create(
        user=user,
        defaults={"status": Cart.Status.ACTIVE}
    )
    if cart.status != Cart.Status.ACTIVE:
        cart.status = Cart.Status.ACTIVE
        cart.save(update_fields=["status", "updated_at"])
    return cart


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cart_detail(request):
    cart = get_active_cart(request.user)
    return Response(CartSerializer(cart, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cart_add_item(request):
    product_id = request.data.get("product")
    quantity = request.data.get("quantity", 1)

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return Response({"detail": "La cantidad debe ser un número entero."}, status=400)

    if quantity < 1:
        return Response({"detail": "La cantidad debe ser mayor que cero."}, status=400)

    try:
        with transaction.atomic():
            product = Product.objects.select_for_update().select_related("company").get(
                id=product_id, active=True, company__active=True
            )
            cart = get_active_cart(request.user)

            existing = cart.items.filter(product=product).first()
            current_quantity = existing.quantity if existing else 0

            reserved_by_others = CartItem.objects.filter(
                product=product,
                cart__status=Cart.Status.ACTIVE
            ).exclude(cart=cart).aggregate(total=Sum("quantity"))["total"] or 0

            if reserved_by_others + current_quantity + quantity > product.stock:
                available = max(product.stock - reserved_by_others - current_quantity, 0)
                return Response(
                    {"detail": f"No hay suficiente stock. Disponible para agregar: {available}."},
                    status=409
                )

            if existing:
                existing.quantity += quantity
                existing.save(update_fields=["quantity"])
                item = existing
            else:
                item = CartItem.objects.create(
                    cart=cart,
                    product=product,
                    quantity=quantity,
                    price_at_addition=product.price
                )

    except Product.DoesNotExist:
        return Response({"detail": "Producto no encontrado."}, status=404)

    return Response({
        "message": "Producto reservado y agregado al carrito.",
        "item_id": item.id
    }, status=201)


@api_view(["PATCH", "PUT"])
@permission_classes([IsAuthenticated])
def cart_update_item(request, item_id):
    try:
        quantity = int(request.data.get("quantity"))
    except (TypeError, ValueError):
        return Response({"detail": "Cantidad inválida."}, status=400)

    if quantity < 1:
        return Response({"detail": "La cantidad debe ser mayor que cero."}, status=400)

    try:
        with transaction.atomic():
            item = CartItem.objects.select_for_update().select_related("product").get(
                id=item_id, cart__user=request.user, cart__status=Cart.Status.ACTIVE
            )
            product = Product.objects.select_for_update().get(id=item.product_id)

            reserved_by_others = CartItem.objects.filter(
                product=product,
                cart__status=Cart.Status.ACTIVE
            ).exclude(cart=item.cart).aggregate(total=Sum("quantity"))["total"] or 0

            if reserved_by_others + quantity > product.stock:
                available = max(product.stock - reserved_by_others, 0)
                return Response({"detail": f"Stock insuficiente. Disponible: {available}."}, status=409)

            item.quantity = quantity
            item.save(update_fields=["quantity"])

    except CartItem.DoesNotExist:
        return Response({"detail": "Item no encontrado."}, status=404)

    return Response({"message": "Cantidad actualizada."})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def cart_remove_item(request, item_id):
    deleted, _ = CartItem.objects.filter(
        id=item_id,
        cart__user=request.user,
        cart__status=Cart.Status.ACTIVE
    ).delete()

    if not deleted:
        return Response({"detail": "Item no encontrado."}, status=404)

    return Response({"message": "Producto liberado y eliminado del carrito."})


# ---------- Checkout ----------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def checkout(request):
    with transaction.atomic():
        cart = get_active_cart(request.user)
        items = list(
            cart.items.select_related("product", "product__company").all()
        )

        if not items:
            return Response({"detail": "El carrito está vacío."}, status=400)

        locked_products = {
            p.id: p
            for p in Product.objects.select_for_update().filter(
                id__in=[item.product_id for item in items]
            ).select_related("company")
        }

        total = Decimal("0.00")

        for item in items:
            product = locked_products[item.product_id]
            if not product.active or not product.company.active:
                return Response({"detail": f"El producto {product.name} ya no está disponible."}, status=409)

            if item.quantity > product.stock:
                return Response({"detail": f"El producto {product.name} ya no tiene suficiente stock."}, status=409)

            total += item.price_at_addition * item.quantity

        order = Order.objects.create(
            customer=request.user,
            total=total,
            status=Order.Status.PENDING
        )

        for item in items:
            product = locked_products[item.product_id]
            OrderItem.objects.create(
                order=order,
                product=product,
                company=product.company,
                quantity=item.quantity,
                price=item.price_at_addition
            )
            product.stock -= item.quantity
            product.save(update_fields=["stock", "updated_at"])

        cart.status = Cart.Status.COMPLETED
        cart.save(update_fields=["status", "updated_at"])
        cart.items.all().delete()

    return Response(
        OrderSerializer(order, context={"request": request}).data,
        status=201
    )


# ---------- Company API ----------

def company_required(request):
    return (
        request.user.is_authenticated
        and request.user.user_type == request.user.UserType.COMPANY
        and hasattr(request.user, "company")
        and request.user.company.active
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_products(request):
    if not company_required(request):
        return Response({"detail": "Se requiere una cuenta de empresa."}, status=403)

    products = request.user.company.products.all()
    return Response(ProductSerializer(products, many=True, context={"request": request}).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def company_product_create(request):
    if not company_required(request):
        return Response({"detail": "Se requiere una cuenta de empresa."}, status=403)

    serializer = ProductSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(company=request.user.company)
    return Response(serializer.data, status=201)


@api_view(["GET", "PATCH", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def company_product_detail(request, product_id):
    if not company_required(request):
        return Response({"detail": "Se requiere una cuenta de empresa."}, status=403)

    try:
        product = request.user.company.products.get(id=product_id)
    except Product.DoesNotExist:
        return Response({"detail": "Producto no encontrado."}, status=404)

    if request.method == "GET":
        return Response(ProductSerializer(product, context={"request": request}).data)

    if request.method in ["PATCH", "PUT"]:
        serializer = ProductSerializer(product, data=request.data, partial=request.method == "PATCH")
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    product.active = False
    product.save(update_fields=["active", "updated_at"])
    return Response({"message": "Producto desactivado."})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_dashboard(request):
    if not company_required(request):
        return Response({"detail": "Se requiere una cuenta de empresa."}, status=403)

    company = request.user.company

    order_items = OrderItem.objects.filter(
        company=company,
        order__status__in=[
            Order.Status.PENDING,
            Order.Status.PAID,
            Order.Status.PROCESSING,
            Order.Status.SHIPPED,
            Order.Status.COMPLETED,
        ]
    ).select_related("order", "order__customer", "product")

    total_sales = order_items.aggregate(
        total=Sum(models.F("quantity") * models.F("price"))
    )["total"] or Decimal("0.00")

    order_ids = order_items.values_list("order_id", flat=True).distinct()

    daily = order_items.annotate(
        day=TruncDate("order__created_at")
    ).values("day").annotate(
        total=Sum(models.F("quantity") * models.F("price"))
    ).order_by("day")

    recent_orders = (
        Order.objects.filter(id__in=order_ids)
        .prefetch_related("items")
        .order_by("-created_at")[:20]
    )

    return Response({
        "company": {
            "id": company.id,
            "name": company.name,
            "rut": company.rut,
        },
        "total_sales": total_sales,
        "product_count": company.products.filter(active=True).count(),
        "order_count": len(order_ids),
        "sales": {
            "labels": [row["day"].strftime("%Y-%m-%d") for row in daily],
            "values": [row["total"] for row in daily],
        },
        "recent_orders": [
            {
                "id": order.id,
                "customer": order.customer.get_full_name() or order.customer.rut,
                "date": order.created_at.strftime("%Y-%m-%d %H:%M"),
                "total": sum(
                    (item.subtotal for item in order.items.all()
                     if item.company_id == company.id),
                    Decimal("0.00")
                ),
                "status": order.get_status_display(),
            }
            for order in recent_orders
        ],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_orders(request):
    if not company_required(request):
        return Response({"detail": "Se requiere una cuenta de empresa."}, status=403)

    order_ids = OrderItem.objects.filter(
        company=request.user.company
    ).values_list("order_id", flat=True).distinct()

    orders = Order.objects.filter(
        id__in=order_ids
    ).select_related("customer").order_by("-created_at")

    return Response(OrderSerializer(orders, many=True, context={"request": request}).data)



@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    from django.contrib.auth import get_user_model
    from .models import Company
    User = get_user_model()

    companies = Company.objects.select_related("owner").all().order_by("name")
    customers = User.objects.filter(
        user_type=User.UserType.CLIENT,
        is_superuser=False,
    ).order_by("username")

    return render(request, "admin/dashboard.html", {
        "companies": companies,
        "customers": customers,
    })
