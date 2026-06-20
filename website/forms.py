from django import forms

from website.models import Dentist, Procedure, PaymentMethod


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
    payment_method = forms.ChoiceField(
        choices=[('', 'Selecione uma forma de pagamento')] + list(PaymentMethod.choices),
        label="Forma de pagamento",
    )

    def clean_payment_method(self):
        value = self.cleaned_data.get('payment_method')
        if not value:
            raise forms.ValidationError("Selecione uma forma de pagamento.")
        return int(value)
