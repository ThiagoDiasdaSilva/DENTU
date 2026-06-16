from django.db import models
from django.contrib.auth.models import User


class Procedure(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Procedimento"
        verbose_name_plural = "Procedimentos"

    def __str__(self):
        return self.name

    def get_price(self):
        return self.price

    def update_price(self, new_price):
        self.price = new_price
        self.save()


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
        pass

    def get_appointments(self):
        pass

    def is_available(self, date_time):
        pass


class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    def update_phone_number(self, phone_number):
        self.phone_number = phone_number
        self.save()
