"""
Raw material and supplier views.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Sum, Q

from modules.manufacturing.models import (
    RawMaterial,
    Supplier,
    MaterialLot,
    MaterialUsage,
)
from modules.manufacturing.serializers import (
    RawMaterialSerializer,
    RawMaterialListSerializer,
    SupplierSerializer,
    SupplierListSerializer,
    MaterialLotSerializer,
    MaterialLotListSerializer,
    MaterialLotCreateSerializer,
    MaterialUsageSerializer,
    MaterialUsageCreateSerializer,
)
from apps.iam.permissions import RBACPermission
from apps.audit.middleware import AuditContextMixin


class RawMaterialViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Raw Materials."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'manufacturing.material.read'
    filterset_fields = ['material_type', 'storage_class', 'is_active']
    search_fields = ['code', 'name', 'cas_number']
    ordering = ['name']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return RawMaterial.objects.filter(tenant_id=tenant_id)

    def get_serializer_class(self):
        if self.action == 'list':
            return RawMaterialListSerializer
        return RawMaterialSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'manufacturing.material.create',
            'update': 'manufacturing.material.update',
            'partial_update': 'manufacturing.material.update',
            'destroy': 'manufacturing.material.delete',
        }
        self.required_permission = permission_map.get(self.action, 'manufacturing.material.read')
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get materials below reorder point."""
        queryset = self.get_queryset().filter(
            is_active=True,
            reorder_point__isnull=False
        )

        low_stock = []
        for material in queryset:
            available = MaterialLot.objects.filter(
                material=material,
                status=MaterialLot.Status.APPROVED
            ).aggregate(total=Sum('quantity_available'))['total'] or 0

            if available <= material.reorder_point:
                low_stock.append({
                    'material': RawMaterialListSerializer(material).data,
                    'available_quantity': available,
                    'reorder_point': material.reorder_point,
                    'reorder_quantity': material.reorder_quantity,
                })

        return Response(low_stock)


class SupplierViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Suppliers."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'manufacturing.supplier.read'
    filterset_fields = ['status', 'country']
    search_fields = ['code', 'name', 'contact_name']
    ordering = ['name']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return Supplier.objects.filter(tenant_id=tenant_id)

    def get_serializer_class(self):
        if self.action == 'list':
            return SupplierListSerializer
        return SupplierSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'manufacturing.supplier.create',
            'update': 'manufacturing.supplier.update',
            'partial_update': 'manufacturing.supplier.update',
            'destroy': 'manufacturing.supplier.delete',
            'approve': 'manufacturing.supplier.approve',
        }
        self.required_permission = permission_map.get(self.action, 'manufacturing.supplier.read')
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a supplier."""
        supplier = self.get_object()

        if supplier.status == Supplier.Status.APPROVED:
            return Response(
                {'error': 'Supplier is already approved.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        supplier.status = Supplier.Status.APPROVED
        supplier.approved_date = timezone.now().date()
        supplier.modified_by = request.user
        supplier.save()

        return Response({
            'message': f'Supplier {supplier.name} approved.',
            'supplier': SupplierSerializer(supplier).data
        })

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspend a supplier."""
        supplier = self.get_object()
        reason = request.data.get('reason', '')

        supplier.status = Supplier.Status.SUSPENDED
        supplier.notes = f"Suspended: {reason}\n\n{supplier.notes}"
        supplier.modified_by = request.user
        supplier.save()

        return Response({
            'message': f'Supplier {supplier.name} suspended.',
            'supplier': SupplierSerializer(supplier).data
        })


class MaterialLotViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Material Lots."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'manufacturing.lot.read'
    filterset_fields = ['material', 'supplier', 'status']
    search_fields = ['lot_number', 'internal_lot_number', 'supplier_lot_number', 'barcode']
    ordering = ['-received_date']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return MaterialLot.objects.filter(
            tenant_id=tenant_id
        ).select_related('material', 'supplier', 'received_by', 'qc_approved_by')

    def get_serializer_class(self):
        if self.action == 'list':
            return MaterialLotListSerializer
        if self.action == 'create':
            return MaterialLotCreateSerializer
        return MaterialLotSerializer

    def get_permissions(self):
        permission_map = {
            'create': 'manufacturing.lot.receive',
            'approve': 'manufacturing.lot.approve',
            'reject': 'manufacturing.lot.reject',
        }
        self.required_permission = permission_map.get(self.action, 'manufacturing.lot.read')
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a material lot after QC."""
        lot = self.get_object()

        if lot.status != MaterialLot.Status.PENDING_QC:
            return Response(
                {'error': f'Lot cannot be approved. Current status: {lot.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        lot.status = MaterialLot.Status.APPROVED
        lot.qc_approved_by = request.user
        lot.qc_approved_date = timezone.now()
        lot.modified_by = request.user
        lot.save()

        return Response({
            'message': f'Lot {lot.internal_lot_number} approved.',
            'lot': MaterialLotSerializer(lot).data
        })

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a material lot."""
        lot = self.get_object()
        reason = request.data.get('reason', '')

        if not reason:
            return Response(
                {'error': 'Rejection reason required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        lot.status = MaterialLot.Status.REJECTED
        lot.notes = f"Rejected: {reason}\n\n{lot.notes}"
        lot.modified_by = request.user
        lot.save()

        return Response({
            'message': f'Lot {lot.internal_lot_number} rejected.',
            'lot': MaterialLotSerializer(lot).data
        })

    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get lots expiring within specified days."""
        days = int(request.query_params.get('days', 30))
        cutoff = timezone.now().date() + timezone.timedelta(days=days)

        lots = self.get_queryset().filter(
            status=MaterialLot.Status.APPROVED,
            expiry_date__lte=cutoff,
            expiry_date__gte=timezone.now().date()
        ).order_by('expiry_date')

        serializer = MaterialLotListSerializer(lots, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def scan(self, request):
        """Look up lot by barcode scan."""
        barcode = request.query_params.get('barcode')
        if not barcode:
            return Response(
                {'error': 'Barcode parameter required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lot = self.get_queryset().get(
                Q(barcode=barcode) | Q(internal_lot_number=barcode)
            )
            return Response(MaterialLotSerializer(lot).data)
        except MaterialLot.DoesNotExist:
            return Response(
                {'error': 'Lot not found.'},
                status=status.HTTP_404_NOT_FOUND
            )


class MaterialUsageViewSet(AuditContextMixin, viewsets.ModelViewSet):
    """ViewSet for Material Usage records."""

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permission = 'manufacturing.usage.read'
    http_method_names = ['get', 'post', 'head', 'options']
    filterset_fields = ['lot', 'batch', 'used_by']
    ordering = ['-used_at']

    def get_queryset(self):
        tenant_id = getattr(self.request, 'tenant_id', '')
        return MaterialUsage.objects.filter(
            lot__tenant_id=tenant_id
        ).select_related('lot', 'lot__material', 'batch', 'used_by', 'verified_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return MaterialUsageCreateSerializer
        return MaterialUsageSerializer

    def get_permissions(self):
        if self.action == 'create':
            self.required_permission = 'manufacturing.usage.create'
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify material usage record."""
        usage = self.get_object()

        if usage.verified_by:
            return Response(
                {'error': 'Usage already verified.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if usage.used_by == request.user:
            return Response(
                {'error': 'Cannot verify your own usage record.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        usage.verified_by = request.user
        usage.verified_at = timezone.now()
        usage.save()

        return Response({
            'message': 'Usage verified.',
            'usage': MaterialUsageSerializer(usage).data
        })
