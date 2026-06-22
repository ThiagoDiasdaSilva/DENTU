
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import json
import os
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User

from website.models import (
    Dentist, Patient, Procedure, Schedule, WeeklySchedule, DayOff,
    Appointment, AppointmentDetails, Payment, DayOfWeek, AppointmentStatus,
    PaymentMethod, PaymentStatus
)

class ModelTests(TestCase):
    @staticmethod
    def _create_dentist(username, first_name, license_number):
        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            password=os.getenv("DJANGO_TEST_PASSWORD", "test123")
        )
        return Dentist.objects.create(user=user, license_number=license_number)

    @staticmethod
    def _create_patient(username, first_name, phone):
        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            password=os.getenv("DJANGO_TEST_PASSWORD", "test123")
        )
        return Patient.objects.create(user=user, phone_number=phone)

    @staticmethod
    def _create_procedure(name, duration, price=Decimal('100.00')):
        return Procedure.objects.create(
            name=name, price=price, duration_minutes=duration
        )

    @staticmethod
    def _create_schedule(dentist, start_hour, end_hour, day=10):
        return Schedule.objects.create(
            dentist=dentist,
            start_datetime=timezone.make_aware(
                datetime(2026, 7, day, start_hour, 0)
            ),
            end_datetime=timezone.make_aware(
                datetime(2026, 7, day, end_hour, 0)
            ),
        )

    def test_create_procedure(self):
        proc = Procedure.objects.create(
            name="Limpeza", price=150.00, duration_minutes=45
        )
        self.assertEqual(str(proc), "Limpeza")

    def test_create_dentist(self):
        user = User.objects.create_user(
            username="drjoao",
            first_name="João",
            password=os.getenv("DJANGO_TEST_PASSWORD", "test123")
        )
        dentist = Dentist.objects.create(
            user=user, license_number="12345", specialty="Ortodontia"
        )
        self.assertEqual(str(dentist), "Dr(a). João")

    def test_create_patient(self):
        user = User.objects.create_user(
            username="maria",
            first_name="Maria",
            password=os.getenv("DJANGO_TEST_PASSWORD", "test123")
        )
        patient = Patient.objects.create(
            user=user, phone_number="11999999999"
        )
        self.assertEqual(str(patient), "Maria")

    # --- Schedule / janela de trabalho ---

    def test_create_schedule(self):
        dentist = self._create_dentist("drana", "Ana", "54321")
        schedule = self._create_schedule(dentist, 9, 18)
        self.assertIn("09:00 às 18:00", str(schedule))
        self.assertTrue(
            dentist.is_available(
                timezone.make_aware(datetime(2026, 7, 10, 13, 0))
            )
        )

    def test_overlapping_schedule(self):
        dentist = self._create_dentist("drpedro", "Pedro", "99999")
        self._create_schedule(dentist, 9, 14)
        overlapping = Schedule(
            dentist=dentist,
            start_datetime=timezone.make_aware(datetime(2026, 7, 10, 13, 0)),
            end_datetime=timezone.make_aware(datetime(2026, 7, 10, 16, 0)),
        )
        with self.assertRaises(ValidationError):
            overlapping.clean()

    # --- WeeklySchedule e DayOff ---

    def test_create_weekly_schedule(self):
        dentist = self._create_dentist("drhelena", "Helena", "11111")
        weekly = WeeklySchedule.objects.create(
            dentist=dentist,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        self.assertIn("Segunda-feira", str(weekly))

    def test_weekly_schedule_invalid_time(self):
        dentist = self._create_dentist("drhelena2", "Helena", "11112")
        weekly = WeeklySchedule(
            dentist=dentist,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(14, 0),
            end_time=time(9, 0),
        )
        with self.assertRaises(ValidationError):
            weekly.clean()

    def test_generate_schedules(self):
        dentist = self._create_dentist("drhelena3", "Helena", "11113")
        WeeklySchedule.objects.create(
            dentist=dentist,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        WeeklySchedule.objects.create(
            dentist=dentist,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(13, 0),
            end_time=time(18, 0),
        )
        # 2026-07-13 is a Monday
        created = dentist.generate_schedules(
            date(2026, 7, 13), date(2026, 7, 13))
        self.assertEqual(created, 2)
        self.assertEqual(dentist.schedules.count(), 2)

    def test_generate_schedules_skip_day_off(self):
        dentist = self._create_dentist("drhelena4", "Helena", "11114")
        WeeklySchedule.objects.create(
            dentist=dentist,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(18, 0),
        )
        # 2026-07-13 is a Monday
        DayOff.objects.create(dentist=dentist, date=date(
            2026, 7, 13), reason="Folga")
        created = dentist.generate_schedules(
            date(2026, 7, 13), date(2026, 7, 13))
        self.assertEqual(created, 0)
        self.assertEqual(dentist.schedules.count(), 0)

    def test_generate_schedules_idempotent(self):
        dentist = self._create_dentist("drhelena5", "Helena", "11115")
        WeeklySchedule.objects.create(
            dentist=dentist,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(18, 0),
        )
        # 2026-07-13 is a Monday
        dentist.generate_schedules(date(2026, 7, 13), date(2026, 7, 13))
        created = dentist.generate_schedules(
            date(2026, 7, 13), date(2026, 7, 13))
        self.assertEqual(created, 0)
        self.assertEqual(dentist.schedules.count(), 1)

    # --- Appointment ---

    def test_create_appointment(self):
        dentist = self._create_dentist("drmarcos", "Marcos", "77777")
        patient = self._create_patient("carla", "Carla", "11988888888")
        procedure = self._create_procedure("Limpeza", 45)
        self._create_schedule(dentist, 9, 18)
        appointment = Appointment.objects.create(
            dentist=dentist,
            patient=patient,
            procedure=procedure,
            start_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 0)),
            end_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 45)),
        )
        self.assertEqual(appointment.status, AppointmentStatus.SCHEDULED)
        self.assertEqual(appointment.duration_minutes, 45)

    def test_appointment_outside_schedule(self):
        dentist = self._create_dentist("drjoao", "João", "11111")
        patient = self._create_patient("maria", "Maria", "11999999999")
        procedure = self._create_procedure("Consulta", 30)
        self._create_schedule(dentist, 9, 12)
        appointment = Appointment(
            dentist=dentist,
            patient=patient,
            procedure=procedure,
            start_datetime=timezone.make_aware(datetime(2026, 7, 10, 14, 0)),
            end_datetime=timezone.make_aware(datetime(2026, 7, 10, 14, 30)),
        )
        with self.assertRaises(ValidationError):
            appointment.clean()

    def test_overlapping_appointments(self):
        dentist = self._create_dentist("drana2", "Ana", "54322")
        patient1 = self._create_patient("p1", "Paciente1", "11111111111")
        patient2 = self._create_patient("p2", "Paciente2", "22222222222")
        procedure = self._create_procedure("Consulta", 30)
        self._create_schedule(dentist, 9, 18)
        Appointment.objects.create(
            dentist=dentist,
            patient=patient1,
            procedure=procedure,
            start_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 0)),
            end_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 30)),
        )
        overlapping = Appointment(
            dentist=dentist,
            patient=patient2,
            procedure=procedure,
            start_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 15)),
            end_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 45)),
        )
        with self.assertRaises(ValidationError):
            overlapping.clean()

    def test_cancel_and_complete_appointment(self):
        dentist = self._create_dentist("drana3", "Ana", "54323")
        patient = self._create_patient("p3", "Paciente3", "33333333333")
        procedure = self._create_procedure("Consulta", 30)
        self._create_schedule(dentist, 9, 18)
        appointment = Appointment.objects.create(
            dentist=dentist,
            patient=patient,
            procedure=procedure,
            start_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 0)),
            end_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 30)),
        )
        appointment.cancel()
        self.assertTrue(appointment.is_canceled())

        with self.assertRaises(ValidationError):
            appointment.complete()

    def test_reschedule_appointment(self):
        dentist = self._create_dentist("drana4", "Ana", "54324")
        patient = self._create_patient("p4", "Paciente4", "44444444444")
        procedure = self._create_procedure("Consulta", 30)
        self._create_schedule(dentist, 9, 18)
        appointment = Appointment.objects.create(
            dentist=dentist,
            patient=patient,
            procedure=procedure,
            start_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 0)),
            end_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 30)),
        )
        new_start = timezone.make_aware(datetime(2026, 7, 10, 11, 0))
        appointment.reschedule(new_start)
        self.assertEqual(appointment.start_datetime, new_start)
        self.assertEqual(
            appointment.end_datetime,
            new_start + timedelta(minutes=procedure.duration_minutes)
        )

    # --- regenerate_schedules ---

    def test_regenerate_schedules_cancels_appointments(self):
        dentist = self._create_dentist("drjoao2", "João", "22222")
        patient = self._create_patient("maria2", "Maria", "12345678901")
        procedure = self._create_procedure("Limpeza", 45)
        # Weekly pattern: Monday 9-12
        WeeklySchedule.objects.create(
            dentist=dentist,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        # 2026-07-13 is a Monday
        dentist.generate_schedules(date(2026, 7, 13), date(2026, 7, 13))
        sched = dentist.schedules.first()
        appointment = Appointment.objects.create(
            dentist=dentist,
            patient=patient,
            procedure=procedure,
            start_datetime=sched.start_datetime,
            end_datetime=sched.start_datetime + timedelta(minutes=45),
        )
        # Change pattern: now Monday 14-17
        dentist.weekly_schedules.all().delete()
        WeeklySchedule.objects.create(
            dentist=dentist,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(14, 0),
            end_time=time(17, 0),
        )
        dentist.regenerate_schedules(date(2026, 7, 13), date(2026, 7, 13))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, AppointmentStatus.CANCELED)
        self.assertEqual(dentist.schedules.count(), 1)
        new_sched = dentist.schedules.first()
        self.assertEqual(timezone.localtime(new_sched.start_datetime).hour, 14)

    def test_regenerate_schedules_does_not_cancel_completed(self):
        dentist = self._create_dentist("drjoao3", "João", "22223")
        patient = self._create_patient("maria3", "Maria", "12345678902")
        procedure = self._create_procedure("Limpeza", 45)
        WeeklySchedule.objects.create(
            dentist=dentist,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        dentist.generate_schedules(date(2026, 7, 13), date(2026, 7, 13))
        sched = dentist.schedules.first()
        appointment = Appointment.objects.create(
            dentist=dentist,
            patient=patient,
            procedure=procedure,
            start_datetime=sched.start_datetime,
            end_datetime=sched.start_datetime + timedelta(minutes=45),
            status=AppointmentStatus.COMPLETED,
        )
        dentist.weekly_schedules.all().delete()
        dentist.regenerate_schedules(date(2026, 7, 13), date(2026, 7, 13))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, AppointmentStatus.COMPLETED)

    # --- AppointmentDetails ---

    def test_get_or_create_details(self):
        dentist = self._create_dentist("drluis", "Luís", "33333")
        patient = self._create_patient("paula", "Paula", "55555555555")
        procedure = self._create_procedure("Limpeza", 45)
        self._create_schedule(dentist, 9, 18)
        appointment = Appointment.objects.create(
            dentist=dentist,
            patient=patient,
            procedure=procedure,
            start_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 0)),
            end_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 45)),
        )
        details = appointment.get_or_create_details()
        self.assertIsInstance(details, AppointmentDetails)
        self.assertEqual(details.appointment, appointment)

    def test_update_details(self):
        dentist = self._create_dentist("drluis2", "Luís", "33334")
        patient = self._create_patient("paula2", "Paula", "55555555556")
        procedure = self._create_procedure("Limpeza", 45)
        self._create_schedule(dentist, 9, 18)
        appointment = Appointment.objects.create(
            dentist=dentist,
            patient=patient,
            procedure=procedure,
            start_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 0)),
            end_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 45)),
        )
        details = appointment.get_or_create_details()
        details.update_notes("Paciente sem queixas.")
        details.update_diagnosis("Saudável.")
        details.add_prescription("Nenhuma.")
        details.refresh_from_db()
        self.assertEqual(details.notes, "Paciente sem queixas.")
        self.assertEqual(details.diagnosis, "Saudável.")
        self.assertEqual(details.prescription, "Nenhuma.")

    # --- Payment ---

    def test_create_payment(self):
        dentist = self._create_dentist("drluis3", "Luís", "33335")
        patient = self._create_patient("paula3", "Paula", "55555555557")
        procedure = self._create_procedure("Limpeza", 45, Decimal('150.00'))
        self._create_schedule(dentist, 9, 18)
        appointment = Appointment.objects.create(
            dentist=dentist,
            patient=patient,
            procedure=procedure,
            start_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 0)),
            end_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 45)),
        )
        payment = Payment.objects.create(
            appointment=appointment,
            amount=Decimal('150.00'),
            method=PaymentMethod.CASH,
        )
        self.assertEqual(payment.status, PaymentStatus.PENDING)

    def test_payment_exceeds_limit(self):
        dentist = self._create_dentist("drluis5", "Luís", "33337")
        patient = self._create_patient("paula5", "Paula", "55555555559")
        procedure = self._create_procedure("Limpeza", 45, Decimal('150.00'))
        self._create_schedule(dentist, 9, 18)
        appointment = Appointment.objects.create(
            dentist=dentist,
            patient=patient,
            procedure=procedure,
            start_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 0)),
            end_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 45)),
        )
        payment = Payment(
            appointment=appointment, amount=Decimal('200.00'), method=PaymentMethod.CASH,
        )
        with self.assertRaises(ValidationError):
            payment.clean()

    def test_payment_mark_as_paid(self):
        dentist = self._create_dentist("drluis6", "Luís", "33338")
        patient = self._create_patient("paula6", "Paula", "55555555560")
        procedure = self._create_procedure("Limpeza", 45, Decimal('150.00'))
        self._create_schedule(dentist, 9, 18)
        appointment = Appointment.objects.create(
            dentist=dentist,
            patient=patient,
            procedure=procedure,
            start_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 0)),
            end_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 45)),
        )
        payment = Payment.objects.create(
            appointment=appointment, amount=Decimal('150.00'), method=PaymentMethod.CASH,
        )
        payment.mark_as_paid()
        self.assertEqual(payment.status, PaymentStatus.PAID)
        self.assertIsNotNone(payment.payment_date)

    def test_payment_mark_as_refunded(self):
        dentist = self._create_dentist("drluis7", "Luís", "33339")
        patient = self._create_patient("paula7", "Paula", "55555555561")
        procedure = self._create_procedure("Limpeza", 45, Decimal('150.00'))
        self._create_schedule(dentist, 9, 18)
        appointment = Appointment.objects.create(
            dentist=dentist,
            patient=patient,
            procedure=procedure,
            start_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 0)),
            end_datetime=timezone.make_aware(datetime(2026, 7, 10, 10, 45)),
        )
        payment = Payment.objects.create(
            appointment=appointment, amount=Decimal('150.00'), method=PaymentMethod.CASH,
            status=PaymentStatus.PAID,
        )
        payment.mark_as_refunded()
        self.assertEqual(payment.status, PaymentStatus.REFUNDED)

    # --- get_available_slots ---

    def test_get_available_slots(self):
        dentist = self._create_dentist("drclara", "Clara", "66661")
        procedure = self._create_procedure("Limpeza", 45)
        WeeklySchedule.objects.create(
            dentist=dentist,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(8, 0),
            end_time=time(12, 0),
        )
        # 2026-07-13 is a Monday
        dentist.generate_schedules(date(2026, 7, 13), date(2026, 7, 13))
        slots = dentist.get_available_slots(
            procedure, date(2026, 7, 13), date(2026, 7, 13)
        )
        # 4h window / 45 min slots = 5 slots (8:00, 8:45, 9:30, 10:15, 11:00)
        self.assertEqual(len(slots), 5)
        self.assertEqual(timezone.localtime(slots[0][0]).hour, 8)
        self.assertEqual(timezone.localtime(slots[-1][0]).hour, 11)

    def test_get_available_slots_excludes_booked(self):
        dentist = self._create_dentist("drclara2", "Clara", "66662")
        patient = self._create_patient("p_slots", "Paciente", "00000000000")
        procedure = self._create_procedure("Limpeza", 45)
        WeeklySchedule.objects.create(
            dentist=dentist,
            day_of_week=DayOfWeek.MONDAY,
            start_time=time(8, 0),
            end_time=time(10, 0),
        )
        # 2026-07-13 is a Monday
        dentist.generate_schedules(date(2026, 7, 13), date(2026, 7, 13))
        # Book the 8:00 - 8:45 slot
        sched = dentist.schedules.first()
        Appointment.objects.create(
            dentist=dentist,
            patient=patient,
            procedure=procedure,
            start_datetime=sched.start_datetime,
            end_datetime=sched.start_datetime + timedelta(minutes=45),
        )
        slots = dentist.get_available_slots(
            procedure, date(2026, 7, 13), date(2026, 7, 13)
        )
        # 2h window = 2 slots (8:00, 8:45) minus booked slot = 1
        self.assertEqual(len(slots), 1)
        self.assertEqual(timezone.localtime(slots[0][0]).hour, 8)
        self.assertEqual(slots[0][0].minute, 45)

    def test_available_slots_endpoint(self):
        dentist = self._create_dentist("drclara3", "Clara", "66663")
        procedure = self._create_procedure("Limpeza", 45)
        tomorrow = date.today() + timedelta(days=1)
        sched_start = timezone.make_aware(
            datetime(tomorrow.year, tomorrow.month, tomorrow.day, 8, 0))
        sched_end = timezone.make_aware(
            datetime(tomorrow.year, tomorrow.month, tomorrow.day, 12, 0))
        Schedule.objects.create(
            dentist=dentist, start_datetime=sched_start, end_datetime=sched_end)
        resp = self.client.get('/appointment/slots/', {
            'dentist': dentist.id,
            'procedure': procedure.id,
        })
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn('slots', data)
        self.assertEqual(len(data['slots']), 5)
        self.assertIn('value', data['slots'][0])
        self.assertIn('label', data['slots'][0])

    def test_payment_created_on_appointment(self):
        dentist = self._create_dentist("drpag", "Pagar", "88888")
        patient = self._create_patient("pagante", "Pagante", "55555555555")
        procedure = self._create_procedure("Limpeza", 45)
        tomorrow = date.today() + timedelta(days=1)
        sched_start = timezone.make_aware(datetime(tomorrow.year, tomorrow.month, tomorrow.day, 8, 0))
        sched_end = timezone.make_aware(datetime(tomorrow.year, tomorrow.month, tomorrow.day, 12, 0))
        Schedule.objects.create(dentist=dentist, start_datetime=sched_start, end_datetime=sched_end)
        self.client.login(username="pagante", password=os.getenv("DJANGO_TEST_PASSWORD", "test123"))
        resp = self.client.get("/appointment/slots/", {"dentist": dentist.id, "procedure": procedure.id})
        data = json.loads(resp.content)
        slot_value = data["slots"][0]["value"]
        resp = self.client.post("/appointment/", {
            "dentist": dentist.id,
            "procedure": procedure.id,
            "start_datetime": slot_value,
            "payment_method": PaymentMethod.CASH,
        })
        self.assertEqual(resp.status_code, 302)
        payment = Payment.objects.get(appointment__patient=patient)
        self.assertEqual(payment.amount, procedure.price)
        self.assertEqual(payment.method, PaymentMethod.CASH)
        self.assertEqual(payment.status, PaymentStatus.PENDING)

    def test_past_slots_excluded(self):
        dentist = self._create_dentist("drpassado", "Passado", "88887")
        procedure = self._create_procedure("Limpeza", 45)
        # 2026-07-13 is a Monday, schedule 08:00-12:00
        self._create_schedule(dentist, 8, 12, day=13)
        with patch('website.models.dentist.timezone.now') as mock_now:
            mock_now.return_value = timezone.make_aware(
                datetime(2026, 7, 13, 10, 0))
            slots = dentist.get_available_slots(
                procedure, date(2026, 7, 13), date(2026, 7, 13)
            )
        # "now" is 10:00; slots at 08:00, 08:45, 09:30 are past (excluded)
        # Should only get 10:15 and 11:00
        self.assertEqual(len(slots), 2)
        for slot_start, slot_end in slots:
            self.assertGreater(slot_start, timezone.make_aware(
                datetime(2026, 7, 13, 10, 0)))
