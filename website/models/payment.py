from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from website.models.enums import PaymentMethod, PaymentStatus


class Payment(models.Model):
    appointment = models.ForeignKey(
        'Appointment',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(null=True, blank=True)
    method = models.IntegerField(
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH
    )
    status = models.IntegerField(
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Pagamento"
        verbose_name_plural = "Pagamentos"

    def __str__(self):
        return (
            f"{self.get_status_display()} - "
            f"R$ {self.amount} ({self.get_method_display()})"
        )

    def clean(self):
        if self.status == PaymentStatus.REFUNDED:
            return
        existing_total = self.appointment.payments.exclude(
            pk=self.pk
        ).exclude(
            status=PaymentStatus.REFUNDED
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        if existing_total + self.amount > self.appointment.procedure.price:
            raise ValidationError(
                "A soma dos pagamentos não pode ultrapassar "
                "o valor do procedimento."
            )

    def mark_as_paid(self):
        self.status = PaymentStatus.PAID
        if not self.payment_date:
            self.payment_date = timezone.now()
        self.save()

    def mark_as_refunded(self):
        self.status = PaymentStatus.REFUNDED
        self.save()

    def is_paid(self):
        return self.status == PaymentStatus.PAID
