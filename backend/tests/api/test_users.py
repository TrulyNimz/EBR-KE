"""
Integration tests for the User Management API.

Covers: list, create, get, update, lock/unlock, force password reset.
"""
import pytest

BASE = '/api/v1/users'


@pytest.mark.django_db
class TestUserList:
    """GET /api/v1/users/"""

    def test_admin_can_list_users(self, admin_client, admin_user, tenant):
        resp = admin_client.get(f'{BASE}/')
        assert resp.status_code == 200
        data = resp.json()
        assert 'results' in data
        assert data['count'] >= 1

    def test_unauthenticated_returns_401(self, api_client, tenant):
        resp = api_client.get(f'{BASE}/')
        assert resp.status_code == 401

    def test_search_by_email(self, admin_client, admin_user, tenant):
        resp = admin_client.get(f'{BASE}/?search=admin@test.local')
        assert resp.status_code == 200
        results = resp.json()['results']
        assert any(u['email'] == 'admin@test.local' for u in results)

    def test_filter_by_active_status(self, admin_client, admin_user, tenant):
        resp = admin_client.get(f'{BASE}/?is_active=true')
        assert resp.status_code == 200
        for user in resp.json()['results']:
            assert user['is_active'] is True


@pytest.mark.django_db
class TestUserCreate:
    """POST /api/v1/users/"""

    def test_admin_can_create_user(self, admin_client, tenant):
        resp = admin_client.post(
            f'{BASE}/',
            {
                'email': 'new.user@test.local',
                'employee_id': 'EMP-001',
                'first_name': 'New',
                'last_name': 'User',
                'password': 'NewUser@Test123',
                'confirm_password': 'NewUser@Test123',
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data['email'] == 'new.user@test.local'

    def test_duplicate_email_returns_400(self, admin_client, admin_user, tenant):
        resp = admin_client.post(
            f'{BASE}/',
            {
                'email': 'admin@test.local',  # already exists
                'first_name': 'Dup',
                'last_name': 'User',
                'password': 'DupUser@Test123',
                'confirm_password': 'DupUser@Test123',
            },
        )
        assert resp.status_code == 400

    def test_password_mismatch_returns_400(self, admin_client, tenant):
        resp = admin_client.post(
            f'{BASE}/',
            {
                'email': 'mismatch@test.local',
                'first_name': 'X',
                'last_name': 'Y',
                'password': 'Pass@1234',
                'confirm_password': 'Different@5678',
            },
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestUserDetail:
    """GET /api/v1/users/{id}/"""

    def test_admin_can_get_user(self, admin_client, admin_user, tenant):
        resp = admin_client.get(f'{BASE}/{admin_user.id}/')
        assert resp.status_code == 200
        assert resp.json()['email'] == admin_user.email

    def test_nonexistent_user_returns_404(self, admin_client, tenant):
        import uuid
        resp = admin_client.get(f'{BASE}/{uuid.uuid4()}/')
        assert resp.status_code == 404


@pytest.mark.django_db
class TestCurrentUser:
    """GET/PATCH /api/v1/users/me/"""

    def test_me_returns_authenticated_user(self, admin_client, admin_user, tenant):
        resp = admin_client.get(f'{BASE}/me/')
        assert resp.status_code == 200
        assert resp.json()['email'] == admin_user.email

    def test_me_unauthenticated_returns_401(self, api_client, tenant):
        resp = api_client.get(f'{BASE}/me/')
        assert resp.status_code == 401

    def test_me_patch_updates_name(self, admin_client, admin_user, tenant):
        resp = admin_client.patch(
            f'{BASE}/me/',
            {'first_name': 'Updated'},
        )
        assert resp.status_code == 200
        assert resp.json()['first_name'] == 'Updated'


@pytest.mark.django_db
class TestUserLockUnlock:
    """POST /api/v1/users/{id}/lock/ and /unlock/"""

    def test_admin_can_lock_user(self, admin_client, regular_user, tenant):
        resp = admin_client.post(f'{BASE}/{regular_user.id}/lock/')
        assert resp.status_code == 200
        regular_user.refresh_from_db()
        assert regular_user.is_locked is True

    def test_admin_can_unlock_user(self, admin_client, regular_user, tenant_schema):
        from apps.iam.models import User
        regular_user.lock_account(reason='test')
        resp = admin_client.post(f'{BASE}/{regular_user.id}/unlock/')
        assert resp.status_code == 200
        regular_user.refresh_from_db()
        assert regular_user.is_locked is False


@pytest.mark.django_db
class TestForcePasswordReset:
    """POST /api/v1/users/{id}/reset_password/"""

    def test_admin_can_force_password_reset(self, admin_client, regular_user, tenant):
        resp = admin_client.post(f'{BASE}/{regular_user.id}/reset_password/')
        assert resp.status_code == 200
        regular_user.refresh_from_db()
        assert regular_user.must_change_password is True
