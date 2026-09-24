# MiTienda - Django + DRF + SimpleJWT

Proyecto funcional de tienda multiempresa con:
- Clientes y empresas separados.
- JWT.
- Validación de RUT chileno.
- Selector de código telefónico.
- Productos con imágenes.
- Carrito con reserva de stock en base de datos.
- Checkout.
- Dashboard de empresa con gráfico.
- Tema claro/oscuro con Bootstrap 5.3.
- SQLite.

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Windows:
```powershell
.venv\Scripts\activate
```

Abrir:
http://127.0.0.1:8000/

Admin:
http://127.0.0.1:8000/admin/

## Flujo

Cliente:
1. Registrar cuenta.
2. Iniciar sesión con RUT y contraseña.
3. Agregar productos al carrito.
4. El stock queda reservado mientras el carrito está activo.
5. Confirmar compra.

Empresa:
1. Registrar empresa.
2. Iniciar sesión desde /login/company/.
3. Crear productos.
4. Ver productos.
5. Ver ventas y estadísticas en /company/dashboard/.

La reserva se calcula desde CartItem y solamente cuenta carritos ACTIVE.
El checkout descuenta el stock físico y transforma el carrito en COMPLETED.

## Mock data

After migrations, populate the development database with:

```bash
python manage.py seed_mock_data
```

This creates:
- 2 companies
- 20 products for each company
- 1 demo customer

Demo passwords:
- Companies: `Demo1234!`
- Customer: `Demo1234!`

The admin dashboard is available at:

```text
/admin-dashboard/
```

It is restricted to Django superusers.
