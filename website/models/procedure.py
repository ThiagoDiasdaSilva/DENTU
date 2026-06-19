from django.db import models


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
