
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
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.http import require_http_methods

from website.forms import (
    AppointmentForm, PatientProfileForm, WeeklyScheduleForm, DentistProfileForm,
    AppointmentRatingForm, AppointmentDetailsForm,
)
from website.models import (
    Appointment, AppointmentRating, AppointmentStatus, Dentist, Patient, Procedure,
    Payment, PaymentMethod, PaymentStatus, WeeklySchedule,
)

# --- Funções Auxiliares de Autenticação (Refatoradas) ---

def _handle_registration(request):
    nome = request.POST.get('user', '').strip()
    email = request.POST.get('email', '').strip()
    address = request.POST.get('address', '').strip()
    date_of_birth = request.POST.get('date_of_birth', '').strip()
    senha = request.POST.get('senha', '').strip()

    if not all([nome, date_of_birth, address, email, senha]):
        return "Preencha todos os campos", None
    if User.objects.filter(username=nome).exists():
        return "Usuário já cadastrado", None
    if User.objects.filter(email=email).exists():
        return "E-mail já cadastrado", None
    
    user = User.objects.create_user(username=nome, email=email, password=senha)
    Patient.objects.create(
        user=user,
        address=address,
        date_of_birth=date_of_birth,
    )
    return None, "Conta criada com sucesso, faça login"

def _handle_login(request):
    identificador = request.POST.get('login-email', '').strip()
    senha = request.POST.get('login-senha', '')

    try:
        username = User.objects.get(email=identificador).username
    except User.DoesNotExist:
        return 'E-mail ou senha incorretos.', None

    user = authenticate(request, username=username, password=senha)
    if user is not None:
        auth_login(request, user)
        return None, user
    
    return 'E-mail ou senha incorretos.', None

# --- Views ---

@require_GET
def index(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'patient'):
            return redirect('loggado_paciente')
        if hasattr(request.user, 'dentist'):
            return redirect('loggado_dentista')
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
            erro, sucesso = _handle_registration(request)
        elif 'login' in request.POST:
            erro, user = _handle_login(request)
            if user:
                next_url = request.POST.get('next') or request.GET.get('next') or 'loggado_paciente'
                return redirect(next_url)

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

        user = authenticate(request, username=username,
                            password=senha) if username else None

        if user is not None and hasattr(user, 'dentist'):
            auth_login(request, user)
            return redirect('loggado_dentista')
        else:
            erro = 'Licença ou senha incorretos.'

    return render(request, 'signin_dentista.html', {'erro': erro})


@require_GET
def loggado_dentista(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'dentist'):
        return redirect('signin_dentista')
    messages.get_messages(request).used = True
    dentist = request.user.dentist
    appointments = Appointment.objects.filter(dentist=dentist)

    status = request.GET.get('status')
    periodo = request.GET.get('periodo')
    busca = request.GET.get('busca', '').strip()

    if status:
        appointments = appointments.filter(status=status)
    if periodo == 'hoje':
        appointments = appointments.filter(start_datetime__date=date.today())
    elif periodo == 'proximas':
        appointments = appointments.filter(start_datetime__date__gte=date.today())
    elif periodo == 'passadas':
        appointments = appointments.filter(start_datetime__date__lt=date.today())
    if busca:
        from django.db.models import Q
        appointments = appointments.filter(
            Q(patient__user__first_name__icontains=busca) |
            Q(patient__user__last_name__icontains=busca) |
            Q(procedure__name__icontains=busca)
        )

    appointments = appointments.order_by('-start_datetime')
    return render(request, 'loggado_dentista.html', {
        'appointments': appointments,
        'AppointmentStatus': AppointmentStatus,
        'today': date.today(),
    })


@require_GET
def loggado_paciente(request):
    if not request.user.is_authenticated:
        return redirect('signin')
    patient = request.user.patient
    appointments = Appointment.objects.filter(patient=patient)

    status = request.GET.get('status')
    periodo = request.GET.get('periodo')
    busca = request.GET.get('busca', '').strip()

    if status:
        appointments = appointments.filter(status=status)
    if periodo == 'hoje':
        appointments = appointments.filter(start_datetime__date=date.today())
    elif periodo == 'proximas':
        appointments = appointments.filter(start_datetime__date__gte=date.today())
    elif periodo == 'passadas':
        appointments = appointments.filter(start_datetime__date__lt=date.today())
    if busca:
        from django.db.models import Q
        appointments = appointments.filter(
            Q(dentist__user__first_name__icontains=busca) |
            Q(dentist__user__last_name__icontains=busca) |
            Q(procedure__name__icontains=busca)
        )

    appointments = appointments.order_by('-start_datetime')
    return render(request, 'loggado_paciente.html', {
        'appointments': appointments,
        'AppointmentStatus': AppointmentStatus,
    })


@require_POST
def cancel_appointment(request, appointment_id):
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


@login_required(login_url='/signin/')
def rate_appointment(request, appointment_id):
    try:
        appointment = Appointment.objects.get(pk=appointment_id)
    except Appointment.DoesNotExist:
        return redirect('loggado_paciente')

    if appointment.patient.user != request.user:
        return redirect('loggado_paciente')

    if appointment.status != AppointmentStatus.COMPLETED:
        return redirect('loggado_paciente')

    has_rating = hasattr(appointment, 'rating')

    if request.method == 'POST':
        rating = appointment.rating if has_rating else None
        form = AppointmentRatingForm(request.POST, instance=rating)
        if form.is_valid():
            rating_obj = form.save(commit=False)
            rating_obj.appointment = appointment
            rating_obj.save()
            messages.success(request, "Avaliação registrada com sucesso!")
            return redirect('loggado_paciente')
    else:
        if has_rating:
            messages.info(request, "Você já avaliou esta consulta.")
            return redirect('loggado_paciente')
        form = AppointmentRatingForm()

    return render(request, 'rate_appointment.html', {
        'form': form,
        'appointment': appointment,
    })


def dentist_schedule(request):
    if not request.user.is_authenticated or not hasattr(request.user, 'dentist'):
        return redirect('signin_dentista')
    messages.get_messages(request).used = True
    dentist = request.user.dentist

    if request.method == 'POST':
        if 'add' in request.POST:
            form = WeeklyScheduleForm(request.POST)
            if form.is_valid():
                WeeklySchedule.objects.create(
                    dentist=dentist,
                    day_of_week=form.cleaned_data['day_of_week'],
                    start_time=form.cleaned_data['start_time'],
                    end_time=form.cleaned_data['end_time'],
                )
                messages.success(request, "Horário adicionado com sucesso!")
        elif 'remove' in request.POST:
            schedule_id = request.POST.get('schedule_id')
            WeeklySchedule.objects.filter(
                pk=schedule_id, dentist=dentist).delete()
            messages.success(request, "Horário removido.")
        elif 'generate' in request.POST:
            today = date.today()
            created = dentist.generate_schedules(
                today, today + timedelta(days=30))
            messages.success(
                request, f"Agenda gerada para os próximos 30 dias ({created} horários).")

    weekly_schedules = WeeklySchedule.objects.filter(
        dentist=dentist).order_by('day_of_week', 'start_time')
    form = WeeklyScheduleForm()
    return render(request, 'dentist_schedule.html', {
        'weekly_schedules': weekly_schedules,
        'form': form,
    })


@login_required(login_url='/signin/')
def dentist_profile(request):
    dentist = request.user.dentist
    if request.method == 'POST':
        form = DentistProfileForm(request.POST, instance=dentist)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil atualizado com sucesso!")
            return redirect('dentist_profile')
    else:
        form = DentistProfileForm(instance=dentist)
    return render(request, 'dentist_profile.html', {'form': form})


@require_POST
def complete_appointment(request, appointment_id):
    if not request.user.is_authenticated or not hasattr(request.user, 'dentist'):
        return redirect('signin_dentista')
    try:
        appointment = Appointment.objects.get(pk=appointment_id)
    except Appointment.DoesNotExist:
        return redirect('loggado_dentista')
    if appointment.dentist.user != request.user:
        return redirect('loggado_dentista')
    if appointment.status == AppointmentStatus.SCHEDULED or appointment.status == AppointmentStatus.NO_SHOW:
        appointment.complete()
    return redirect('loggado_dentista')


@require_POST
def no_show_appointment(request, appointment_id):
    if not request.user.is_authenticated or not hasattr(request.user, 'dentist'):
        return redirect('signin_dentista')
    try:
        appointment = Appointment.objects.get(pk=appointment_id)
    except Appointment.DoesNotExist:
        return redirect('loggado_dentista')
    if appointment.dentist.user != request.user:
        return redirect('loggado_dentista')
    if appointment.status == AppointmentStatus.SCHEDULED:
        appointment.mark_no_show()
    return redirect('loggado_dentista')


def dentist_appointment_details(request, appointment_id):
    if not request.user.is_authenticated or not hasattr(request.user, 'dentist'):
        return redirect('signin_dentista')
    messages.get_messages(request).used = True
    try:
        appointment = Appointment.objects.get(pk=appointment_id)
    except Appointment.DoesNotExist:
        return redirect('loggado_dentista')
    if appointment.dentist.user != request.user:
        return redirect('loggado_dentista')
    if appointment.status != AppointmentStatus.COMPLETED:
        return redirect('loggado_dentista')

    details = appointment.details if hasattr(appointment, 'details') else None

    if request.method == 'POST':
        form = AppointmentDetailsForm(request.POST, instance=details)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.appointment = appointment
            obj.save()
            messages.success(request, "Detalhes salvos com sucesso!")
            return redirect('loggado_dentista')
    else:
        form = AppointmentDetailsForm(instance=details)

    return render(request, 'dentist_appointment_details.html', {
        'form': form,
        'appointment': appointment,
    })


@require_GET
def patient_appointment_details(request, appointment_id):
    if not request.user.is_authenticated:
        return redirect('signin')
    try:
        appointment = Appointment.objects.get(pk=appointment_id)
    except Appointment.DoesNotExist:
        return redirect('loggado_paciente')
    if appointment.patient.user != request.user:
        return redirect('loggado_paciente')
    if appointment.status != AppointmentStatus.COMPLETED:
        return redirect('loggado_paciente')
    details = appointment.details if hasattr(appointment, 'details') else None
    return render(request, 'patient_appointment_details.html', {
        'appointment': appointment,
        'details': details,
    })


@require_GET
def dentists_list(request):
    dentists = Dentist.objects.select_related('user').all()
    return render(request, 'dentists_list.html', {'dentists': dentists})


@require_http_methods(["GET"])
def payment(request):
    return render(request, 'payment.html', {})


@require_http_methods(["GET"])
def about(request):
    return render(request, 'about.html', {})


@require_http_methods(["GET"])
def pricing(request):
    return render(request, 'pricing.html', {})


@require_http_methods(["GET"])
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


@require_GET
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
