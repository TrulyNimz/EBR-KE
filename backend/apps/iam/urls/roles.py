"""
Role management URL routes.

GET    /api/v1/roles/                    - List roles
POST   /api/v1/roles/                    - Create role
GET    /api/v1/roles/{id}/               - Get role
PATCH  /api/v1/roles/{id}/               - Update role
DELETE /api/v1/roles/{id}/               - Delete role
GET    /api/v1/roles/{id}/permissions/   - Get all permissions for role
POST   /api/v1/roles/{id}/add_permission/    - Add permission to role
POST   /api/v1/roles/{id}/remove_permission/ - Remove permission from role
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.iam.views import RoleViewSet

app_name = 'roles'

router = DefaultRouter()
router.register('', RoleViewSet, basename='role')

urlpatterns = [
    path('', include(router.urls)),
]
