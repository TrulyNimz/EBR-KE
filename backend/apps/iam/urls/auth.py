"""
Authentication URL routes.

POST /api/v1/auth/login/              - Login
POST /api/v1/auth/logout/             - Logout
POST /api/v1/auth/token/refresh/      - Refresh token
POST /api/v1/auth/password/change/    - Change password
POST /api/v1/auth/password/reset/     - Request password reset
POST /api/v1/auth/password/reset/confirm/ - Confirm password reset
POST /api/v1/auth/mfa/setup/          - Setup MFA
POST /api/v1/auth/mfa/verify/         - Verify MFA code
POST /api/v1/auth/mfa/disable/        - Disable MFA
"""
from django.urls import path
from apps.iam.views import (
    LoginView,
    LogoutView,
    TokenRefreshView,
    PasswordChangeView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    MFASetupView,
    MFAVerifyView,
    MFADisableView,
)

app_name = 'auth'

urlpatterns = [
    # Core authentication
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # Password management
    path('password/change/', PasswordChangeView.as_view(), name='password-change'),
    path('password/reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    # Multi-factor authentication
    path('mfa/setup/', MFASetupView.as_view(), name='mfa-setup'),
    path('mfa/verify/', MFAVerifyView.as_view(), name='mfa-verify'),
    path('mfa/disable/', MFADisableView.as_view(), name='mfa-disable'),
]
