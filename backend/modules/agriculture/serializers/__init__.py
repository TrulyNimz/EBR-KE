"""
Agriculture module serializers.
"""
from .crops import (
    CropSerializer,
    CropListSerializer,
    FieldSerializer,
    FieldListSerializer,
    CropBatchSerializer,
    CropBatchListSerializer,
    CropBatchCreateSerializer,
    FarmInputSerializer,
    FarmInputCreateSerializer,
)
from .livestock import (
    AnimalSpeciesSerializer,
    AnimalSerializer,
    AnimalListSerializer,
    AnimalCreateSerializer,
    AnimalHealthRecordSerializer,
    AnimalHealthRecordCreateSerializer,
    AnimalProductionRecordSerializer,
    AnimalProductionRecordCreateSerializer,
)
from .traceability import (
    TraceabilityRecordSerializer,
    TraceabilityRecordCreateSerializer,
    CertificationRecordSerializer,
    CertificationRecordCreateSerializer,
)

__all__ = [
    # Crops
    'CropSerializer',
    'CropListSerializer',
    'FieldSerializer',
    'FieldListSerializer',
    'CropBatchSerializer',
    'CropBatchListSerializer',
    'CropBatchCreateSerializer',
    'FarmInputSerializer',
    'FarmInputCreateSerializer',
    # Livestock
    'AnimalSpeciesSerializer',
    'AnimalSerializer',
    'AnimalListSerializer',
    'AnimalCreateSerializer',
    'AnimalHealthRecordSerializer',
    'AnimalHealthRecordCreateSerializer',
    'AnimalProductionRecordSerializer',
    'AnimalProductionRecordCreateSerializer',
    # Traceability
    'TraceabilityRecordSerializer',
    'TraceabilityRecordCreateSerializer',
    'CertificationRecordSerializer',
    'CertificationRecordCreateSerializer',
]
