"""
Authentication serializers for the EBR Platform.
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.utils import timezone
import pyotp

from apps.iam.models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes additional user claims.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['email'] = user.email
        token['employee_id'] = user.employee_id
        token['full_name'] = user.full_name

        # Get user roles
        roles = list(user.user_roles.filter(
            valid_from__lte=timezone.now()
        ).filter(
            models.Q(valid_until__isnull=True) |
            models.Q(valid_until__gt=timezone.now())
        ).values_list('role__code', flat=True))
        token['roles'] = roles

        # MFA status
        token['mfa_verified'] = False

        return token


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            # Try to authenticate
            user = authenticate(
                request=self.context.get('request'),
                email=email,
                password=password
            )

            if not user:
                # Check if user exists but password is wrong
                try:
                    existing_user = User.objects.get(email=email)
                    # Record failed login attempt
                    existing_user.record_failed_login()
                except User.DoesNotExist:
                    pass

                raise serializers.ValidationError(
                    'Unable to log in with provided credentials.',
                    code='authentication'
                )

            # Check if account is locked
            if user.is_locked:
                raise serializers.ValidationError(
                    'Account is locked. Please contact administrator.',
                    code='account_locked'
                )

            # Check if account is active
            if not user.is_active:
                raise serializers.ValidationError(
                    'Account is inactive.',
                    code='account_inactive'
                )

            # Check if password has expired
            if user.is_password_expired:
                raise serializers.ValidationError(
                    'Password has expired. Please reset your password.',
                    code='password_expired'
                )

        else:
            raise serializers.ValidationError(
                'Must include "email" and "password".',
                code='invalid_credentials'
            )

        attrs['user'] = user
        return attrs


class TokenRefreshSerializer(serializers.Serializer):
    """
    Serializer for token refresh.
    """
    refresh = serializers.CharField()


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change.
    """
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=12)
    confirm_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'New passwords do not match.'
            })

        # Check password history (prevent reuse)
        user = self.context['request'].user
        for old_hash in user.password_history[-5:]:  # Check last 5 passwords
            if user.check_password(attrs['new_password']):
                raise serializers.ValidationError({
                    'new_password': 'Cannot reuse recent passwords.'
                })

        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for password reset request.
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            User.objects.get(email=value, is_active=True)
        except User.DoesNotExist:
            # Don't reveal if user exists
            pass
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for password reset confirmation.
    Expects uid (base64-encoded user pk) and token from the reset email.
    """
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=12)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        return attrs


class MFASetupSerializer(serializers.Serializer):
    """
    Serializer for MFA setup response.
    """
    secret = serializers.CharField(read_only=True)
    qr_uri = serializers.CharField(read_only=True)
    backup_codes = serializers.ListField(
        child=serializers.CharField(),
        read_only=True
    )


class MFAVerifySerializer(serializers.Serializer):
    """
    Serializer for MFA verification.
    """
    code = serializers.CharField(max_length=6, min_length=6)

    def validate_code(self, value):
        user = self.context['request'].user

        if not user.mfa_secret:
            raise serializers.ValidationError('MFA is not set up.')

        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(value, valid_window=1):
            # Check backup codes
            if value in user.mfa_backup_codes:
                # Remove used backup code
                user.mfa_backup_codes.remove(value)
                user.save(update_fields=['mfa_backup_codes'])
            else:
                raise serializers.ValidationError('Invalid verification code.')

        return value
