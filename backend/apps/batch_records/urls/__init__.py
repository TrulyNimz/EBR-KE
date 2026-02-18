"""
Batch Records URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers as nested_routers

from apps.batch_records.views import (
    BatchViewSet,
    BatchTemplateViewSet,
    BatchStepViewSet,
    BatchAttachmentViewSet,
)

app_name = 'batch_records'

# Main router
router = DefaultRouter()
router.register('batches', BatchViewSet, basename='batch')
router.register('templates', BatchTemplateViewSet, basename='batch-template')

# Nested routers for batch-related resources
batch_router = nested_routers.NestedDefaultRouter(router, 'batches', lookup='batch')
batch_router.register('steps', BatchStepViewSet, basename='batch-step')
batch_router.register('attachments', BatchAttachmentViewSet, basename='batch-attachment')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(batch_router.urls)),
]
