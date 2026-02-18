"""
Notification URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    NotificationViewSet,
    NotificationTemplateViewSet,
    UserNotificationPreferenceView,
    DeviceTokenViewSet,
    SendNotificationView,
    NotificationBatchViewSet,
    NotificationSSEView,
)

app_name = 'notifications'

router = DefaultRouter()
router.register('', NotificationViewSet, basename='notification')
router.register('templates', NotificationTemplateViewSet, basename='notification-template')
router.register('devices', DeviceTokenViewSet, basename='device-token')
router.register('batches', NotificationBatchViewSet, basename='notification-batch')

urlpatterns = [
    # Custom endpoints (before router)
    path('preferences/', UserNotificationPreferenceView.as_view(), name='preferences'),
    path('send/', SendNotificationView.as_view(), name='send'),
    path('stream/', NotificationSSEView.as_view(), name='stream'),

    # Router URLs
    path('', include(router.urls)),
]
