from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model

class User(AbstractUser):
    # AbstractUser ya incluye first_name, last_name, password (hash), is_active
    email = models.EmailField(unique=True)
    
    # Agregamos 'owner' a las opciones válidas para que haga match con el frontend
    role = models.CharField(max_length=50, choices=[
        ('admin', 'Administrador'),
        ('owner', 'Dueño de Negocio'),
        ('worker', 'Trabajador'),
        ('client', 'Cliente')
    ], default='client')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

class Client(models.Model):
    # Referencia cruzada como string para evitar errores de importación circular
    business = models.ForeignKey('businesses.Business', on_delete=models.CASCADE, related_name='clients')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='client_profiles')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField()
    birth_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.business.name}"
    
    
User = get_user_model()
    
class Business(models.Model):
    # Definición de los niveles del SaaS
    PLAN_CHOICES = [
        ('emprendedor', 'Plan Emprendedor (Staff 2)'),
        ('pro', 'Plan Profesional (Staff 4)'),
        ('luxury', 'Plan Luxury (Staff 6)'),
    ]

    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='business')
    name = models.CharField(max_length=150, verbose_name="Nombre del Local")
    
    # ========================================================
    # CONTROL DE SUSCRIPCIÓN SAAS (TRIAL Y PLAN)
    # ========================================================
    current_plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='pro')
    is_in_trial = models.BooleanField(default=True)
    trial_start = models.DateTimeField(auto_now_add=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    
    # ========================================================
    # SEGURIDAD FINANCIERA (TRANSBANK CARD ON FILE)
    # ========================================================
    tbk_user = models.CharField(max_length=100, null=True, blank=True, verbose_name="Token Cliente Transbank")
    card_number = models.CharField(max_length=20, null=True, blank=True, verbose_name="Máscara de Tarjeta")

    def __str__(self):
        return f"{self.name} - Plan: {self.get_current_plan_display()}"