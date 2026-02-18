"""
Manufacturing module serializers.
"""
from .materials import (
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
from .equipment import (
    EquipmentSerializer,
    EquipmentListSerializer,
    CalibrationRecordSerializer,
    CalibrationRecordCreateSerializer,
    EquipmentUsageSerializer,
    EquipmentUsageCreateSerializer,
)
from .quality import (
    QCTestSerializer,
    QCTestRequestSerializer,
    QCTestRequestCreateSerializer,
    QCResultSerializer,
    QCResultCreateSerializer,
    BatchReleaseSerializer,
    BatchReleaseCreateSerializer,
)

__all__ = [
    # Materials
    'RawMaterialSerializer',
    'RawMaterialListSerializer',
    'SupplierSerializer',
    'SupplierListSerializer',
    'MaterialLotSerializer',
    'MaterialLotListSerializer',
    'MaterialLotCreateSerializer',
    'MaterialUsageSerializer',
    'MaterialUsageCreateSerializer',
    # Equipment
    'EquipmentSerializer',
    'EquipmentListSerializer',
    'CalibrationRecordSerializer',
    'CalibrationRecordCreateSerializer',
    'EquipmentUsageSerializer',
    'EquipmentUsageCreateSerializer',
    # Quality
    'QCTestSerializer',
    'QCTestRequestSerializer',
    'QCTestRequestCreateSerializer',
    'QCResultSerializer',
    'QCResultCreateSerializer',
    'BatchReleaseSerializer',
    'BatchReleaseCreateSerializer',
]
