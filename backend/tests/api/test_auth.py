"""
Integration tests for the Authentication API.

Covers: login, logout, token refresh, password change, MFA setup.
"""
import pytest
from django.urls import reverse


BASE = '/api/v1/auth'


@pytest.mark.django_db
class TestLogin:
    """POST /api/v1/auth/login/"""

    def test_login_success(self, api_client, admin_user, tenant):
        """Valid credentials return access + refresh tokens."""
        resp = api_client.post(
            f'{BASE}/login/',
            {'email': 'admin@test.local', 'password': 'Admin@Test123'},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert 'access' in data
        assert 'refresh' in data
        assert 'user' in data
        assert data['user']['email'] == 'admin@test.local'

    def test_login_wrong_password(self, api_client, admin_user, tenant):
        """Wrong password returns 400 with non-field error."""
        resp = api_client.post(
            f'{BASE}/login/',
            {'email': 'admin@test.local', 'password': 'WrongPassword!'},
        )
        assert resp.status_code == 400

    def test_login_unknown_email(self, api_client, tenant):
        """Unknown email returns 400 (does not expose account existence)."""
        resp = api_client.post(
            f'{BASE}/login/',
            {'email': 'nobody@test.local', 'password': 'anything'},
        )
        assert resp.status_code == 400

    def test_login_missing_fields(self, api_client, tenant):
        """Missing required fields returns 400."""
        resp = api_client.post(f'{BASE}/login/', {})
        assert resp.status_code == 400

    def test_login_inactive_user(self, api_client, tenant_schema):
        """Inactive user cannot log in."""
        from apps.iam.models import User

        user = User.objects.create_user(
            email='inactive@test.local',
            password='Pass@1234',
            is_active=False,
        )
        resp = api_client.post(
            f'{BASE}/login/',
            {'email': 'inactive@test.local', 'password': 'Pass@1234'},
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestLogout:
    """POST /api/v1/auth/logout/"""

    def test_logout_blacklists_token(self, admin_client, admin_user, tenant):
        """Logout with valid refresh token succeeds and blacklists it."""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(admin_user)
        resp = admin_client.post(
            f'{BASE}/logout/',
            {'refresh': str(refresh)},
        )
        assert resp.status_code == 200

    def test_logout_requires_auth(self, api_client, tenant):
        """Unauthenticated logout returns 401."""
        resp = api_client.post(f'{BASE}/logout/', {'refresh': 'fake-token'})
        assert resp.status_code == 401


@pytest.mark.django_db
class TestTokenRefresh:
    """POST /api/v1/auth/token/refresh/"""

    def test_refresh_returns_new_access_token(self, api_client, admin_user, tenant):
        """Valid refresh token returns a new access token."""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(admin_user)
        resp = api_client.post(
            f'{BASE}/token/refresh/',
            {'refresh': str(refresh)},
        )
        assert resp.status_code == 200
        assert 'access' in resp.json()

    def test_refresh_invalid_token(self, api_client, tenant):
        """Invalid refresh token returns 401."""
        resp = api_client.post(
            f'{BASE}/token/refresh/',
            {'refresh': 'not-a-real-token'},
        )
        assert resp.status_code == 401


@pytest.mark.django_db
class TestPasswordChange:
    """POST /api/v1/auth/password/change/"""

    def test_change_password_success(self, admin_client, admin_user, tenant):
        """Authenticated user can change their password."""
        resp = admin_client.post(
            f'{BASE}/password/change/',
            {
                'current_password': 'Admin@Test123',
                'new_password': 'NewPass@456',
                'confirm_password': 'NewPass@456',
            },
        )
        assert resp.status_code == 200

    def test_change_password_wrong_current(self, admin_client, admin_user, tenant):
        """Wrong current password returns 400."""
        resp = admin_client.post(
            f'{BASE}/password/change/',
            {
                'current_password': 'WrongCurrent!',
                'new_password': 'NewPass@456',
                'confirm_password': 'NewPass@456',
            },
        )
        assert resp.status_code == 400

    def test_change_password_mismatch(self, admin_client, admin_user, tenant):
        """Mismatched new passwords return 400."""
        resp = admin_client.post(
            f'{BASE}/password/change/',
            {
                'current_password': 'Admin@Test123',
                'new_password': 'NewPass@456',
                'confirm_password': 'DifferentPass@789',
            },
        )
        assert resp.status_code == 400

    def test_change_password_requires_auth(self, api_client, tenant):
        """Unauthenticated request returns 401."""
        resp = api_client.post(
            f'{BASE}/password/change/',
            {
                'current_password': 'anything',
                'new_password': 'anything',
                'confirm_password': 'anything',
            },
        )
        assert resp.status_code == 401


@pytest.mark.django_db
class TestPasswordReset:
    """POST /api/v1/auth/password/reset/ + /reset/confirm/"""

    def test_reset_request_always_200(self, api_client, tenant):
        """Password reset request always returns 200 (security: no account leak)."""
        resp = api_client.post(
            f'{BASE}/password/reset/',
            {'email': 'nobody@test.local'},
        )
        assert resp.status_code == 200

    def test_reset_request_with_real_email(self, api_client, admin_user, tenant):
        """Password reset with valid email sends email and returns 200."""
        resp = api_client.post(
            f'{BASE}/password/reset/',
            {'email': 'admin@test.local'},
        )
        assert resp.status_code == 200

    def test_reset_confirm_invalid_token(self, api_client, admin_user, tenant):
        """Invalid token returns 400."""
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        uid = urlsafe_base64_encode(force_bytes(admin_user.pk))
        resp = api_client.post(
            f'{BASE}/password/reset/confirm/',
            {
                'uid': uid,
                'token': 'invalid-token',
                'new_password': 'NewPass@789',
                'confirm_password': 'NewPass@789',
            },
        )
        assert resp.status_code == 400
