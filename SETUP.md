# EBR Platform — Developer Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ running locally (or Docker)
- Redis 7+ running locally (or Docker)
- Docker & Docker Compose (optional, for full stack)

---

## Option A: Docker (recommended for full stack)

```bash
# Start all services (PostgreSQL, Redis, Django, Celery, Next.js)
docker compose up --build

# In a separate terminal, run migrations and seed data
docker compose exec backend python manage.py migrate_schemas --shared
docker compose exec backend python manage.py migrate_schemas
docker compose exec backend python manage.py seed_dev_data
```

Access:
- Frontend: http://localhost:3000
- API: http://localhost:8000/api/v1/
- API Docs: http://localhost:8000/api/docs/
- Admin: http://localhost:8000/admin/

---

## Option B: Local Development (no Docker)

### 1. Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
.venv\Scripts\activate          # Windows

# Install dependencies
pip install -r requirements-dev.txt

# Copy and edit environment file
cp .env.example .env
# Edit .env — set DB_PASSWORD and ensure PostgreSQL is running

# Create the database and user in PostgreSQL:
# psql -U postgres
#   CREATE USER ebr_user WITH PASSWORD 'ebr_dev_password_2024';
#   CREATE DATABASE ebr_platform OWNER ebr_user;
#   \q

# Run migrations
# Step 1: Migrate shared (public) schema first — this creates the tenants table
python manage.py migrate_schemas --shared

# Step 2: Migrate all tenant schemas
python manage.py migrate_schemas

# Step 3: Seed development data (creates tenant, superuser, roles, sample template)
python manage.py seed_dev_data

# Start the development server
python manage.py runserver
```

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Copy and edit environment file
cp .env.local.example .env.local
# .env.local is already configured for localhost — no changes needed for local dev

# Start the development server
npm run dev
```

### 3. Celery (optional, needed for async notifications)

```bash
# In a separate terminal with the venv activated
cd backend
celery -A config worker -l INFO

# In another terminal for the beat scheduler
celery -A config beat -l INFO
```

---

## Login Credentials (after seed_dev_data)

| Field    | Value                       |
|----------|-----------------------------|
| Email    | admin@dev-company.local     |
| Password | Admin@1234567               |

---

## Tenant Domain Setup

The development tenant is registered with domain `dev-company.localhost`.

For the middleware to route correctly, you have two options:

**Option 1**: Add to your hosts file:
```
127.0.0.1   dev-company.localhost
```

**Option 2**: Use `127.0.0.1` directly — the seed command also registers this IP
as a domain for the dev tenant.

---

## Common Commands

```bash
# Generate new migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate_schemas

# Create a new tenant (in Django shell)
python manage.py shell
>>> from apps.tenants.models import Tenant, Domain
>>> t = Tenant(name="Acme Corp", schema_name="acme", slug="acme", industry="manufacturing")
>>> t.save()
>>> Domain.objects.create(domain="acme.localhost", tenant=t, is_primary=True)

# Run tests
pytest

# Format code
black .
isort .
```

---

## Architecture Notes

- **Multi-tenancy**: Each tenant gets a separate PostgreSQL schema (`django-tenants`)
- **Authentication**: JWT tokens via `djangorestframework-simplejwt`
- **URL structure**: `http://localhost:8000/api/v1/{resource}/`
- **Batch steps**: Nested under batches → `/api/v1/batches/{id}/steps/`
- **Notifications**: Available at `/api/v1/notifications/`
- **Audit logs**: Available at `/api/v1/audit/logs/`
