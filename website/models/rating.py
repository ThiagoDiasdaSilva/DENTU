from django.core.exceptions import ValidationError
from django.db import models


class AppointmentRating(models.Model):
    appointment = models.OneToOneField(
        'Appointment',
        on_delete=models.CASCADE,
        related_name='rating'
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Avaliação"
        verbose_name_plural = "Avaliações"

    def __str__(self):
        return f"{self.appointment} - {self.rating} estrelas"

    def clean(self):
        if self.rating < 1 or self.rating > 5:
            raise ValidationError("A nota deve ser entre 1 e 5.")
