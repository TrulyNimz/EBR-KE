"""
IAM URL Configuration.
"""
from django.urls import path, include

app_name = 'iam'

urlpatterns = [
    path('auth/', include('apps.iam.urls.auth')),
    path('users/', include('apps.iam.urls.users')),
    path('roles/', include('apps.iam.urls.roles')),
    path('permissions/', include('apps.iam.urls.permissions')),
    path('user-roles/', include('apps.iam.urls.user_roles')),
]
