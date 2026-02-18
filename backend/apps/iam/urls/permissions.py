"""
Permission URL routes (read-only).

GET /api/v1/permissions/      - List permissions
GET /api/v1/permissions/{id}/ - Get permission
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.iam.views import PermissionViewSet

app_name = 'permissions'

router = DefaultRouter()
router.register('', PermissionViewSet, basename='permission')

urlpatterns = [
    path('', include(router.urls)),
]
