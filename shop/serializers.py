from django.db import transaction
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Company, Product, Cart, CartItem, Order, OrderItem
from .validators import validate_rut, normalize_rut


class LoginTokenSerializer(TokenObtainPairSerializer):
    username_field = "rut"

    def validate(self, attrs):
        attrs["rut"] = normalize_rut(attrs.get("rut"))
        data = super().validate(attrs)
        if self.user.user_type != User.UserType.CLIENT:
            raise serializers.ValidationError("Esta cuenta pertenece al portal de empresas.")
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["user_type"] = user.user_type
        token["rut"] = user.rut
        if user.user_type == User.UserType.COMPANY and hasattr(user, "company"):
            token["company_id"] = user.company.id
        return token


class CompanyTokenSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["user_type"] = user.user_type
        token["rut"] = user.rut
        token["company_id"] = user.company.id
        return token

    def validate(self, attrs):
        rut = normalize_rut(self.initial_data.get("rut"))
        password = self.initial_data.get("password")
        try:
            company = Company.objects.select_related("owner").get(rut=rut, active=True)
        except Company.DoesNotExist:
            raise serializers.ValidationError("Credenciales de empresa inválidas.")
        user = authenticate(username=company.owner.rut, password=password)
        if not user or user.user_type != User.UserType.COMPANY:
            raise serializers.ValidationError("Credenciales de empresa inválidas.")
        attrs["rut"] = user.rut
        attrs["password"] = password
        return super().validate(attrs)


class ClientRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "rut", "email",
            "phone_country_code", "phone_number",
            "password", "password_confirm"
        ]

    def validate_rut(self, value):
        return validate_rut(value)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Las contraseñas no coinciden."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        return User.objects.create_user(
            password=password,
            user_type=User.UserType.CLIENT,
            **validated_data
        )


class CompanyRegisterSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=150)
    company_rut = serializers.CharField(max_length=12)
    description = serializers.CharField(required=False, allow_blank=True)
    representative_first_name = serializers.CharField(max_length=150)
    representative_last_name = serializers.CharField(max_length=150)
    representative_rut = serializers.CharField(max_length=12)
    email = serializers.EmailField()
    phone_country_code = serializers.CharField(max_length=6)
    phone_number = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    def validate_company_rut(self, value):
        return validate_rut(value)

    def validate_representative_rut(self, value):
        return validate_rut(value)

    def validate_phone_number(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("El teléfono debe contener solamente números.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Las contraseñas no coinciden."})
        if User.objects.filter(rut=normalize_rut(attrs["representative_rut"])).exists():
            raise serializers.ValidationError({"representative_rut": "Ese RUT ya está registrado."})
        if User.objects.filter(email=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "Ese correo ya está registrado."})
        if Company.objects.filter(rut=normalize_rut(attrs["company_rut"])).exists():
            raise serializers.ValidationError({"company_rut": "Ese RUT de empresa ya está registrado."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        company_name = validated_data.pop("company_name")
        company_rut = validated_data.pop("company_rut")
        description = validated_data.pop("description", "")
        password = validated_data.pop("password")
        validated_data.pop("password_confirm")
        first_name = validated_data.pop("representative_first_name")
        last_name = validated_data.pop("representative_last_name")
        representative_rut = validated_data.pop("representative_rut")

        user = User.objects.create_user(
            rut=representative_rut,
            email=validated_data["email"],
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_country_code=validated_data["phone_country_code"],
            phone_number=validated_data["phone_number"],
            user_type=User.UserType.COMPANY,
        )
        Company.objects.create(
            owner=user,
            name=company_name,
            rut=company_rut,
            description=description,
        )
        return user


class ProductSerializer(serializers.ModelSerializer):
    available_stock = serializers.IntegerField(read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "company", "company_name", "name", "description",
            "image", "price", "stock", "available_stock", "active",
            "created_at", "updated_at"
        ]
        read_only_fields = ["company", "available_stock", "company_name"]


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product", "product_id", "quantity", "price_at_addition", "subtotal", "reserved_at"]
        read_only_fields = ["price_at_addition", "reserved_at"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "status", "items", "total", "created_at", "updated_at"]

    def get_total(self, obj):
        return sum((item.subtotal for item in obj.items.all()), 0)


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "company", "quantity", "price", "subtotal"]

    def get_subtotal(self, obj):
        return obj.subtotal


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "status", "total", "created_at", "updated_at", "items"]
