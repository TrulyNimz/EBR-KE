"""
Agriculture Crop models.

Crop management, planting records, and harvest tracking
with full traceability.
"""
import uuid
from django.db import models
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from apps.core.models import AuditableModel


class Crop(AuditableModel):
    """
    Crop type/variety catalog.
    """

    class CropType(models.TextChoices):
        CEREAL = 'cereal', 'Cereal'
        LEGUME = 'legume', 'Legume'
        VEGETABLE = 'vegetable', 'Vegetable'
        FRUIT = 'fruit', 'Fruit'
        ROOT = 'root', 'Root/Tuber'
        OIL_SEED = 'oil_seed', 'Oil Seed'
        FIBER = 'fiber', 'Fiber'
        FODDER = 'fodder', 'Fodder'
        OTHER = 'other', 'Other'

    # Identification
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    scientific_name = models.CharField(max_length=255, blank=True)
    variety = models.CharField(max_length=100, blank=True)

    # Classification
    crop_type = models.CharField(
        max_length=20,
        choices=CropType.choices,
        default=CropType.OTHER
    )

    # Growing information
    growing_season = models.CharField(max_length=100, blank=True)
    days_to_maturity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Average days from planting to harvest'
    )
    optimal_temperature_min = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text='Minimum temperature (°C)'
    )
    optimal_temperature_max = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text='Maximum temperature (°C)'
    )
    water_requirements = models.CharField(max_length=200, blank=True)
    soil_requirements = models.TextField(blank=True)

    # Yield expectations
    expected_yield_per_hectare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    yield_unit = models.CharField(max_length=20, default='kg')

    # Certifications applicable
    organic_certified = models.BooleanField(default=False)
    fair_trade_eligible = models.BooleanField(default=False)

    # Status
    is_active = models.BooleanField(default=True)

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'agriculture_crops'
        ordering = ['name']

    def __str__(self):
        if self.variety:
            return f'{self.name} - {self.variety}'
        return self.name


class Field(AuditableModel):
    """
    Agricultural field/plot.
    """

    class SoilType(models.TextChoices):
        CLAY = 'clay', 'Clay'
        SANDY = 'sandy', 'Sandy'
        LOAMY = 'loamy', 'Loamy'
        SILTY = 'silty', 'Silty'
        PEATY = 'peaty', 'Peaty'
        CHALKY = 'chalky', 'Chalky'
        MIXED = 'mixed', 'Mixed'

    class IrrigationType(models.TextChoices):
        NONE = 'none', 'Rain-fed'
        DRIP = 'drip', 'Drip Irrigation'
        SPRINKLER = 'sprinkler', 'Sprinkler'
        FLOOD = 'flood', 'Flood Irrigation'
        CENTER_PIVOT = 'center_pivot', 'Center Pivot'
        FURROW = 'furrow', 'Furrow'

    # Identification
    field_code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)

    # Location
    location_description = models.TextField(blank=True)
    # GPS boundaries (using PostGIS)
    # boundary = gis_models.PolygonField(null=True, blank=True)
    # center_point = gis_models.PointField(null=True, blank=True)
    # For non-GIS installations, store as JSON
    boundary_coordinates = models.JSONField(
        default=list,
        help_text='List of [lat, lon] coordinates defining field boundary'
    )
    center_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    center_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    # Size
    area_hectares = models.DecimalField(max_digits=10, decimal_places=4)
    arable_area_hectares = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True
    )

    # Soil information
    soil_type = models.CharField(
        max_length=20,
        choices=SoilType.choices,
        default=SoilType.MIXED
    )
    soil_ph = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True
    )
    last_soil_test = models.DateField(null=True, blank=True)

    # Irrigation
    irrigation_type = models.CharField(
        max_length=20,
        choices=IrrigationType.choices,
        default=IrrigationType.NONE
    )
    water_source = models.CharField(max_length=200, blank=True)

    # Certifications
    organic_certified = models.BooleanField(default=False)
    organic_certification_date = models.DateField(null=True, blank=True)
    organic_certificate_number = models.CharField(max_length=100, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    current_status = models.CharField(
        max_length=50,
        default='fallow',
        help_text='fallow, planted, growing, ready_for_harvest'
    )

    # Notes
    notes = models.TextField(blank=True)

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'agriculture_fields'
        ordering = ['name']

    def __str__(self):
        return f'{self.field_code} - {self.name}'


class CropBatch(AuditableModel):
    """
    A batch/lot of crops from planting to harvest.

    Provides full traceability from seed to sale.
    """

    class Status(models.TextChoices):
        PLANNED = 'planned', 'Planned'
        PLANTED = 'planted', 'Planted'
        GROWING = 'growing', 'Growing'
        READY_FOR_HARVEST = 'ready', 'Ready for Harvest'
        HARVESTING = 'harvesting', 'Harvesting'
        HARVESTED = 'harvested', 'Harvested'
        POST_HARVEST = 'post_harvest', 'Post-Harvest Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    # Batch identification
    batch_number = models.CharField(max_length=100, unique=True, db_index=True)

    # Crop and field
    crop = models.ForeignKey(
        Crop,
        on_delete=models.PROTECT,
        related_name='batches'
    )
    field = models.ForeignKey(
        Field,
        on_delete=models.PROTECT,
        related_name='crop_batches'
    )

    # Linked EBR batch
    ebr_batch = models.OneToOneField(
        'batch_records.Batch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='crop_batch'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED
    )

    # Seed information
    seed_lot_number = models.CharField(max_length=100, blank=True)
    seed_supplier = models.CharField(max_length=200, blank=True)
    seed_quantity_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Planting
    planned_planting_date = models.DateField(null=True, blank=True)
    actual_planting_date = models.DateField(null=True, blank=True)
    planting_method = models.CharField(max_length=100, blank=True)
    planted_area_hectares = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True
    )

    # Growing period
    expected_harvest_date = models.DateField(null=True, blank=True)

    # Harvest
    actual_harvest_start = models.DateField(null=True, blank=True)
    actual_harvest_end = models.DateField(null=True, blank=True)
    harvest_quantity = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    harvest_unit = models.CharField(max_length=20, default='kg')
    yield_per_hectare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Quality grading
    quality_grade = models.CharField(max_length=50, blank=True)
    moisture_content = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Percentage'
    )

    # Storage
    storage_location = models.CharField(max_length=200, blank=True)
    storage_conditions = models.CharField(max_length=200, blank=True)

    # Weather data during growing
    weather_summary = models.JSONField(
        default=dict,
        help_text='Summary of weather conditions during growing period'
    )

    # Notes
    notes = models.TextField(blank=True)

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'agriculture_crop_batches'
        ordering = ['-actual_planting_date', '-created_at']

    def __str__(self):
        return f'{self.batch_number} - {self.crop.name}'


class FarmInput(AuditableModel):
    """
    Farm input application record (fertilizer, pesticide, etc.).
    """

    class InputType(models.TextChoices):
        FERTILIZER = 'fertilizer', 'Fertilizer'
        PESTICIDE = 'pesticide', 'Pesticide'
        HERBICIDE = 'herbicide', 'Herbicide'
        FUNGICIDE = 'fungicide', 'Fungicide'
        SEED_TREATMENT = 'seed_treatment', 'Seed Treatment'
        GROWTH_REGULATOR = 'growth_regulator', 'Growth Regulator'
        ORGANIC_AMENDMENT = 'organic_amendment', 'Organic Amendment'
        OTHER = 'other', 'Other'

    # Reference
    crop_batch = models.ForeignKey(
        CropBatch,
        on_delete=models.CASCADE,
        related_name='inputs'
    )
    batch_step = models.ForeignKey(
        'batch_records.BatchStep',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='farm_inputs'
    )

    # Input details
    input_type = models.CharField(
        max_length=20,
        choices=InputType.choices
    )
    product_name = models.CharField(max_length=255)
    product_code = models.CharField(max_length=100, blank=True)
    active_ingredient = models.CharField(max_length=255, blank=True)

    # Application details
    application_date = models.DateField()
    application_method = models.CharField(max_length=100, blank=True)
    quantity_applied = models.DecimalField(max_digits=10, decimal_places=4)
    quantity_unit = models.CharField(max_length=20)
    application_rate = models.CharField(
        max_length=100,
        blank=True,
        help_text='e.g., 200 kg/hectare'
    )
    area_treated_hectares = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True
    )

    # Applicator
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='farm_input_applications'
    )

    # Safety
    pre_harvest_interval_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Days to wait before harvest'
    )
    re_entry_interval_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Hours before field re-entry'
    )

    # Weather at application
    weather_conditions = models.JSONField(
        default=dict,
        help_text='Weather conditions at time of application'
    )

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'agriculture_farm_inputs'
        ordering = ['-application_date']

    def __str__(self):
        return f'{self.crop_batch.batch_number} - {self.product_name}'
