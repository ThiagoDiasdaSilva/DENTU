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
	path('paciente/perfil/', views.patient_profile, name='patient_profile'),
	path('paciente/cancelar/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),
	path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
]
