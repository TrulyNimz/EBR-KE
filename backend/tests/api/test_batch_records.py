"""
Integration tests for the Batch Records API.

Covers: list, create, get, update, start, complete, steps.
"""
import pytest

BATCH_BASE = '/api/v1/batches'
TEMPLATE_BASE = '/api/v1/templates'


def make_batch_payload(**overrides):
    """Return minimal valid batch creation payload."""
    data = {
        'batch_number': f'BATCH-{__import__("uuid").uuid4().hex[:8].upper()}',
        'name': 'Test Batch',
        'product_code': 'TEST-001',
        'product_name': 'Test Product',
        'planned_quantity': 100,
        'quantity_unit': 'units',
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
class TestBatchList:
    """GET /api/v1/batches/"""

    def test_admin_can_list_batches(self, admin_client, tenant):
        resp = admin_client.get(f'{BATCH_BASE}/')
        assert resp.status_code == 200
        data = resp.json()
        assert 'results' in data
        assert 'count' in data

    def test_unauthenticated_returns_401(self, api_client, tenant):
        resp = api_client.get(f'{BATCH_BASE}/')
        assert resp.status_code == 401

    def test_filter_by_status(self, admin_client, tenant):
        resp = admin_client.get(f'{BATCH_BASE}/?status=draft')
        assert resp.status_code == 200
        for batch in resp.json()['results']:
            assert batch['status'] == 'draft'


@pytest.mark.django_db
class TestBatchCreate:
    """POST /api/v1/batches/"""

    def test_admin_can_create_batch(self, admin_client, tenant):
        resp = admin_client.post(f'{BATCH_BASE}/', make_batch_payload())
        assert resp.status_code == 201
        data = resp.json()
        assert data['status'] == 'draft'
        assert data['product_code'] == 'TEST-001'

    def test_duplicate_batch_number_returns_400(self, admin_client, tenant):
        payload = make_batch_payload(batch_number='DUP-001')
        admin_client.post(f'{BATCH_BASE}/', payload)  # first create
        resp = admin_client.post(f'{BATCH_BASE}/', payload)  # duplicate
        assert resp.status_code == 400

    def test_missing_required_fields_returns_400(self, admin_client, tenant):
        resp = admin_client.post(f'{BATCH_BASE}/', {})
        assert resp.status_code == 400


@pytest.mark.django_db
class TestBatchDetail:
    """GET /api/v1/batches/{id}/"""

    def test_get_batch_returns_steps(self, admin_client, tenant):
        # Create batch first
        payload = make_batch_payload()
        create_resp = admin_client.post(f'{BATCH_BASE}/', payload)
        assert create_resp.status_code == 201
        batch_id = create_resp.json()['id']

        # Get detail
        resp = admin_client.get(f'{BATCH_BASE}/{batch_id}/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['id'] == batch_id
        assert 'steps' in data
        assert isinstance(data['steps'], list)

    def test_nonexistent_batch_returns_404(self, admin_client, tenant):
        import uuid
        resp = admin_client.get(f'{BATCH_BASE}/{uuid.uuid4()}/')
        assert resp.status_code == 404


@pytest.mark.django_db
class TestBatchUpdate:
    """PATCH /api/v1/batches/{id}/"""

    def test_admin_can_update_draft_batch(self, admin_client, tenant):
        create_resp = admin_client.post(f'{BATCH_BASE}/', make_batch_payload())
        batch_id = create_resp.json()['id']

        resp = admin_client.patch(
            f'{BATCH_BASE}/{batch_id}/',
            {'name': 'Updated Name'},
        )
        assert resp.status_code == 200
        assert resp.json()['name'] == 'Updated Name'


@pytest.mark.django_db
class TestBatchLifecycle:
    """POST /api/v1/batches/{id}/start/ and /complete/"""

    def test_start_moves_batch_to_in_progress(self, admin_client, tenant):
        create_resp = admin_client.post(f'{BATCH_BASE}/', make_batch_payload())
        batch_id = create_resp.json()['id']

        resp = admin_client.post(f'{BATCH_BASE}/{batch_id}/start/')
        assert resp.status_code == 200
        assert resp.json()['status'] == 'in_progress'

    def test_cannot_start_already_started_batch(self, admin_client, tenant):
        create_resp = admin_client.post(f'{BATCH_BASE}/', make_batch_payload())
        batch_id = create_resp.json()['id']

        admin_client.post(f'{BATCH_BASE}/{batch_id}/start/')  # first start
        resp = admin_client.post(f'{BATCH_BASE}/{batch_id}/start/')  # second start
        assert resp.status_code == 400

    def test_complete_in_progress_batch(self, admin_client, tenant):
        create_resp = admin_client.post(f'{BATCH_BASE}/', make_batch_payload())
        batch_id = create_resp.json()['id']

        admin_client.post(f'{BATCH_BASE}/{batch_id}/start/')
        resp = admin_client.post(f'{BATCH_BASE}/{batch_id}/complete/')
        assert resp.status_code == 200
        assert resp.json()['status'] == 'completed'


@pytest.mark.django_db
class TestBatchSoftDelete:
    """DELETE /api/v1/batches/{id}/ (soft delete)"""

    def test_delete_soft_removes_batch(self, admin_client, tenant):
        create_resp = admin_client.post(f'{BATCH_BASE}/', make_batch_payload())
        batch_id = create_resp.json()['id']

        delete_resp = admin_client.delete(f'{BATCH_BASE}/{batch_id}/')
        assert delete_resp.status_code == 204

        # Should no longer appear in list
        list_resp = admin_client.get(f'{BATCH_BASE}/')
        ids = [b['id'] for b in list_resp.json()['results']]
        assert batch_id not in ids


@pytest.mark.django_db
class TestBatchTemplate:
    """GET /api/v1/batch-templates/"""

    def test_admin_can_list_templates(self, admin_client, tenant):
        resp = admin_client.get(f'{TEMPLATE_BASE}/')
        assert resp.status_code == 200
        assert 'results' in resp.json()


@pytest.mark.django_db
class TestDashboardSummary:
    """GET /api/v1/dashboard/summary/"""

    def test_summary_returns_expected_shape(self, admin_client, tenant):
        resp = admin_client.get('/api/v1/dashboard/summary/')
        assert resp.status_code == 200
        data = resp.json()

        assert 'batches' in data
        assert 'activity' in data
        assert 'recent_batches' in data
        assert 'upcoming_batches' in data
        assert 'pending_approvals' in data
        assert 'active_templates' in data

        batches = data['batches']
        assert 'total' in batches
        assert 'active' in batches
        assert 'pending_review' in batches
