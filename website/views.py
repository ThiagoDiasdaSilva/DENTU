from datetime import date, timedelta
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import login as auth_login, authenticate
from django.contrib.auth.models import User
from website.forms import AppointmentForm, PatientProfileForm
from website.models import (
    Appointment, AppointmentStatus, Dentist, Patient, Procedure,
    Payment, PaymentMethod, PaymentStatus,
)


def index(request):
    if request.user.is_authenticated:
        try:
            request.user.patient
            return redirect('loggado_paciente')
        except Patient.DoesNotExist:
            pass
    return render(request, 'index.html', {})


def contact(request):
    if request.method == "POST":
        message_name = request.POST['message-name']
        message_email = request.POST['message-email']
        message = request.POST['message']

        send_mail(
            "Message from " + message_name + "@" + message_email,
            message,
            settings.EMAIL_HOST_USER,
            ['laurimakoko44@gmail.com'],
        )

        return render(request, 'contact.html', {'message_name': message_name})

    else:
        return render(request, 'contact.html', {})


def signin(request):
    erro = None
    sucesso = None

    if request.method == 'POST':
        if 'cadastro' in request.POST:
            nome = request.POST.get('user', '').strip()
            email = request.POST.get('email', '').strip()
            address = request.POST.get('address', '').strip()
            date_of_birth = request.POST.get('date_of_birth', '').strip()
            senha = request.POST.get('senha', '').strip()

            if not all([nome, date_of_birth, address, email, senha]):
                erro = "Preencha todos os campos"
            elif User.objects.filter(username=nome).exists():
                erro = "Usuário já cadastrado"
            elif User.objects.filter(email=email).exists():
                erro = "E-mail já cadastrado"
            else:
                user = User.objects.create_user(username=nome, email=email, password=senha)
                Patient.objects.create(
                    user=user,
                    address=address,
                    date_of_birth=date_of_birth,
                )
                sucesso = "Conta criada com sucesso, faça login"

        elif 'login' in request.POST:
            identificador = request.POST.get('login-email', '').strip()
            senha = request.POST.get('login-senha', '')

            try:
                username = User.objects.get(email=identificador).username
            except User.DoesNotExist:
                username = None

            user = authenticate(request, username=username, password=senha) if username else None

            if user is not None:
                auth_login(request, user)
                next_url = request.POST.get('next') or request.GET.get('next') or 'loggado_paciente'
                return redirect(next_url)
            else:
                erro = 'E-mail ou senha incorretos.'

    return render(request, 'signin.html', {'erro': erro, 'sucesso': sucesso})


def signin_dentista(request):
    erro = None

    if request.method == 'POST':
        licenca = request.POST.get('email_cpf', '').strip()
        senha = request.POST.get('senha', '')

        try:
            dentist = Dentist.objects.get(license_number=licenca)
            username = dentist.user.username
        except Dentist.DoesNotExist:
            username = None

        user = authenticate(request, username=username, password=senha) if username else None

        if user is not None and hasattr(user, 'dentist'):
            auth_login(request, user)
            return redirect('loggado_dentista')
        else:
            erro = 'Licença ou senha incorretos.'

    return render(request, 'signin_dentista.html', {'erro': erro})


def loggado_dentista(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'dentist'):
        return redirect('signin_dentista')
    return render(request, 'loggado_dentista.html', {})


def loggado_paciente(request):
    if not request.user.is_authenticated:
        return redirect('signin')
    patient = request.user.patient
    appointments = Appointment.objects.filter(patient=patient).order_by('-start_datetime')
    return render(request, 'loggado_paciente.html', {
        'appointments': appointments,
        'AppointmentStatus': AppointmentStatus,
    })


def cancel_appointment(request, appointment_id):
    if request.method != 'POST':
        return redirect('loggado_paciente')
    if not request.user.is_authenticated:
        return redirect('signin')
    try:
        appointment = Appointment.objects.get(pk=appointment_id)
    except Appointment.DoesNotExist:
        return redirect('loggado_paciente')
    if appointment.patient.user != request.user:
        return redirect('loggado_paciente')
    if appointment.status == AppointmentStatus.SCHEDULED:
        appointment.cancel()
    return redirect('loggado_paciente')


@login_required(login_url='/signin/')
def patient_profile(request):
    patient = request.user.patient
    if request.method == 'POST':
        form = PatientProfileForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil atualizado com sucesso!")
            return redirect('patient_profile')
    else:
        form = PatientProfileForm(instance=patient)
    return render(request, 'patient_profile.html', {'form': form})


def payment(request):
    return render(request, 'payment.html', {})


def about(request):
    return render(request, 'about.html', {})


def pricing(request):
    return render(request, 'pricing.html', {})


def service(request):
    return render(request, 'service.html', {})


@login_required(login_url='/signin/')
def appointment(request):
    try:
        patient = request.user.patient
    except Patient.DoesNotExist:
        return render(request, 'appointment.html', {
            'not_patient': True,
        })

    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment_obj = Appointment(
                dentist=form.cleaned_data['dentist'],
                patient=patient,
                procedure=form.cleaned_data['procedure'],
            )
            start_dt = form.cleaned_data['start_datetime']
            appointment_obj.start_datetime = start_dt
            appointment_obj.end_datetime = start_dt + timedelta(
                minutes=appointment_obj.procedure.duration_minutes
            )
            try:
                appointment_obj.full_clean()
            except ValidationError as e:
                form.add_error(None, e)
            else:
                appointment_obj.save()
                Payment.objects.create(
                    appointment=appointment_obj,
                    amount=appointment_obj.procedure.price,
                    method=form.cleaned_data['payment_method'],
                    status=PaymentStatus.PENDING,
                )
                messages.success(request, "Consulta agendada com sucesso!")
                return redirect('appointment')
    else:
        form = AppointmentForm()

    return render(request, 'appointment.html', {
        'form': form,
        'patient': patient,
        'procedures': Procedure.objects.all(),
        'payment_method_choices': PaymentMethod.choices,
    })


def available_slots(request):
    try:
        dentist_id = request.GET.get('dentist')
        procedure_id = request.GET.get('procedure')
        if not dentist_id or not procedure_id:
            return JsonResponse({'error': 'Parâmetros dentista e procedimento são obrigatórios.'}, status=400)

        dentist = Dentist.objects.get(pk=dentist_id)
        procedure = Procedure.objects.get(pk=procedure_id)
    except (Dentist.DoesNotExist, Procedure.DoesNotExist):
        return JsonResponse({'error': 'Dentista ou procedimento não encontrado.'}, status=404)

    today = date.today()
    end_date = today + timedelta(days=14)

    slots = dentist.get_available_slots(procedure, today, end_date)

    data = [
        {
            'value': timezone.localtime(slot[0]).strftime('%Y-%m-%d %H:%M:%S'),
            'label': timezone.localtime(slot[0]).strftime('%d/%m %H:%M') + ' às ' + timezone.localtime(slot[1]).strftime('%H:%M'),
        }
        for slot in slots
    ]
    return JsonResponse({'slots': data})
