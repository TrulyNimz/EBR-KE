"""
Healthcare module serializers.
"""
from .patients import (
    PatientSerializer,
    PatientListSerializer,
    PatientCreateSerializer,
    PatientAllergySerializer,
)
from .medications import (
    MedicationOrderSerializer,
    MedicationOrderCreateSerializer,
    MedicationAdministrationSerializer,
    MedicationAdministrationCreateSerializer,
    FiveRightsVerificationSerializer,
)
from .observations import (
    VitalSignsSerializer,
    VitalSignsCreateSerializer,
    ClinicalNoteSerializer,
    ClinicalNoteCreateSerializer,
    AssessmentSerializer,
)

__all__ = [
    # Patients
    'PatientSerializer',
    'PatientListSerializer',
    'PatientCreateSerializer',
    'PatientAllergySerializer',
    # Medications
    'MedicationOrderSerializer',
    'MedicationOrderCreateSerializer',
    'MedicationAdministrationSerializer',
    'MedicationAdministrationCreateSerializer',
    'FiveRightsVerificationSerializer',
    # Observations
    'VitalSignsSerializer',
    'VitalSignsCreateSerializer',
    'ClinicalNoteSerializer',
    'ClinicalNoteCreateSerializer',
    'AssessmentSerializer',
]
