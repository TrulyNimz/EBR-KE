"""
User management URL routes.

GET    /api/v1/users/           - List users
POST   /api/v1/users/           - Create user
GET    /api/v1/users/{id}/      - Get user
PATCH  /api/v1/users/{id}/      - Update user
DELETE /api/v1/users/{id}/      - Deactivate user
POST   /api/v1/users/{id}/lock/ - Lock user account
POST   /api/v1/users/{id}/unlock/ - Unlock user account
POST   /api/v1/users/{id}/reset_password/ - Force password reset
GET    /api/v1/users/me/        - Get current user
PATCH  /api/v1/users/me/        - Update current user
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.iam.views import UserViewSet, CurrentUserView

app_name = 'users'

router = DefaultRouter()
router.register('', UserViewSet, basename='user')

urlpatterns = [
    # Current user endpoint (must be before router to avoid conflict)
    path('me/', CurrentUserView.as_view(), name='current-user'),

    # ViewSet routes
    path('', include(router.urls)),
]
