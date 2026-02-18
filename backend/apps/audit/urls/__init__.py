"""
Audit URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.audit.views import (
    AuditLogViewSet,
    AuditIntegrityView,
    SignatureMeaningViewSet,
    DigitalSignatureViewSet,
    SignatureRequirementViewSet,
)

app_name = 'audit'

router = DefaultRouter()
router.register('logs', AuditLogViewSet, basename='audit-log')
router.register('signature-meanings', SignatureMeaningViewSet, basename='signature-meaning')
router.register('signatures', DigitalSignatureViewSet, basename='digital-signature')
router.register('signature-requirements', SignatureRequirementViewSet, basename='signature-requirement')

urlpatterns = [
    path('integrity/', AuditIntegrityView.as_view(), name='integrity'),
    path('', include(router.urls)),
]
