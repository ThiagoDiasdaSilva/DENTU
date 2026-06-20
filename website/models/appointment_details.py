from django.db import models


class AppointmentDetails(models.Model):
    appointment = models.OneToOneField(
        'Appointment',
        on_delete=models.CASCADE,
        related_name='details'
    )
    notes = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)
    prescription = models.TextField(blank=True)

    class Meta:
        verbose_name = "Detalhes da Consulta"
        verbose_name_plural = "Detalhes das Consultas"

    def __str__(self):
        return f"Detalhes - {self.appointment}"

    def update_notes(self, notes):
        self.notes = notes
        self.save()

    def update_diagnosis(self, diagnosis):
        self.diagnosis = diagnosis
        self.save()

    def add_prescription(self, prescription):
        self.prescription = prescription
        self.save()
