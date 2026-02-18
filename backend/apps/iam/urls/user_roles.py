"""
User-Role assignment URL routes.

GET    /api/v1/user-roles/      - List assignments
POST   /api/v1/user-roles/      - Create assignment
GET    /api/v1/user-roles/{id}/ - Get assignment
DELETE /api/v1/user-roles/{id}/ - Remove assignment
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.iam.views import UserRoleViewSet

app_name = 'user_roles'

router = DefaultRouter()
router.register('', UserRoleViewSet, basename='user-role')

urlpatterns = [
    path('', include(router.urls)),
]
