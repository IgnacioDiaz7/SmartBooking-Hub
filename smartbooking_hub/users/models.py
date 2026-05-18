from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # AbstractUser ya incluye first_name, last_name, password (hash), is_active
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50, choices=[
        ('admin', 'Administrador'),
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