"""
Healthcare module URL configuration.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers as nested_routers

from modules.healthcare.views import (
    PatientViewSet,
    PatientAllergyViewSet,
    MedicationOrderViewSet,
    MedicationAdministrationViewSet,
    VitalSignsViewSet,
    ClinicalNoteViewSet,
    AssessmentViewSet,
)

app_name = 'healthcare'

# Main router
router = DefaultRouter()
router.register('patients', PatientViewSet, basename='patient')
router.register('medication-orders', MedicationOrderViewSet, basename='medication-order')
router.register('medication-administrations', MedicationAdministrationViewSet, basename='medication-administration')
router.register('vital-signs', VitalSignsViewSet, basename='vital-signs')
router.register('clinical-notes', ClinicalNoteViewSet, basename='clinical-note')
router.register('assessments', AssessmentViewSet, basename='assessment')

# Nested router for patient allergies
patients_router = nested_routers.NestedDefaultRouter(router, 'patients', lookup='patient')
patients_router.register('allergies', PatientAllergyViewSet, basename='patient-allergy')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(patients_router.urls)),
]
