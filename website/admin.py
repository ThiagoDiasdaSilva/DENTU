from django.contrib import admin
from .models import (
    Procedure,
    Dentist,
    Patient,
    WeeklySchedule,
    DayOff,
    Schedule,
    Appointment,
)


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


@admin.register(WeeklySchedule)
class WeeklyScheduleAdmin(admin.ModelAdmin):
    list_display = ('dentist', 'day_of_week', 'start_time', 'end_time')
    list_filter = ('dentist', 'day_of_week')
    search_fields = ('dentist__user__first_name', 'dentist__user__last_name')


@admin.register(DayOff)
class DayOffAdmin(admin.ModelAdmin):
    list_display = ('dentist', 'date', 'reason')
    list_filter = ('dentist', 'date')
    search_fields = ('dentist__user__first_name', 'dentist__user__last_name')


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('dentist', 'start_datetime', 'end_datetime')
    list_filter = ('dentist', 'start_datetime')
    search_fields = ('dentist__user__first_name', 'dentist__user__last_name')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        'dentist', 'patient', 'procedure',
        'start_datetime', 'end_datetime', 'status'
    )
    list_filter = ('status', 'dentist', 'procedure')
    search_fields = (
        'patient__user__first_name',
        'patient__user__last_name',
        'dentist__user__first_name',
        'dentist__user__last_name',
    )
