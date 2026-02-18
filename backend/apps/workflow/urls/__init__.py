"""
Workflow URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.workflow.views import (
    WorkflowDefinitionViewSet,
    WorkflowInstanceViewSet,
    ApprovalRequestViewSet,
)

app_name = 'workflow'

router = DefaultRouter()
router.register('definitions', WorkflowDefinitionViewSet, basename='workflow-definition')
router.register('instances', WorkflowInstanceViewSet, basename='workflow-instance')
router.register('approval-requests', ApprovalRequestViewSet, basename='approval-request')

urlpatterns = [
    path('', include(router.urls)),
]
