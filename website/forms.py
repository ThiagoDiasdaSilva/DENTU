from django import forms

from website.models import Dentist, Patient, Procedure, PaymentMethod


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


class PatientProfileForm(forms.ModelForm):
    first_name = forms.CharField(label="Nome", max_length=30, required=False)
    last_name = forms.CharField(label="Sobrenome", max_length=150, required=False)
    email = forms.EmailField(label="Email")

    class Meta:
        model = Patient
        fields = ['phone_number', 'date_of_birth', 'address']
        labels = {
            'phone_number': 'Telefone',
            'date_of_birth': 'Data de nascimento',
            'address': 'Endereço',
        }
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_id:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        patient = super().save(commit=False)
        patient.user.first_name = self.cleaned_data['first_name']
        patient.user.last_name = self.cleaned_data['last_name']
        patient.user.email = self.cleaned_data['email']
        if commit:
            patient.user.save()
            patient.save()
        return patient
