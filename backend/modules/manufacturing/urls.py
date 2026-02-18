"""
Manufacturing module URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from modules.manufacturing.views import (
    RawMaterialViewSet,
    SupplierViewSet,
    MaterialLotViewSet,
    MaterialUsageViewSet,
    EquipmentViewSet,
    CalibrationRecordViewSet,
    EquipmentUsageViewSet,
    QCTestViewSet,
    QCTestRequestViewSet,
    QCResultViewSet,
    BatchReleaseViewSet,
)

app_name = 'manufacturing'

router = DefaultRouter()

# Materials
router.register('materials', RawMaterialViewSet, basename='material')
router.register('suppliers', SupplierViewSet, basename='supplier')
router.register('material-lots', MaterialLotViewSet, basename='material-lot')
router.register('material-usages', MaterialUsageViewSet, basename='material-usage')

# Equipment
router.register('equipment', EquipmentViewSet, basename='equipment')
router.register('calibrations', CalibrationRecordViewSet, basename='calibration')
router.register('equipment-usages', EquipmentUsageViewSet, basename='equipment-usage')

# Quality Control
router.register('qc-tests', QCTestViewSet, basename='qc-test')
router.register('qc-requests', QCTestRequestViewSet, basename='qc-request')
router.register('qc-results', QCResultViewSet, basename='qc-result')
router.register('batch-releases', BatchReleaseViewSet, basename='batch-release')

urlpatterns = [
    path('', include(router.urls)),
]
