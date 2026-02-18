"""
Healthcare module views.
"""
from .patients import PatientViewSet, PatientAllergyViewSet
from .medications import MedicationOrderViewSet, MedicationAdministrationViewSet
from .observations import VitalSignsViewSet, ClinicalNoteViewSet, AssessmentViewSet

__all__ = [
    'PatientViewSet',
    'PatientAllergyViewSet',
    'MedicationOrderViewSet',
    'MedicationAdministrationViewSet',
    'VitalSignsViewSet',
    'ClinicalNoteViewSet',
    'AssessmentViewSet',
]
