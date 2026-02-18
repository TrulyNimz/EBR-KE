"""
Agriculture module URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from modules.agriculture.views import (
    CropViewSet,
    FieldViewSet,
    CropBatchViewSet,
    FarmInputViewSet,
    AnimalSpeciesViewSet,
    AnimalViewSet,
    AnimalHealthRecordViewSet,
    AnimalProductionRecordViewSet,
    TraceabilityRecordViewSet,
    CertificationRecordViewSet,
)

app_name = 'agriculture'

router = DefaultRouter()

# Crops
router.register('crops', CropViewSet, basename='crop')
router.register('fields', FieldViewSet, basename='field')
router.register('crop-batches', CropBatchViewSet, basename='crop-batch')
router.register('farm-inputs', FarmInputViewSet, basename='farm-input')

# Livestock
router.register('species', AnimalSpeciesViewSet, basename='species')
router.register('animals', AnimalViewSet, basename='animal')
router.register('health-records', AnimalHealthRecordViewSet, basename='health-record')
router.register('production-records', AnimalProductionRecordViewSet, basename='production-record')

# Traceability
router.register('traceability', TraceabilityRecordViewSet, basename='traceability')
router.register('certifications', CertificationRecordViewSet, basename='certification')

urlpatterns = [
    path('', include(router.urls)),
]
