"""
Digital signature serializers.
"""
from rest_framework import serializers
from apps.audit.models import SignatureMeaning, DigitalSignature, SignatureRequirement


class SignatureMeaningSerializer(serializers.ModelSerializer):
    """Serializer for signature meanings."""

    class Meta:
        model = SignatureMeaning
        fields = [
            'code',
            'name',
            'description',
            'requires_comment',
            'is_active',
        ]
        read_only_fields = ['code']


class DigitalSignatureSerializer(serializers.ModelSerializer):
    """Serializer for digital signatures (read-only)."""

    meaning_name = serializers.CharField(source='meaning.name', read_only=True)
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = DigitalSignature
        fields = [
            'id',
            'signed_at',
            'signer_email',
            'signer_full_name',
            'signer_employee_id',
            'meaning',
            'meaning_name',
            'meaning_text',
            'signer_comment',
            'record_type',
            'record_identifier',
            'data_hash',
            'signature_algorithm',
            'status',
            'is_valid',
        ]
        read_only_fields = fields

    def get_is_valid(self, obj):
        """Check if signature is cryptographically valid."""
        return obj.verify()


class SignatureCreateSerializer(serializers.Serializer):
    """Serializer for creating a digital signature."""

    meaning_code = serializers.CharField()
    comment = serializers.CharField(required=False, allow_blank=True, default='')
    password = serializers.CharField(
        write_only=True,
        help_text='User password for authentication'
    )

    def validate_meaning_code(self, value):
        """Validate signature meaning exists."""
        try:
            SignatureMeaning.objects.get(code=value, is_active=True)
        except SignatureMeaning.DoesNotExist:
            raise serializers.ValidationError('Invalid signature meaning.')
        return value

    def validate(self, data):
        """Validate the signature request."""
        user = self.context.get('user')
        if not user:
            raise serializers.ValidationError('User not found in context.')

        # Verify password
        if not user.check_password(data['password']):
            raise serializers.ValidationError({'password': 'Invalid password.'})

        # Check if user has signing capability
        if not user.digital_signature_enabled:
            raise serializers.ValidationError(
                'Digital signature is not enabled for your account.'
            )

        # Check if meaning requires comment
        meaning = SignatureMeaning.objects.get(code=data['meaning_code'])
        if meaning.requires_comment and not data.get('comment'):
            raise serializers.ValidationError({
                'comment': 'Comment is required for this signature type.'
            })

        return data


class SignatureRequirementSerializer(serializers.ModelSerializer):
    """Serializer for signature requirements."""

    meaning_name = serializers.CharField(source='required_meaning.name', read_only=True)

    class Meta:
        model = SignatureRequirement
        fields = [
            'id',
            'record_type',
            'workflow_state',
            'required_meaning',
            'meaning_name',
            'min_signatures',
            'required_role',
            'order',
            'is_active',
        ]


class SignatureStatusSerializer(serializers.Serializer):
    """Serializer for signature status on a record."""

    is_complete = serializers.BooleanField()
    total_required = serializers.IntegerField()
    total_collected = serializers.IntegerField()
    missing_requirements = serializers.ListField(child=serializers.DictField())
    signatures = DigitalSignatureSerializer(many=True)
