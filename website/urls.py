#from django.contrib import admin
from django.urls import path
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
	path('signin/dentista/', views.signin_dentista, name='signin_dentista'),
	path('appointment/slots/', views.available_slots,   name="available_slots"),
	path('paciente/', views.loggado_paciente, name='loggado_paciente'),
	path('dentista/', views.loggado_dentista, name='loggado_dentista'),
]
