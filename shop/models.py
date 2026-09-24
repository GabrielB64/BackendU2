from decimal import Decimal
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator
from django.db import models
from .validators import validate_rut, normalize_rut


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, rut, email, password, **extra_fields):
        if not rut:
            raise ValueError("El RUT es obligatorio.")
        if not email:
            raise ValueError("El correo es obligatorio.")
        user = self.model(
            rut=normalize_rut(rut),
            email=self.normalize_email(email),
            **extra_fields,
        )
        user.username = user.rut
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, rut, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(rut, email, password, **extra_fields)

    def create_superuser(self, rut, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("user_type", User.UserType.CLIENT)
        return self._create_user(rut, email, password, **extra_fields)


class User(AbstractUser):
    class UserType(models.TextChoices):
        CLIENT = "CLIENT", "Cliente"
        COMPANY = "COMPANY", "Empresa"

    username = models.CharField(max_length=150, unique=True, editable=False)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    rut = models.CharField(max_length=12, unique=True, validators=[validate_rut])
    email = models.EmailField(unique=True)
    phone_country_code = models.CharField(max_length=6, default="+56")
    phone_number = models.CharField(max_length=20)
    user_type = models.CharField(max_length=10, choices=UserType.choices, default=UserType.CLIENT)

    USERNAME_FIELD = "rut"
    REQUIRED_FIELDS = ["email"]

    objects = UserManager()

    def save(self, *args, **kwargs):
        self.rut = normalize_rut(self.rut)
        self.username = self.rut
        super().save(*args, **kwargs)

    def __str__(self):
        return self.rut


class Company(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name="company")
    name = models.CharField(max_length=150)
    rut = models.CharField(max_length=12, unique=True, validators=[validate_rut])
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="companies/logos/", blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.rut = normalize_rut(self.rut)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/")
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    stock = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def reserved_stock(self):
        return self.cart_items.filter(cart__status=Cart.Status.ACTIVE).aggregate(
            total=models.Sum("quantity")
        )["total"] or 0

    @property
    def available_stock(self):
        return max(self.stock - self.reserved_stock, 0)

    def __str__(self):
        return self.name


class Cart(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activo"
        COMPLETED = "COMPLETED", "Completado"
        ABANDONED = "ABANDONED", "Abandonado"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Carrito de {self.user.rut}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    price_at_addition = models.DecimalField(max_digits=12, decimal_places=2)
    reserved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="unique_product_per_cart")
        ]

    @property
    def subtotal(self):
        return self.price_at_addition * self.quantity


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        PAID = "PAID", "Pagado"
        PROCESSING = "PROCESSING", "Procesando"
        SHIPPED = "SHIPPED", "Enviado"
        COMPLETED = "COMPLETED", "Completado"
        CANCELLED = "CANCELLED", "Cancelado"

    customer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantity * self.price
