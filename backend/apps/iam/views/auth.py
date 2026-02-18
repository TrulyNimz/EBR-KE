"""
Authentication views for the EBR Platform.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as JWTTokenRefreshView
from django.utils import timezone
from datetime import timedelta
import pyotp
import secrets

from apps.iam.serializers import (
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    MFASetupSerializer,
    MFAVerifySerializer,
)
from apps.iam.serializers.users import UserProfileSerializer


class LoginView(APIView):
    """
    User login endpoint.

    POST /api/v1/auth/login/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        # Record successful login
        user.record_successful_login(
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        # Add custom claims
        refresh['email'] = user.email
        refresh['employee_id'] = user.employee_id
        refresh['full_name'] = user.full_name

        # Serialize user data
        user_data = UserProfileSerializer(user, context={'request': request}).data

        response_data = {
            'user': user_data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'mfa_required': user.mfa_enabled,
        }

        # If MFA is enabled, don't include access token until verified
        if user.mfa_enabled:
            response_data['access'] = None
            response_data['mfa_token'] = str(refresh)  # Temporary token for MFA

        return Response(response_data, status=status.HTTP_200_OK)

    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class LogoutView(APIView):
    """
    User logout endpoint. Blacklists the refresh token.

    POST /api/v1/auth/logout/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            return Response(
                {'message': 'Successfully logged out.'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': 'Invalid token.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class TokenRefreshView(JWTTokenRefreshView):
    """
    Token refresh endpoint.

    POST /api/v1/auth/token/refresh/
    """
    pass


class PasswordChangeView(APIView):
    """
    Password change endpoint for authenticated users.

    POST /api/v1/auth/password/change/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user

        # Store current password hash in history
        user.password_history.append(user.password)
        user.password_history = user.password_history[-5:]  # Keep last 5

        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.password_changed_at = timezone.now()
        user.password_expires_at = timezone.now() + timedelta(days=90)
        user.must_change_password = False
        user.save()

        return Response(
            {'message': 'Password changed successfully.'},
            status=status.HTTP_200_OK
        )


class PasswordResetRequestView(APIView):
    """
    Request password reset email.

    POST /api/v1/auth/password/reset/
    Body: { "email": "user@example.com" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from django.contrib.auth.tokens import PasswordResetTokenGenerator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        from django.core.mail import send_mail
        from django.conf import settings
        from apps.iam.models import User

        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        # Always return 200 — never reveal whether account exists (security)
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return Response(
                {'message': 'If an account exists with this email, a reset link has been sent.'},
                status=status.HTTP_200_OK
            )

        token_generator = PasswordResetTokenGenerator()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)

        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        reset_link = f'{frontend_url}/reset-password?uid={uid}&token={token}'

        send_mail(
            subject='EBR Platform — Password Reset Request',
            message=(
                f'Hi {user.first_name or user.email},\n\n'
                f'You requested a password reset for your EBR Platform account.\n\n'
                f'Click the link below to reset your password (valid for 24 hours):\n'
                f'{reset_link}\n\n'
                f'If you did not request this, please ignore this email.\n\n'
                f'— EBR Platform Security'
            ),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@ebr-platform.local'),
            recipient_list=[user.email],
            fail_silently=True,
        )

        return Response(
            {'message': 'If an account exists with this email, a reset link has been sent.'},
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(APIView):
    """
    Confirm password reset with token from email.

    POST /api/v1/auth/password/reset/confirm/
    Body: { "uid": "...", "token": "...", "new_password": "...", "confirm_password": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from django.contrib.auth.tokens import PasswordResetTokenGenerator
        from django.utils.encoding import force_str
        from django.utils.http import urlsafe_base64_decode
        from apps.iam.models import User

        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Decode uid
        try:
            uid = force_str(urlsafe_base64_decode(serializer.validated_data['uid']))
            user = User.objects.get(pk=uid, is_active=True)
        except (TypeError, ValueError, User.DoesNotExist):
            return Response(
                {'error': 'Invalid or expired reset link.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate token
        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(user, serializer.validated_data['token']):
            return Response(
                {'error': 'Invalid or expired reset link.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password with history tracking
        new_password = serializer.validated_data['new_password']
        user.password_history = (user.password_history or [])[-4:]  # Keep last 4 before setting new
        user.password_history.append(user.password)
        user.set_password(new_password)
        user.password_changed_at = timezone.now()
        user.password_expires_at = timezone.now() + timedelta(days=90)
        user.must_change_password = False
        user.failed_login_attempts = 0
        user.is_locked = False
        user.save()

        return Response(
            {'message': 'Password has been reset successfully.'},
            status=status.HTTP_200_OK
        )


class MFASetupView(APIView):
    """
    Setup MFA (TOTP) for the authenticated user.

    POST /api/v1/auth/mfa/setup/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.mfa_enabled:
            return Response(
                {'error': 'MFA is already enabled.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate TOTP secret
        secret = pyotp.random_base32()
        user.mfa_secret = secret
        user.save(update_fields=['mfa_secret'])

        # Generate QR code URI
        totp = pyotp.TOTP(secret)
        qr_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name='EBR Platform'
        )

        # Generate backup codes
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]

        return Response({
            'secret': secret,
            'qr_uri': qr_uri,
            'backup_codes': backup_codes,
            'message': 'Scan the QR code with your authenticator app, then verify with a code.'
        })


class MFAVerifyView(APIView):
    """
    Verify MFA code and complete setup or login.

    POST /api/v1/auth/mfa/verify/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MFAVerifySerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user

        # If MFA not yet enabled, this is completing setup
        if not user.mfa_enabled:
            # Store backup codes
            backup_codes = request.data.get('backup_codes', [])
            user.mfa_backup_codes = backup_codes
            user.mfa_enabled = True

        user.mfa_verified_at = timezone.now()
        user.save()

        # Generate new tokens with MFA verified
        refresh = RefreshToken.for_user(user)
        refresh['mfa_verified'] = True

        return Response({
            'message': 'MFA verification successful.',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class MFADisableView(APIView):
    """
    Disable MFA for the authenticated user.

    POST /api/v1/auth/mfa/disable/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Require password confirmation
        password = request.data.get('password')
        if not password or not user.check_password(password):
            return Response(
                {'error': 'Password confirmation required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.mfa_enabled = False
        user.mfa_secret = ''
        user.mfa_backup_codes = []
        user.mfa_verified_at = None
        user.save()

        return Response(
            {'message': 'MFA has been disabled.'},
            status=status.HTTP_200_OK
        )
