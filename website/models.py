from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
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


class DayOfWeek(models.IntegerChoices):
    MONDAY = 0, 'Segunda-feira'
    TUESDAY = 1, 'Terça-feira'
    WEDNESDAY = 2, 'Quarta-feira'
    THURSDAY = 3, 'Quinta-feira'
    FRIDAY = 4, 'Sexta-feira'
    SATURDAY = 5, 'Sábado'
    SUNDAY = 6, 'Domingo'


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
                has_conflict = Appointment.objects.filter(
                    dentist=self,
                    start_datetime__lt=slot_end,
                    end_datetime__gt=current,
                ).exclude(status=AppointmentStatus.CANCELED).exists()
                if not has_conflict:
                    slots.append((current, slot_end))
                current = current + slot_duration
        return slots


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


class WeeklySchedule(models.Model):
    dentist = models.ForeignKey(
        Dentist,
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


class DayOff(models.Model):
    dentist = models.ForeignKey(
        Dentist,
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


class Schedule(models.Model):
    dentist = models.ForeignKey(
        Dentist,
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


class AppointmentStatus(models.IntegerChoices):
    SCHEDULED = 1, 'Agendado'
    COMPLETED = 2, 'Concluído'
    CANCELED = 3, 'Cancelado'
    NO_SHOW = 4, 'Faltou'


class Appointment(models.Model):
    dentist = models.ForeignKey(
        Dentist,
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    procedure = models.ForeignKey(
        Procedure,
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
        return AppointmentDetails.objects.get_or_create(appointment=self)[0]


class AppointmentDetails(models.Model):
    appointment = models.OneToOneField(
        Appointment,
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


class PaymentStatus(models.IntegerChoices):
    PENDING = 1, 'Pendente'
    PAID = 2, 'Pago'
    REFUNDED = 3, 'Estornado'


class PaymentMethod(models.IntegerChoices):
    CASH = 1, 'Dinheiro'
    CREDIT_CARD = 2, 'Cartão de Crédito'
    DEBIT_CARD = 3, 'Cartão de Débito'


class Payment(models.Model):
    appointment = models.ForeignKey(
        Appointment,
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
