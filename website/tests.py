from django.test import TestCase
from django.contrib.auth.models import User
from website.models import Procedure, Dentist, Patient


class ModelTests(TestCase):
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
