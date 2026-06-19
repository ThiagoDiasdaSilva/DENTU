from datetime import date, timedelta
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from website.forms import AppointmentForm
from website.models import (
    Appointment, Dentist, Patient, Procedure,
    Payment, PaymentMethod, PaymentStatus,
)


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
            ['laurimakoko44@gmail.com'],
        )

        return render(request, 'contact.html', {'message_name': message_name})

    else:
        return render(request, 'contact.html', {})


def signin(request):
    return render(request, 'signin.html', {})


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
        return render(request, 'appointment.html', {
            'not_authenticated': True,
        })

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
            'value': slot[0].strftime('%Y-%m-%d %H:%M:%S'),
            'label': slot[0].strftime('%d/%m %H:%M') + ' às ' + slot[1].strftime('%H:%M'),
        }
        for slot in slots
    ]
    return JsonResponse({'slots': data})
