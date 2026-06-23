#from django.contrib import admin
from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
	path('', views.index, name="index"),
	path('contact.html', views.contact, name="contact"),
	path('signin/', views.signin, name="signin"),
	path('payment/', views.payment, name="payment"),
	path('about.html', views.about, name="about"),
	path('pricing.html', views.pricing, name="pricing"),
	path('service.html', views.service, name="service"),
	path('appointment/', views.appointment, name="appointment"),
	path('appointment/slots/', views.available_slots, name="available_slots"),
	path('signin/dentista/', views.signin_dentista, name='signin_dentista'),
	path('paciente/', views.loggado_paciente, name='loggado_paciente'),
	path('dentista/', views.loggado_dentista, name='loggado_dentista'),
	path('paciente/dentistas/', views.dentists_list, name='dentists_list'),
	path('paciente/consulta/<int:appointment_id>/detalhes/', views.patient_appointment_details, name='patient_appointment_details'),
	path('paciente/perfil/', views.patient_profile, name='patient_profile'),
	path('paciente/avaliar/<int:appointment_id>/', views.rate_appointment, name='rate_appointment'),
	path('paciente/cancelar/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),
	path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
	path('dentista/horario/', views.dentist_schedule, name='dentist_schedule'),
	path('dentista/perfil/', views.dentist_profile, name='dentist_profile'),
	path('dentista/consulta/<int:appointment_id>/concluir/', views.complete_appointment, name='complete_appointment'),
	path('dentista/consulta/<int:appointment_id>/faltou/', views.no_show_appointment, name='no_show_appointment'),
	path('dentista/consulta/<int:appointment_id>/detalhes/', views.dentist_appointment_details, name='dentist_appointment_details'),
	path('suporte/', views.support, name='support'),
]
