import base64
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.contrib.auth import get_user_model

from shop.models import Company, Product


# Valid 1x1 transparent PNG used so Product.image is populated without external files.
PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class Command(BaseCommand):
    help = "Creates deterministic demo data: 2 companies, 20 products each, and 1 demo customer."

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        companies_data = [
            {
                "rut": "76.543.210-3",
                "email": "admin@tecnomax.cl",
                "password": "Demo1234!",
                "name": "TecnoMax Chile",
                "company_rut": "76.543.210-3",
                "phone_number": "961234567",
                "description": "Tecnología, computación y accesorios.",
            },
            {
                "rut": "77.654.321-7",
                "email": "admin@hogarplus.cl",
                "password": "Demo1234!",
                "name": "HogarPlus",
                "company_rut": "77.654.321-7",
                "phone_number": "972345678",
                "description": "Productos para hogar, cocina y vida diaria.",
            },
        ]

        companies = []
        for data in companies_data:
            user, _ = User.objects.get_or_create(
                rut=data["rut"],
                defaults={
                    "email": data["email"],
                    "phone_country_code": "+56",
                    "phone_number": data["phone_number"],
                    "user_type": User.UserType.COMPANY,
                },
            )
            user.email = data["email"]
            user.phone_country_code = "+56"
            user.phone_number = data["phone_number"]
            user.user_type = User.UserType.COMPANY
            user.set_password(data["password"])
            user.save()

            company, _ = Company.objects.get_or_create(
                owner=user,
                defaults={
                    "name": data["name"],
                    "rut": data["company_rut"],
                    "description": data["description"],
                },
            )
            company.name = data["name"]
            company.rut = data["company_rut"]
            company.description = data["description"]
            company.active = True
            company.save()
            companies.append(company)

        # Customer demo account.
        customer, _ = User.objects.get_or_create(
            rut="12.345.678-5",
            defaults={
                "email": "cliente@example.com",
                "first_name": "Cliente",
                "last_name": "Demo",
                "phone_country_code": "+56",
                "phone_number": "912345678",
                "user_type": User.UserType.CLIENT,
            },
        )
        customer.email = "cliente@example.com"
        customer.first_name = "Cliente"
        customer.last_name = "Demo"
        customer.phone_country_code = "+56"
        customer.phone_number = "912345678"
        customer.user_type = User.UserType.CLIENT
        customer.set_password("Demo1234!")
        customer.save()

        products_a = [
            ("Notebook Lenovo IdeaPad 3", 549990, 12),
            ("Mouse Logitech M185", 9990, 35),
            ("Teclado Mecánico Redragon K552", 39990, 18),
            ("Monitor LG 24MP400", 129990, 10),
            ("SSD Kingston NV2 1TB", 69990, 22),
            ("Memoria RAM Kingston 16GB DDR4", 44990, 30),
            ("Audífonos HyperX Cloud Stinger 2", 49990, 14),
            ("Webcam Logitech C920", 79990, 9),
            ("Hub USB-C 7 en 1", 29990, 25),
            ("Disco Externo Seagate 2TB", 74990, 16),
            ("Router TP-Link Archer C6", 44990, 20),
            ("Control Xbox Wireless", 64990, 11),
            ("Cable HDMI 2.1 2m", 14990, 40),
            ("Pad Mouse RGB", 17990, 27),
            ("Soporte Notebook Aluminio", 24990, 21),
            ("Parlante Bluetooth JBL Go 4", 49990, 13),
            ("Cargador USB-C 65W", 32990, 19),
            ("Memoria USB Kingston 128GB", 12990, 45),
            ("Lector de Tarjetas USB-C", 11990, 31),
            ("UPS APC 650VA", 69990, 8),
        ]

        products_b = [
            ("Aspiradora Vertical 2 en 1", 89990, 12),
            ("Freidora de Aire 4L", 59990, 15),
            ("Hervidor Eléctrico 1.7L", 19990, 30),
            ("Set de Ollas 7 Piezas", 79990, 9),
            ("Sartén Antiadherente 28cm", 24990, 22),
            ("Cafetera Programable", 54990, 14),
            ("Licuadora 600W", 39990, 17),
            ("Organizador Multiuso 6 Cajones", 34990, 18),
            ("Lámpara LED de Escritorio", 19990, 25),
            ("Set de Toallas 6 Piezas", 29990, 20),
            ("Juego de Sábanas 2 Plazas", 39990, 16),
            ("Almohada Memory Foam", 24990, 24),
            ("Perchero Metálico", 22990, 19),
            ("Repisa Flotante 80cm", 17990, 28),
            ("Set de Contenedores Herméticos", 29990, 23),
            ("Balanza Digital de Cocina", 12990, 32),
            ("Plancha a Vapor", 44990, 11),
            ("Ventilador de Pie 16\"", 49990, 13),
            ("Humidificador Ultrasónico", 32990, 15),
            ("Set de Vasos 6 Unidades", 14990, 35),
        ]

        for company, definitions in zip(companies, (products_a, products_b)):
            for i, (name, price, stock) in enumerate(definitions, start=1):
                image = SimpleUploadedFile(
                    f"demo-{company.pk}-{i:02d}.png",
                    PLACEHOLDER_PNG,
                    content_type="image/png",
                )
                product, created = Product.objects.get_or_create(
                    company=company,
                    name=name,
                    defaults={
                        "description": f"Producto demo de {company.name}. SKU DEMO-{company.id}-{i:02d}.",
                        "price": price,
                        "stock": stock,
                        "active": True,
                        "image": image,
                    },
                )
                if not created:
                    product.description = f"Producto demo de {company.name}. SKU DEMO-{company.id}-{i:02d}."
                    product.price = price
                    product.stock = stock
                    product.active = True
                    product.save(update_fields=["description", "price", "stock", "active", "updated_at"])

        self.stdout.write(self.style.SUCCESS(
            "Mock data created successfully: 2 companies, 20 products per company, and 1 demo customer."
        ))
        self.stdout.write("Company login 1: RUT 76.543.210-3 / Demo1234!")
        self.stdout.write("Company login 2: RUT 77.654.321-7 / Demo1234!")
        self.stdout.write("Customer login: RUT 12.345.678-5 / Demo1234!")
