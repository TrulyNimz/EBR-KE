"""
Dashboard summary view — aggregates key metrics for the EBR platform.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta

from apps.batch_records.models import Batch, BatchTemplate
from apps.iam.permissions import RBACPermission


class DashboardSummaryView(APIView):
    """
    GET /api/v1/dashboard/summary/

    Returns aggregated metrics for the current tenant's dashboard:
    - Batch counts by status
    - Activity over last 30 days
    - Pending approvals
    - Recent batches
    - Template count
    """
    permission_classes = [IsAuthenticated, RBACPermission]

    def get(self, request):
        tenant_id = getattr(request, 'tenant_id', '')
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)

        base_qs = Batch.objects.filter(tenant_id=tenant_id, is_deleted=False)

        # ------------------------------------------------------------------ #
        # Batch status counts
        # ------------------------------------------------------------------ #
        status_counts = (
            base_qs
            .values('status')
            .annotate(count=Count('id'))
        )
        counts_by_status = {row['status']: row['count'] for row in status_counts}

        total = sum(counts_by_status.values())
        active = counts_by_status.get('in_progress', 0)
        pending_review = counts_by_status.get('pending_review', 0) + counts_by_status.get('pending_approval', 0)
        completed_total = counts_by_status.get('completed', 0)
        draft_count = counts_by_status.get('draft', 0)

        # ------------------------------------------------------------------ #
        # 30-day window metrics
        # ------------------------------------------------------------------ #
        created_last_30d = base_qs.filter(created_at__gte=thirty_days_ago).count()
        completed_last_30d = base_qs.filter(
            status='completed',
            actual_end__gte=thirty_days_ago
        ).count()

        # ------------------------------------------------------------------ #
        # Recent activity (last 7 days)
        # ------------------------------------------------------------------ #
        recent_batches = (
            base_qs
            .filter(created_at__gte=seven_days_ago)
            .select_related('created_by')
            .order_by('-created_at')[:5]
        )

        recent_activity = [
            {
                'id': str(b.id),
                'batch_number': b.batch_number,
                'name': b.name,
                'status': b.status,
                'product_code': b.product_code,
                'created_at': b.created_at.isoformat(),
                'created_by_name': b.created_by.get_full_name() if b.created_by else '',
            }
            for b in recent_batches
        ]

        # ------------------------------------------------------------------ #
        # Batches due soon (scheduled_start within next 7 days)
        # ------------------------------------------------------------------ #
        upcoming = (
            base_qs
            .filter(
                status='draft',
                scheduled_start__gte=now,
                scheduled_start__lte=now + timedelta(days=7),
            )
            .order_by('scheduled_start')[:5]
        )

        upcoming_batches = [
            {
                'id': str(b.id),
                'batch_number': b.batch_number,
                'name': b.name,
                'product_code': b.product_code,
                'scheduled_start': b.scheduled_start.isoformat() if b.scheduled_start else None,
            }
            for b in upcoming
        ]

        # ------------------------------------------------------------------ #
        # Templates
        # ------------------------------------------------------------------ #
        active_templates = BatchTemplate.objects.filter(
            tenant_id=tenant_id,
            is_deleted=False,
            status='active'
        ).count()

        # ------------------------------------------------------------------ #
        # Pending approvals for this user
        # ------------------------------------------------------------------ #
        from apps.workflow.models import ApprovalRequest
        from apps.iam.models import UserRole

        # Collect currently-valid role codes for this user
        user_role_codes = list(
            UserRole.objects.filter(user=request.user)
            .filter(
                Q(valid_until__isnull=True) | Q(valid_until__gt=now)
            )
            .values_list('role__code', flat=True)
        )

        # Direct-user + role-based approval filter
        # approver_roles is a JSONField list of role code strings
        approval_q = Q(approval_rule__approver_users=request.user)
        for code in user_role_codes:
            approval_q |= Q(approval_rule__approver_roles__contains=[code])

        pending_approvals = ApprovalRequest.objects.filter(
            status='pending',
            instance__tenant_id=tenant_id,
        ).filter(approval_q).distinct().count()

        return Response({
            'batches': {
                'total': total,
                'active': active,
                'pending_review': pending_review,
                'completed': completed_total,
                'draft': draft_count,
                'cancelled': counts_by_status.get('cancelled', 0),
            },
            'activity': {
                'created_last_30_days': created_last_30d,
                'completed_last_30_days': completed_last_30d,
            },
            'recent_batches': recent_activity,
            'upcoming_batches': upcoming_batches,
            'pending_approvals': pending_approvals,
            'active_templates': active_templates,
        })
