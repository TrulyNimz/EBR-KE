"""
Raw material and supplier serializers.
"""
from rest_framework import serializers
from django.utils import timezone
from modules.manufacturing.models import (
    RawMaterial,
    Supplier,
    MaterialLot,
    MaterialUsage,
)


class RawMaterialListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for material lists."""

    supplier_count = serializers.SerializerMethodField()
    lot_count = serializers.SerializerMethodField()

    class Meta:
        model = RawMaterial
        fields = [
            'id',
            'code',
            'name',
            'material_type',
            'storage_class',
            'unit_of_measure',
            'is_active',
            'requires_coa',
            'supplier_count',
            'lot_count',
        ]

    def get_supplier_count(self, obj):
        return obj.suppliers.count()

    def get_lot_count(self, obj):
        return obj.lots.filter(status='approved').count()


class RawMaterialSerializer(serializers.ModelSerializer):
    """Full raw material serializer."""

    supplier_names = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = RawMaterial
        fields = [
            'id',
            'code',
            'name',
            'description',
            'material_type',
            'cas_number',
            'specifications',
            'storage_class',
            'storage_conditions',
            'shelf_life_days',
            'reorder_point',
            'reorder_quantity',
            'unit_of_measure',
            'msds_available',
            'safety_precautions',
            'ppe_required',
            'is_active',
            'requires_coa',
            'supplier_names',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_supplier_names(self, obj):
        return list(obj.suppliers.values_list('name', flat=True))

    def validate_code(self, value):
        """Ensure code is uppercase."""
        return value.upper()

    def create(self, validated_data):
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id
        return super().create(validated_data)


class SupplierListSerializer(serializers.ModelSerializer):
    """Lightweight supplier serializer."""

    material_count = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = [
            'id',
            'code',
            'name',
            'status',
            'country',
            'quality_rating',
            'delivery_rating',
            'material_count',
        ]

    def get_material_count(self, obj):
        return obj.materials.count()


class SupplierSerializer(serializers.ModelSerializer):
    """Full supplier serializer."""

    material_codes = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = Supplier
        fields = [
            'id',
            'code',
            'name',
            'contact_name',
            'email',
            'phone',
            'address',
            'country',
            'status',
            'approved_date',
            'next_audit_date',
            'certifications',
            'quality_rating',
            'delivery_rating',
            'material_codes',
            'notes',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_material_codes(self, obj):
        return list(obj.materials.values_list('code', flat=True))

    def validate_code(self, value):
        return value.upper()

    def validate_quality_rating(self, value):
        if value is not None and (value < 0 or value > 5):
            raise serializers.ValidationError('Rating must be between 0 and 5.')
        return value

    def validate_delivery_rating(self, value):
        if value is not None and (value < 0 or value > 5):
            raise serializers.ValidationError('Rating must be between 0 and 5.')
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id
        return super().create(validated_data)


class MaterialLotListSerializer(serializers.ModelSerializer):
    """Lightweight material lot serializer."""

    material_code = serializers.CharField(source='material.code', read_only=True)
    material_name = serializers.CharField(source='material.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = MaterialLot
        fields = [
            'id',
            'internal_lot_number',
            'lot_number',
            'material_code',
            'material_name',
            'supplier_name',
            'status',
            'quantity_available',
            'unit_of_measure',
            'received_date',
            'expiry_date',
            'is_expired',
            'days_until_expiry',
        ]


class MaterialLotSerializer(serializers.ModelSerializer):
    """Full material lot serializer."""

    material_code = serializers.CharField(source='material.code', read_only=True)
    material_name = serializers.CharField(source='material.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    received_by_name = serializers.CharField(source='received_by.full_name', read_only=True)
    qc_approved_by_name = serializers.CharField(
        source='qc_approved_by.full_name',
        read_only=True,
        allow_null=True
    )
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = MaterialLot
        fields = [
            'id',
            'material',
            'material_code',
            'material_name',
            'lot_number',
            'supplier_lot_number',
            'internal_lot_number',
            'supplier',
            'supplier_name',
            'received_date',
            'received_by',
            'received_by_name',
            'purchase_order',
            'quantity_received',
            'quantity_available',
            'unit_of_measure',
            'status',
            'manufacturing_date',
            'expiry_date',
            'retest_date',
            'is_expired',
            'days_until_expiry',
            'coa_received',
            'coa_file',
            'storage_location',
            'storage_conditions',
            'qc_sample_taken',
            'qc_sample_date',
            'qc_approved_date',
            'qc_approved_by',
            'qc_approved_by_name',
            'barcode',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'internal_lot_number', 'created_at', 'updated_at',
            'received_by', 'qc_approved_by', 'qc_approved_date',
        ]


class MaterialLotCreateSerializer(serializers.ModelSerializer):
    """Serializer for receiving material lots."""

    class Meta:
        model = MaterialLot
        fields = [
            'material',
            'lot_number',
            'supplier_lot_number',
            'supplier',
            'received_date',
            'purchase_order',
            'quantity_received',
            'unit_of_measure',
            'manufacturing_date',
            'expiry_date',
            'retest_date',
            'coa_received',
            'coa_file',
            'storage_location',
            'storage_conditions',
            'notes',
        ]

    def validate(self, attrs):
        """Validate lot data."""
        # Ensure expiry date is after manufacturing date
        if attrs.get('manufacturing_date') and attrs.get('expiry_date'):
            if attrs['expiry_date'] <= attrs['manufacturing_date']:
                raise serializers.ValidationError({
                    'expiry_date': 'Expiry date must be after manufacturing date.'
                })

        # Check supplier is approved
        supplier = attrs.get('supplier')
        if supplier and supplier.status != Supplier.Status.APPROVED:
            raise serializers.ValidationError({
                'supplier': 'Supplier must be approved to receive materials.'
            })

        return attrs

    def create(self, validated_data):
        import uuid
        user = self.context['request'].user
        tenant_id = getattr(self.context['request'], 'tenant_id', '')

        validated_data['internal_lot_number'] = f"LOT-{uuid.uuid4().hex[:10].upper()}"
        validated_data['received_by'] = user
        validated_data['quantity_available'] = validated_data['quantity_received']
        validated_data['created_by'] = user
        validated_data['tenant_id'] = tenant_id

        return super().create(validated_data)


class MaterialUsageSerializer(serializers.ModelSerializer):
    """Material usage serializer."""

    lot_number = serializers.CharField(source='lot.internal_lot_number', read_only=True)
    material_name = serializers.CharField(source='lot.material.name', read_only=True)
    batch_number = serializers.CharField(source='batch.batch_number', read_only=True)
    used_by_name = serializers.CharField(source='used_by.full_name', read_only=True)
    verified_by_name = serializers.CharField(
        source='verified_by.full_name',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = MaterialUsage
        fields = [
            'id',
            'lot',
            'lot_number',
            'material_name',
            'batch',
            'batch_number',
            'batch_step',
            'quantity_used',
            'unit_of_measure',
            'used_at',
            'used_by',
            'used_by_name',
            'verified_by',
            'verified_by_name',
            'verified_at',
            'lot_barcode_scanned',
            'notes',
            'created_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'used_by', 'verified_by', 'verified_at',
        ]


class MaterialUsageCreateSerializer(serializers.ModelSerializer):
    """Serializer for recording material usage."""

    lot_barcode = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = MaterialUsage
        fields = [
            'lot',
            'batch',
            'batch_step',
            'quantity_used',
            'unit_of_measure',
            'lot_barcode',
            'notes',
        ]

    def validate(self, attrs):
        """Validate material usage."""
        lot = attrs.get('lot')

        # Check lot is approved
        if lot.status != MaterialLot.Status.APPROVED:
            raise serializers.ValidationError({
                'lot': f'Material lot is not approved for use. Status: {lot.status}'
            })

        # Check not expired
        if lot.is_expired:
            raise serializers.ValidationError({
                'lot': 'Material lot is expired.'
            })

        # Check sufficient quantity
        if lot.quantity_available < attrs['quantity_used']:
            raise serializers.ValidationError({
                'quantity_used': f'Insufficient quantity. Available: {lot.quantity_available}'
            })

        # Verify barcode if provided
        lot_barcode = attrs.pop('lot_barcode', None)
        if lot_barcode:
            if lot_barcode == lot.barcode:
                attrs['lot_barcode_scanned'] = True
            else:
                raise serializers.ValidationError({
                    'lot_barcode': 'Barcode does not match material lot.'
                })

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['used_by'] = user
        validated_data['used_at'] = timezone.now()
        validated_data['created_by'] = user
        return super().create(validated_data)
