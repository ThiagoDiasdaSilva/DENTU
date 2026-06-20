from django.db import models


class DayOfWeek(models.IntegerChoices):
    MONDAY = 0, 'Segunda-feira'
    TUESDAY = 1, 'Terça-feira'
    WEDNESDAY = 2, 'Quarta-feira'
    THURSDAY = 3, 'Quinta-feira'
    FRIDAY = 4, 'Sexta-feira'
    SATURDAY = 5, 'Sábado'
    SUNDAY = 6, 'Domingo'


class AppointmentStatus(models.IntegerChoices):
    SCHEDULED = 1, 'Agendado'
    COMPLETED = 2, 'Concluído'
    CANCELED = 3, 'Cancelado'
    NO_SHOW = 4, 'Faltou'


class PaymentStatus(models.IntegerChoices):
    PENDING = 1, 'Pendente'
    PAID = 2, 'Pago'
    REFUNDED = 3, 'Estornado'


class PaymentMethod(models.IntegerChoices):
    CASH = 1, 'Dinheiro'
    CREDIT_CARD = 2, 'Cartão de Crédito'
    DEBIT_CARD = 3, 'Cartão de Débito'
