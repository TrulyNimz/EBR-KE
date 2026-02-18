"""
API v1 URL Configuration.

All API endpoints are versioned under /api/v1/
"""
from django.urls import path, include
from apps.batch_records.views import DashboardSummaryView

app_name = 'api_v1'

urlpatterns = [
    # Dashboard
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),

    # Authentication
    path('auth/', include('apps.iam.urls.auth')),

    # IAM - Users, Roles, Permissions
    path('users/', include('apps.iam.urls.users')),
    path('roles/', include('apps.iam.urls.roles')),
    path('permissions/', include('apps.iam.urls.permissions')),
    path('user-roles/', include('apps.iam.urls.user_roles')),

    # Audit and Compliance
    path('audit/', include('apps.audit.urls')),

    # Workflow Engine
    path('workflows/', include('apps.workflow.urls')),

    # Batch Records
    path('', include('apps.batch_records.urls')),

    # Notifications
    path('notifications/', include('apps.notifications.urls')),

    # Core apps (to be enabled as implemented)
    # path('schemas/', include('apps.schema_manager.urls')),

    # Industry modules (conditionally loaded based on tenant settings)
    path('healthcare/', include('modules.healthcare.urls')),
    # path('manufacturing/', include('modules.manufacturing.urls')),
    # path('agriculture/', include('modules.agriculture.urls')),
]
