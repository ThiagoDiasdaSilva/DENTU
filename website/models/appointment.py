from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models

from website.models.enums import AppointmentStatus


class Appointment(models.Model):
    dentist = models.ForeignKey(
        'Dentist',
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    patient = models.ForeignKey(
        'Patient',
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    procedure = models.ForeignKey(
        'Procedure',
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    status = models.IntegerField(
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.SCHEDULED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Consulta"
        verbose_name_plural = "Consultas"
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.procedure} - {self.dentist} / {self.patient} "
            f"({self.get_status_display()})"
        )

    @property
    def duration_minutes(self):
        return int(
            (self.end_datetime - self.start_datetime).total_seconds() // 60
        )

    def clean(self):
        if self.start_datetime is None or self.end_datetime is None:
            return
        if self.end_datetime <= self.start_datetime:
            raise ValidationError(
                "O horário de término deve ser posterior ao início."
            )

        if not self.dentist.schedules.filter(
            start_datetime__lte=self.start_datetime,
            end_datetime__gte=self.end_datetime
        ).exists():
            raise ValidationError(
                "A consulta deve estar dentro de um horário de trabalho do dentista."
            )

        overlapping = Appointment.objects.filter(
            dentist=self.dentist,
            start_datetime__lt=self.end_datetime,
            end_datetime__gt=self.start_datetime
        ).exclude(pk=self.pk)
        if overlapping.exists():
            raise ValidationError(
                "Este horário conflita com outra consulta do mesmo dentista."
            )

    def cancel(self):
        if self.status == AppointmentStatus.COMPLETED:
            raise ValidationError(
                "Não é possível cancelar uma consulta já concluída."
            )
        self.status = AppointmentStatus.CANCELED
        self.save()

    def complete(self):
        if self.status == AppointmentStatus.CANCELED:
            raise ValidationError(
                "Não é possível concluir uma consulta cancelada."
            )
        self.status = AppointmentStatus.COMPLETED
        self.save()

    def is_scheduled(self):
        return self.status == AppointmentStatus.SCHEDULED

    def is_canceled(self):
        return self.status == AppointmentStatus.CANCELED

    def reschedule(self, new_start_datetime):
        if self.status in (
            AppointmentStatus.COMPLETED,
            AppointmentStatus.CANCELED,
        ):
            raise ValidationError(
                "Não é possível remarcar uma consulta concluída ou cancelada."
            )
        self.start_datetime = new_start_datetime
        self.end_datetime = new_start_datetime + timedelta(
            minutes=self.procedure.duration_minutes
        )
        self.save()

    def get_or_create_details(self):
        from website.models.appointment_details import AppointmentDetails
        return AppointmentDetails.objects.get_or_create(appointment=self)[0]
