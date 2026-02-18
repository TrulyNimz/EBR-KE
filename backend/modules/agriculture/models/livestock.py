"""
Agriculture Livestock models.

Animal tracking, health records, and production records.
"""
import uuid
from django.db import models
from django.conf import settings
from apps.core.models import AuditableModel


class AnimalSpecies(AuditableModel):
    """
    Animal species catalog.
    """

    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    scientific_name = models.CharField(max_length=200, blank=True)

    # Production type
    production_types = models.JSONField(
        default=list,
        help_text='e.g., meat, milk, eggs, wool'
    )

    # Lifecycle information
    gestation_days = models.PositiveIntegerField(null=True, blank=True)
    maturity_age_months = models.PositiveIntegerField(null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'agriculture_animal_species'
        ordering = ['name']
        verbose_name_plural = 'Animal species'

    def __str__(self):
        return self.name


class Animal(AuditableModel):
    """
    Individual animal record.
    """

    class Sex(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        SOLD = 'sold', 'Sold'
        DECEASED = 'deceased', 'Deceased'
        CULLED = 'culled', 'Culled'
        TRANSFERRED = 'transferred', 'Transferred'

    # Identification
    tag_number = models.CharField(max_length=100, unique=True, db_index=True)
    electronic_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text='RFID or electronic ear tag'
    )
    name = models.CharField(max_length=100, blank=True)

    # Species and breed
    species = models.ForeignKey(
        AnimalSpecies,
        on_delete=models.PROTECT,
        related_name='animals'
    )
    breed = models.CharField(max_length=100, blank=True)
    sex = models.CharField(max_length=10, choices=Sex.choices)

    # Birth information
    birth_date = models.DateField(null=True, blank=True)
    birth_weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Parentage
    dam = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='offspring_dam'
    )
    sire = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='offspring_sire'
    )

    # Acquisition
    acquisition_date = models.DateField()
    acquisition_type = models.CharField(
        max_length=50,
        help_text='born, purchased, transferred'
    )
    acquisition_source = models.CharField(max_length=200, blank=True)
    acquisition_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Current status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    status_date = models.DateField(null=True, blank=True)
    status_notes = models.TextField(blank=True)

    # Location
    current_location = models.CharField(max_length=200, blank=True)
    pen_number = models.CharField(max_length=50, blank=True)

    # Physical attributes
    current_weight_kg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    last_weight_date = models.DateField(null=True, blank=True)
    color_markings = models.CharField(max_length=200, blank=True)

    # Production group
    production_group = models.CharField(
        max_length=100,
        blank=True,
        help_text='e.g., dairy herd, fattening group'
    )

    # Notes
    notes = models.TextField(blank=True)

    # Tenant
    tenant_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        db_table = 'agriculture_animals'
        ordering = ['tag_number']

    def __str__(self):
        if self.name:
            return f'{self.tag_number} - {self.name}'
        return self.tag_number

    @property
    def age_months(self):
        """Calculate age in months."""
        from datetime import date
        if self.birth_date:
            today = date.today()
            return (today.year - self.birth_date.year) * 12 + \
                   (today.month - self.birth_date.month)
        return None


class AnimalHealthRecord(AuditableModel):
    """
    Animal health/veterinary record.
    """

    class RecordType(models.TextChoices):
        VACCINATION = 'vaccination', 'Vaccination'
        TREATMENT = 'treatment', 'Treatment'
        EXAMINATION = 'examination', 'Examination'
        DEWORMING = 'deworming', 'Deworming'
        SURGERY = 'surgery', 'Surgery'
        PREGNANCY_CHECK = 'pregnancy', 'Pregnancy Check'
        OTHER = 'other', 'Other'

    # Animal reference
    animal = models.ForeignKey(
        Animal,
        on_delete=models.CASCADE,
        related_name='health_records'
    )

    # Linked batch step
    batch_step = models.ForeignKey(
        'batch_records.BatchStep',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='animal_health_records'
    )

    # Record details
    record_type = models.CharField(
        max_length=20,
        choices=RecordType.choices
    )
    record_date = models.DateField()

    # For vaccinations/treatments
    product_name = models.CharField(max_length=255, blank=True)
    product_batch = models.CharField(max_length=100, blank=True)
    dosage = models.CharField(max_length=100, blank=True)
    route = models.CharField(
        max_length=50,
        blank=True,
        help_text='e.g., IM, SC, oral'
    )
    withdrawal_period_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Meat/milk withdrawal period'
    )

    # For examinations
    diagnosis = models.CharField(max_length=255, blank=True)
    symptoms = models.TextField(blank=True)
    body_condition_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True
    )
    temperature = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text='Temperature in °C'
    )

    # Performed by
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='animal_health_records'
    )
    veterinarian = models.CharField(max_length=200, blank=True)

    # Costs
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Follow-up
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'agriculture_animal_health_records'
        ordering = ['-record_date']

    def __str__(self):
        return f'{self.animal.tag_number} - {self.record_type} - {self.record_date}'


class AnimalProductionRecord(AuditableModel):
    """
    Animal production record (milk, eggs, wool, etc.).
    """

    class ProductionType(models.TextChoices):
        MILK = 'milk', 'Milk'
        EGGS = 'eggs', 'Eggs'
        WOOL = 'wool', 'Wool'
        MEAT = 'meat', 'Meat'
        OTHER = 'other', 'Other'

    # Animal reference
    animal = models.ForeignKey(
        Animal,
        on_delete=models.CASCADE,
        related_name='production_records'
    )

    # Linked batch step
    batch_step = models.ForeignKey(
        'batch_records.BatchStep',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='animal_production_records'
    )

    # Production details
    production_type = models.CharField(
        max_length=20,
        choices=ProductionType.choices
    )
    production_date = models.DateField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20)

    # Quality
    quality_grade = models.CharField(max_length=50, blank=True)
    quality_notes = models.TextField(blank=True)

    # For milk
    fat_percentage = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )
    protein_percentage = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )
    somatic_cell_count = models.PositiveIntegerField(null=True, blank=True)

    # Recorded by
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='animal_production_records'
    )

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'agriculture_animal_production_records'
        ordering = ['-production_date']

    def __str__(self):
        return f'{self.animal.tag_number} - {self.production_type} - {self.production_date}'
