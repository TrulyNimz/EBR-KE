"""
Management command to seed development data.

Creates:
  - A public tenant (required by django-tenants before any other data)
  - A development tenant with domain
  - A superuser / admin account
  - Basic roles and permissions
  - A sample batch template with steps

Usage:
    python manage.py seed_dev_data
    python manage.py seed_dev_data --reset   # drop and recreate tenant schema
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Seed development data: tenant, superuser, roles, sample batch template'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Drop the dev tenant schema and recreate it before seeding',
        )

    def handle(self, *args, **options):
        from apps.tenants.models import Tenant, Domain, TenantSettings

        self.stdout.write(self.style.MIGRATE_HEADING('=== EBR Seed Data ==='))

        # ------------------------------------------------------------------ #
        # 1. Public tenant (required by django-tenants as the base schema)    #
        # ------------------------------------------------------------------ #
        self.stdout.write('Creating public tenant...')
        public_tenant, created = Tenant.objects.get_or_create(
            schema_name='public',
            defaults={
                'name': 'Public',
                'slug': 'public',
                'industry': 'manufacturing',
                'contact_email': 'admin@ebr-platform.local',
                'is_active': True,
            },
        )
        if created:
            Domain.objects.get_or_create(
                domain='localhost',
                defaults={'tenant': public_tenant, 'is_primary': True},
            )
            self.stdout.write(self.style.SUCCESS('  Public tenant created'))
        else:
            self.stdout.write('  Public tenant already exists')

        # ------------------------------------------------------------------ #
        # 2. Development tenant                                                #
        # ------------------------------------------------------------------ #
        self.stdout.write('Creating development tenant...')

        dev_schema = 'dev_company'
        if options['reset']:
            try:
                existing = Tenant.objects.get(schema_name=dev_schema)
                self.stdout.write(
                    self.style.WARNING(f'  Dropping schema {dev_schema}...')
                )
                connection.set_schema_to_public()
                existing.delete()  # django-tenants drops the schema on delete
                self.stdout.write(self.style.SUCCESS('  Schema dropped'))
            except Tenant.DoesNotExist:
                pass

        dev_tenant, created = Tenant.objects.get_or_create(
            schema_name=dev_schema,
            defaults={
                'name': 'Dev Company Ltd',
                'slug': 'dev-company',
                'industry': 'manufacturing',
                'contact_name': 'Dev Admin',
                'contact_email': 'admin@dev-company.local',
                'subscription_tier': 'enterprise',
                'enabled_modules': ['batch_records', 'workflow', 'audit', 'notifications'],
                'is_active': True,
            },
        )
        if created:
            Domain.objects.get_or_create(
                domain='dev-company.localhost',
                defaults={'tenant': dev_tenant, 'is_primary': True},
            )
            # Also register 127.0.0.1 for convenience in development
            Domain.objects.get_or_create(
                domain='127.0.0.1',
                defaults={'tenant': dev_tenant, 'is_primary': False},
            )
            self.stdout.write(self.style.SUCCESS(f'  Tenant "{dev_tenant.name}" created'))
        else:
            self.stdout.write(f'  Tenant "{dev_tenant.name}" already exists')

        # Ensure tenant settings exist
        TenantSettings.objects.get_or_create(
            tenant=dev_tenant,
            defaults={
                'compliance_mode': 'GMP',
                'require_digital_signatures': False,
                'require_mfa': False,
                'password_expiry_days': 90,
                'max_login_attempts': 5,
                'allow_offline_mode': True,
            },
        )

        # ------------------------------------------------------------------ #
        # 3. Switch to dev tenant schema for remaining data                   #
        # ------------------------------------------------------------------ #
        connection.set_tenant(dev_tenant)
        self.stdout.write(f'  Active schema: {connection.schema_name}')

        # ------------------------------------------------------------------ #
        # 4. Superuser                                                         #
        # ------------------------------------------------------------------ #
        self.stdout.write('Creating superuser...')
        from apps.iam.models import User

        superuser, created = User.objects.get_or_create(
            email='admin@dev-company.local',
            defaults={
                'employee_id': 'EMP-0001',
                'first_name': 'Dev',
                'last_name': 'Admin',
                'title': 'System Administrator',
                'department': 'IT',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            },
        )
        if created:
            superuser.set_password('Admin@1234567')
            superuser.save(update_fields=['password'])
            self.stdout.write(self.style.SUCCESS(
                '  Superuser created: admin@dev-company.local / Admin@1234567'
            ))
        else:
            self.stdout.write('  Superuser already exists')

        # ------------------------------------------------------------------ #
        # 5. Roles & Permissions                                               #
        # ------------------------------------------------------------------ #
        self.stdout.write('Creating roles and permissions...')
        from apps.iam.models import Permission, Role, UserRole

        # Core permissions
        permission_defs = [
            ('batch_records.batch.view',    'Batch Records', 'batch', 'view',   'View batch records'),
            ('batch_records.batch.create',  'Batch Records', 'batch', 'create', 'Create batch records'),
            ('batch_records.batch.update',  'Batch Records', 'batch', 'update', 'Update batch records'),
            ('batch_records.batch.delete',  'Batch Records', 'batch', 'delete', 'Delete batch records'),
            ('batch_records.step.execute',  'Batch Records', 'step',  'execute','Execute batch steps'),
            ('batch_records.step.verify',   'Batch Records', 'step',  'verify', 'Verify batch steps'),
            ('workflow.definition.view',    'Workflow',      'definition', 'view',   'View workflow definitions'),
            ('workflow.definition.manage',  'Workflow',      'definition', 'manage', 'Manage workflow definitions'),
            ('workflow.instance.view',      'Workflow',      'instance',   'view',   'View workflow instances'),
            ('workflow.instance.transition','Workflow',      'instance',   'transition','Execute workflow transitions'),
            ('audit.log.view',              'Audit',         'log',    'view',   'View audit logs'),
            ('audit.signature.view',        'Audit',         'signature','view', 'View digital signatures'),
            ('iam.user.view',               'IAM',           'user',   'view',   'View users'),
            ('iam.user.manage',             'IAM',           'user',   'manage', 'Manage users'),
            ('iam.role.view',               'IAM',           'role',   'view',   'View roles'),
            ('iam.role.manage',             'IAM',           'role',   'manage', 'Manage roles'),
        ]

        permissions = {}
        for code, module, resource, action, description in permission_defs:
            perm, _ = Permission.objects.get_or_create(
                code=code,
                defaults={
                    'name': description,
                    'description': description,
                    'module': module,
                    'resource': resource,
                    'action': action,
                    'is_system': True,
                },
            )
            permissions[code] = perm

        # Roles
        admin_role, created = Role.objects.get_or_create(
            code='system-admin',
            defaults={
                'name': 'System Administrator',
                'description': 'Full system access',
                'is_system_role': True,
                'is_active': True,
            },
        )
        if created:
            admin_role.permissions.set(list(permissions.values()))
            self.stdout.write(self.style.SUCCESS('  System Administrator role created'))

        operator_role, created = Role.objects.get_or_create(
            code='batch-operator',
            defaults={
                'name': 'Batch Operator',
                'description': 'Execute and manage batch records',
                'is_system_role': True,
                'is_active': True,
            },
        )
        if created:
            operator_perms = [
                v for k, v in permissions.items()
                if k.startswith('batch_records') or k in ('audit.log.view', 'workflow.instance.view')
            ]
            operator_role.permissions.set(operator_perms)
            self.stdout.write(self.style.SUCCESS('  Batch Operator role created'))

        reviewer_role, created = Role.objects.get_or_create(
            code='batch-reviewer',
            defaults={
                'name': 'Batch Reviewer',
                'description': 'Review and verify batch records',
                'is_system_role': True,
                'is_active': True,
            },
        )
        if created:
            reviewer_perms = [
                v for k, v in permissions.items()
                if k in (
                    'batch_records.batch.view',
                    'batch_records.step.verify',
                    'audit.log.view',
                    'audit.signature.view',
                )
            ]
            reviewer_role.permissions.set(reviewer_perms)
            self.stdout.write(self.style.SUCCESS('  Batch Reviewer role created'))

        # Assign admin role to superuser
        UserRole.objects.get_or_create(
            user=superuser,
            role=admin_role,
            defaults={'assigned_by': superuser, 'reason': 'Initial seed'},
        )

        # ------------------------------------------------------------------ #
        # 6. Sample Batch Template                                             #
        # ------------------------------------------------------------------ #
        self.stdout.write('Creating sample batch template...')
        from apps.batch_records.models import BatchTemplate, BatchStepTemplate

        template, created = BatchTemplate.objects.get_or_create(
            code='SAMPLE-MFG-001',
            defaults={
                'name': 'Sample Manufacturing Batch',
                'description': 'A sample batch template for demonstration purposes',
                'version': 1,
                'status': 'active',
                'product_code': 'PROD-001',
                'product_name': 'Sample Product',
                'module_type': 'manufacturing',
                'default_quantity_unit': 'kg',
                'created_by': superuser,
            },
        )

        if created:
            steps_data = [
                {
                    'code': 'STEP-001',
                    'name': 'Raw Material Inspection',
                    'description': 'Inspect and verify all raw materials',
                    'instructions': 'Check each material against specification sheet. Record lot numbers and quantities.',
                    'sequence': 1,
                    'step_type': 'data_entry',
                    'form_schema': {
                        'type': 'object',
                        'properties': {
                            'material_lot': {
                                'type': 'string',
                                'title': 'Material Lot Number',
                            },
                            'quantity_received': {
                                'type': 'number',
                                'title': 'Quantity Received (kg)',
                                'minimum': 0,
                            },
                            'inspection_result': {
                                'type': 'string',
                                'title': 'Inspection Result',
                                'enum': ['Pass', 'Fail', 'Conditional Pass'],
                            },
                        },
                        'required': ['material_lot', 'quantity_received', 'inspection_result'],
                    },
                    'requires_verification': True,
                    'requires_signature': False,
                    'created_by': superuser,
                },
                {
                    'code': 'STEP-002',
                    'name': 'Equipment Setup & Calibration',
                    'description': 'Verify equipment calibration and setup',
                    'instructions': 'Check calibration certificates. Ensure all equipment is within calibration dates.',
                    'sequence': 2,
                    'step_type': 'verification',
                    'form_schema': {
                        'type': 'object',
                        'properties': {
                            'equipment_id': {
                                'type': 'string',
                                'title': 'Equipment ID',
                            },
                            'calibration_date': {
                                'type': 'string',
                                'title': 'Last Calibration Date',
                            },
                            'calibration_valid': {
                                'type': 'boolean',
                                'title': 'Calibration Valid',
                            },
                        },
                        'required': ['equipment_id', 'calibration_valid'],
                    },
                    'requires_verification': True,
                    'requires_signature': False,
                    'created_by': superuser,
                },
                {
                    'code': 'STEP-003',
                    'name': 'Production Execution',
                    'description': 'Execute the production process',
                    'instructions': 'Follow SOP-MFG-001. Record all process parameters.',
                    'sequence': 3,
                    'step_type': 'data_entry',
                    'form_schema': {
                        'type': 'object',
                        'properties': {
                            'temperature_c': {
                                'type': 'number',
                                'title': 'Process Temperature (°C)',
                                'minimum': 0,
                                'maximum': 300,
                            },
                            'pressure_bar': {
                                'type': 'number',
                                'title': 'Process Pressure (bar)',
                                'minimum': 0,
                            },
                            'duration_minutes': {
                                'type': 'integer',
                                'title': 'Process Duration (minutes)',
                                'minimum': 1,
                            },
                            'yield_kg': {
                                'type': 'number',
                                'title': 'Actual Yield (kg)',
                                'minimum': 0,
                            },
                        },
                        'required': ['temperature_c', 'duration_minutes', 'yield_kg'],
                    },
                    'requires_verification': False,
                    'requires_signature': False,
                    'created_by': superuser,
                },
                {
                    'code': 'STEP-004',
                    'name': 'Quality Control Check',
                    'description': 'Final QC inspection before release',
                    'instructions': 'Perform all required QC tests per QC-SOP-001. Record results.',
                    'sequence': 4,
                    'step_type': 'approval',
                    'form_schema': {
                        'type': 'object',
                        'properties': {
                            'qc_result': {
                                'type': 'string',
                                'title': 'QC Result',
                                'enum': ['Pass', 'Fail'],
                            },
                            'qc_notes': {
                                'type': 'string',
                                'title': 'QC Notes',
                            },
                        },
                        'required': ['qc_result'],
                    },
                    'requires_verification': True,
                    'requires_signature': True,
                    'signature_meaning': 'I certify this QC check has been completed in accordance with all applicable procedures.',
                    'created_by': superuser,
                },
            ]

            for step_data in steps_data:
                template_obj = template
                BatchStepTemplate.objects.create(
                    batch_template=template_obj,
                    **step_data,
                )

            self.stdout.write(self.style.SUCCESS(
                f'  Template "{template.name}" created with {len(steps_data)} steps'
            ))
        else:
            self.stdout.write(f'  Template "{template.name}" already exists')

        # ------------------------------------------------------------------ #
        # Done                                                                 #
        # ------------------------------------------------------------------ #
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== Seed complete ==='))
        self.stdout.write('')
        self.stdout.write('Login credentials:')
        self.stdout.write(self.style.WARNING('  Email:    admin@dev-company.local'))
        self.stdout.write(self.style.WARNING('  Password: Admin@1234567'))
        self.stdout.write('')
        self.stdout.write('API base URL: http://localhost:8000/api/v1/')
        self.stdout.write('API docs:     http://localhost:8000/api/docs/')
        self.stdout.write('Admin:        http://localhost:8000/admin/')
