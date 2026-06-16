from django.contrib import admin
from .models import Procedure, Dentist, Patient


@admin.register(Procedure)
class ProcedureAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_minutes')
    search_fields = ('name',)


@admin.register(Dentist)
class DentistAdmin(admin.ModelAdmin):
    list_display = ('user', 'license_number', 'specialty', 'phone_number')
    search_fields = ('user__first_name', 'user__last_name', 'license_number')


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'date_of_birth')
    search_fields = ('user__first_name', 'user__last_name', 'phone_number')
