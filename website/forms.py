from django import forms
from django.utils import timezone

from website.models import Dentist, Procedure


class AppointmentForm(forms.Form):
    dentist = forms.ModelChoiceField(
        queryset=Dentist.objects.all(),
        label="Dentista",
        empty_label="Selecione um dentista",
    )
    procedure = forms.ModelChoiceField(
        queryset=Procedure.objects.all(),
        label="Procedimento",
        empty_label="Selecione um procedimento",
    )
    start_datetime = forms.DateTimeField(
        label="Horário",
        input_formats=['%Y-%m-%d %H:%M:%S'],
    )
