"""
Root conftest for EBR Platform test suite.

Provides shared fixtures for tenant creation, authenticated API clients,
and test data factories.
"""
import pytest
from django_tenants.utils import schema_context


# ---------------------------------------------------------------------------
# Tenant fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='session')
def tenant(django_db_setup, django_db_blocker):
    """Create a test tenant and return it. Session-scoped for performance."""
    with django_db_blocker.unblock():
        from apps.tenants.models import Tenant, Domain

        # Ensure public schema tenant exists
        public, _ = Tenant.objects.get_or_create(
            schema_name='public',
            defaults={'name': 'Public', 'is_active': True},
        )
        Domain.objects.get_or_create(
            domain='localhost',
            defaults={'tenant': public, 'is_primary': True},
        )

        # Create dedicated test tenant
        test_tenant, created = Tenant.objects.get_or_create(
            schema_name='test_co',
            defaults={'name': 'Test Company', 'is_active': True},
        )
        Domain.objects.get_or_create(
            domain='test-co.localhost',
            defaults={'tenant': test_tenant, 'is_primary': True},
        )

        return test_tenant


@pytest.fixture
def tenant_schema(tenant):
    """Activate the test tenant schema for a test."""
    with schema_context(tenant.schema_name):
        yield tenant


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_user(tenant_schema):
    """Superuser for tests that need admin privileges."""
    from apps.iam.models import User

    user = User.objects.create_superuser(
        email='admin@test.local',
        password='Admin@Test123',
        first_name='Admin',
        last_name='User',
    )
    return user


@pytest.fixture
def regular_user(tenant_schema):
    """Regular non-admin user with no special permissions."""
    from apps.iam.models import User

    user = User.objects.create_user(
        email='user@test.local',
        password='User@Test123',
        first_name='Test',
        last_name='User',
    )
    return user


# ---------------------------------------------------------------------------
# API client fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    """Unauthenticated DRF APIClient."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def admin_client(api_client, admin_user, tenant):
    """APIClient authenticated as admin, with tenant header set."""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    api_client.defaults['SERVER_NAME'] = 'test-co.localhost'
    return api_client


@pytest.fixture
def user_client(api_client, regular_user, tenant):
    """APIClient authenticated as regular user, with tenant header set."""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(regular_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    api_client.defaults['SERVER_NAME'] = 'test-co.localhost'
    return api_client
