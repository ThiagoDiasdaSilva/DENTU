from datetime import date, datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User
from website.models import (
    Procedure,
    Dentist,
    Patient,
    WeeklySchedule,
    DayOff,
    DayOfWeek,
    Schedule,
    Appointment,
    AppointmentStatus,
)


class ModelTests(TestCase):
    @staticmethod
    def _create_dentist(username, first_name, license_number):
        user = User.objects.create_user(
            username=username, first_name=first_name, password="123"
        )
        return Dentist.objects.create(user=user, license_number=license_number)

    @staticmethod
    def _create_patient(username, first_name, phone):
        user = User.objects.create_user(
            username=username, first_name=first_name, password="123"
        )
        return Patient.objects.create(user=user, phone_number=phone)

    @staticmethod
    def _create_procedure(name, duration):
        return Procedure.objects.create(
            name=name, price=100.00, duration_minutes=duration
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
            username="drjoao", first_name="João", password="123"
        )
        dentist = Dentist.objects.create(
            user=user, license_number="12345", specialty="Ortodontia"
        )
        self.assertEqual(str(dentist), "Dr(a). João")

    def test_create_patient(self):
        user = User.objects.create_user(
            username="maria", first_name="Maria", password="123"
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
        created = dentist.generate_schedules(date(2026, 7, 13), date(2026, 7, 13))
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
        DayOff.objects.create(dentist=dentist, date=date(2026, 7, 13), reason="Folga")
        created = dentist.generate_schedules(date(2026, 7, 13), date(2026, 7, 13))
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
        created = dentist.generate_schedules(date(2026, 7, 13), date(2026, 7, 13))
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
        self.assertEqual(new_sched.start_datetime.hour, 14)

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
