from django.core.exceptions import ValidationError
from django.db import models

from website.models.enums import DayOfWeek


class WeeklySchedule(models.Model):
    dentist = models.ForeignKey(
        'Dentist',
        on_delete=models.CASCADE,
        related_name='weekly_schedules'
    )
    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        verbose_name = "Horário Semanal"
        verbose_name_plural = "Horários Semanais"
        unique_together = ['dentist', 'day_of_week', 'start_time', 'end_time']
        ordering = ['day_of_week', 'start_time']

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError(
                "O horário de término deve ser posterior ao início."
            )

    def __str__(self):
        return (
            f"{self.dentist} - {self.get_day_of_week_display()} "
            f"{self.start_time.strftime('%H:%M')} às "
            f"{self.end_time.strftime('%H:%M')}"
        )
