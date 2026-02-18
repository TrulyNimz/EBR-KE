"""
Health check endpoints for monitoring.
"""
from django.urls import path
from django.http import JsonResponse
from django.db import connection


def health_check(request):
    """Basic health check endpoint."""
    return JsonResponse({'status': 'healthy'})


def ready_check(request):
    """
    Readiness check - verifies all dependencies are available.
    """
    checks = {
        'database': False,
        'cache': False,
    }

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        checks['database'] = True
    except Exception:
        pass

    # Check cache (Redis)
    try:
        from django.core.cache import cache
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            checks['cache'] = True
    except Exception:
        pass

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return JsonResponse(
        {
            'status': 'ready' if all_healthy else 'not_ready',
            'checks': checks
        },
        status=status_code
    )


urlpatterns = [
    path('', health_check, name='health'),
    path('ready/', ready_check, name='ready'),
]
