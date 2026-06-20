from django.db import models


class DayOff(models.Model):
    dentist = models.ForeignKey(
        'Dentist',
        on_delete=models.CASCADE,
        related_name='days_off'
    )
    date = models.DateField()
    reason = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Folga"
        verbose_name_plural = "Folgas"
        unique_together = ['dentist', 'date']
        ordering = ['date']

    def __str__(self):
        return f"{self.dentist} - {self.date}"
