from django.core.exceptions import ValidationError
from django.db import models


class Schedule(models.Model):
    dentist = models.ForeignKey(
        'Dentist',
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()

    class Meta:
        verbose_name = "Horário de Trabalho"
        verbose_name_plural = "Horários de Trabalho"
        ordering = ['start_datetime']
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_datetime__gt=models.F('start_datetime')),
                name='end_after_start'
            )
        ]

    def clean(self):
        overlapping = Schedule.objects.filter(
            dentist=self.dentist,
            start_datetime__lt=self.end_datetime,
            end_datetime__gt=self.start_datetime
        ).exclude(pk=self.pk)
        if overlapping.exists():
            raise ValidationError(
                "Este horário de trabalho sobrepõe outro já cadastrado."
            )

    def __str__(self):
        return (
            f"{self.dentist} - "
            f"{self.start_datetime.strftime('%d/%m/%Y %H:%M')} às "
            f"{self.end_datetime.strftime('%H:%M')}"
        )

    def contains(self, start, end):
        return self.start_datetime <= start and self.end_datetime >= end
