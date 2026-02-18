"""
Integration tests for the Workflow Engine API.

Covers: list workflow definitions, activate/deprecate.
"""
import pytest

BASE = '/api/v1/workflows/definitions'


@pytest.mark.django_db
class TestWorkflowList:
    """GET /api/v1/workflows/"""

    def test_admin_can_list_workflows(self, admin_client, tenant):
        resp = admin_client.get(f'{BASE}/')
        assert resp.status_code == 200
        assert 'results' in resp.json()

    def test_unauthenticated_returns_401(self, api_client, tenant):
        resp = api_client.get(f'{BASE}/')
        assert resp.status_code == 401


@pytest.mark.django_db
class TestWorkflowCreate:
    """POST /api/v1/workflows/"""

    def _make_payload(self):
        return {
            'code': f'WF-TEST-{__import__("uuid").uuid4().hex[:6].upper()}',
            'name': 'Test Workflow',
            'description': 'A test workflow definition',
            'applicable_record_types': ['batch'],
        }

    def test_admin_can_create_workflow(self, admin_client, tenant):
        resp = admin_client.post(f'{BASE}/', self._make_payload(), format='json')
        assert resp.status_code == 201
        data = resp.json()
        assert data['status'] == 'draft'

    def test_missing_name_returns_400(self, admin_client, tenant):
        resp = admin_client.post(f'{BASE}/', {'code': 'WF-NO-NAME'}, format='json')
        assert resp.status_code == 400


@pytest.mark.django_db
class TestWorkflowActivate:
    """POST /api/v1/workflows/{id}/activate/"""

    def test_admin_can_activate_draft_workflow(self, admin_client, tenant):
        # Create a draft workflow
        payload = {
            'code': f'WF-ACT-{__import__("uuid").uuid4().hex[:6].upper()}',
            'name': 'Activatable Workflow',
            'applicable_record_types': [],
        }
        create_resp = admin_client.post(f'{BASE}/', payload, format='json')
        assert create_resp.status_code == 201
        workflow_id = create_resp.json()['id']

        resp = admin_client.post(f'{BASE}/{workflow_id}/activate/')
        assert resp.status_code == 200
        assert resp.json()['status'] == 'active'

    def test_cannot_activate_already_active_workflow(self, admin_client, tenant):
        payload = {
            'code': f'WF-ACT2-{__import__("uuid").uuid4().hex[:6].upper()}',
            'name': 'Already Active',
            'applicable_record_types': [],
        }
        create_resp = admin_client.post(f'{BASE}/', payload, format='json')
        workflow_id = create_resp.json()['id']
        admin_client.post(f'{BASE}/{workflow_id}/activate/')  # activate once

        resp = admin_client.post(f'{BASE}/{workflow_id}/activate/')  # try again
        assert resp.status_code == 400


@pytest.mark.django_db
class TestApprovalRequests:
    """GET /api/v1/approval-requests/pending/"""

    def test_pending_approvals_returns_list(self, admin_client, tenant):
        resp = admin_client.get('/api/v1/workflows/approval-requests/pending/')
        assert resp.status_code == 200
