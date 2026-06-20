from datetime import date, timedelta
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from website.forms import AppointmentForm
from website.models import Appointment, Dentist, Patient, Procedure
from django.contrib.auth import login as auth_login, authenticate
from django.contrib.auth.models import User


def index(request):
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
            ['thcds24@gmail.com'],
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
            elif User.objects.filter(username=nome).exists():  # ✅ username, não nome
                erro = "Usuário já cadastrado"
            elif User.objects.filter(email=email).exists():
                erro = "E-mail já cadastrado"
            else:
                user = User.objects.create_user(username=nome, email=email, password=senha)
                Patient.objects.create(  # ✅ sem nome/senha, pois estão no User
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

            user = authenticate(request, username=username, password=senha) if username else None  # ✅ faltava o authenticate

            if user is not None:
                auth_login(request, user)
                return redirect('loggado_paciente')
            else:
                erro = 'E-mail ou senha incorretos.'

    return render(request, 'signin.html', {'erro': erro, 'sucesso': sucesso})


def signin_dentista(request):
    erro = None

    if request.method == 'POST':
        licenca = request.POST.get('email_cpf', '').strip()
        print("POST completo:", dict(request.POST))
        senha = request.POST.get('senha', '')

        print("=== DEBUG DENTISTA ===")
        print("Licença:", licenca)
        print("Senha:", senha)

        try:
            dentist = Dentist.objects.get(license_number=licenca)
            username = dentist.user.username
            print("Dentist encontrado:", dentist)
            print("Username:", username)
        except Dentist.DoesNotExist:
            username = None
            print("Dentist NÃO encontrado para licença:", licenca)

        user = authenticate(request, username=username, password=senha) if username else None
        print("User autenticado:", user)

        if user is not None and hasattr(user, 'dentist'):
            auth_login(request, user)
            return redirect('loggado_dentista')
        else:
            print("Falhou — user:", user, "| tem dentist:", hasattr(user, 'dentist') if user else 'N/A')
            erro = 'Licença ou senha incorretos.'

    return render(request, 'signin_dentista.html', {'erro': erro})


def loggado_dentista(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'dentist'):
        return redirect('signin_dentista')
    return render(request, 'loggado_dentista.html', {})


def loggado_paciente(request):
    if not request.user.is_authenticated:
        return redirect('signin')
    return render(request, 'loggado_paciente.html', {})


def payment(request):
    return render(request, 'payment.html', {})


def about(request):
    return render(request, 'about.html', {})


def pricing(request):
    return render(request, 'pricing.html', {})


def service(request):
    return render(request, 'service.html', {})


def appointment(request):
    if not request.user.is_authenticated:
        return render(request, 'appointment.html', {'not_authenticated': True})

    try:
        patient = request.user.patient
    except Patient.DoesNotExist:
        return render(request, 'appointment.html', {'not_patient': True})

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
                messages.success(request, "Consulta agendada com sucesso!")
                return redirect('appointment')
    else:
        form = AppointmentForm()

    return render(request, 'appointment.html', {'form': form, 'patient': patient})


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
            'value': slot[0].strftime('%Y-%m-%d %H:%M:%S'),
            'label': slot[0].strftime('%d/%m %H:%M') + ' às ' + slot[1].strftime('%H:%M'),
        }
        for slot in slots
    ]
    return JsonResponse({'slots': data})