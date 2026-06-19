from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Dentist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    license_number = models.CharField(max_length=50, unique=True)
    specialty = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "Dentista"
        verbose_name_plural = "Dentistas"

    def __str__(self):
        return f"Dr(a). {self.user.get_full_name() or self.user.username}"

    def get_schedule(self):
        return self.schedules.all()

    def get_appointments(self):
        return self.appointments.all()

    def is_available(self, date_time):
        return self.schedules.filter(
            start_datetime__lte=date_time,
            end_datetime__gt=date_time
        ).exists()

    def generate_schedules(self, start_date, end_date):
        from website.models.schedule import Schedule

        current = start_date
        created_count = 0
        while current <= end_date:
            if self.days_off.filter(date=current).exists():
                current += timedelta(days=1)
                continue
            weekday = current.weekday()
            for weekly in self.weekly_schedules.filter(day_of_week=weekday):
                start_datetime = timezone.make_aware(
                    datetime.combine(current, weekly.start_time)
                )
                end_datetime = timezone.make_aware(
                    datetime.combine(current, weekly.end_time)
                )
                _, created = Schedule.objects.get_or_create(
                    dentist=self,
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                )
                if created:
                    created_count += 1
            current += timedelta(days=1)
        return created_count

    def regenerate_schedules(self, start_date, end_date):
        from website.models.appointment import Appointment
        from website.models.enums import AppointmentStatus

        affected = Appointment.objects.filter(
            dentist=self,
            start_datetime__date__gte=start_date,
            start_datetime__date__lte=end_date,
            status=AppointmentStatus.SCHEDULED,
        )
        for appointment in affected:
            appointment.cancel()

        self.schedules.filter(
            start_datetime__date__gte=start_date,
            start_datetime__date__lte=end_date,
        ).delete()

        return self.generate_schedules(start_date, end_date)

    def get_available_slots(self, procedure, start_date, end_date):
        from website.models.appointment import Appointment
        from website.models.enums import AppointmentStatus

        slots = []
        slot_duration = timedelta(minutes=procedure.duration_minutes)
        schedules = self.schedules.filter(
            start_datetime__date__gte=start_date,
            start_datetime__date__lte=end_date,
        ).order_by('start_datetime')
        for schedule in schedules:
            current = schedule.start_datetime
            while current + slot_duration <= schedule.end_datetime:
                slot_end = current + slot_duration
                if current <= timezone.now():
                    current = current + slot_duration
                    continue
                has_conflict = Appointment.objects.filter(
                    dentist=self,
                    start_datetime__lt=slot_end,
                    end_datetime__gt=current,
                ).exclude(status=AppointmentStatus.CANCELED).exists()
                if not has_conflict:
                    slots.append((current, slot_end))
                current = current + slot_duration
        return slots
