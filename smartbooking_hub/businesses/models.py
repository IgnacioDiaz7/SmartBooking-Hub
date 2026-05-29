from django.db import models
from django.conf import settings

class Business(models.Model):
    TIPO_NEGOCIO_CHOICES = [
        ('salon_belleza', 'Salón de Belleza'),
        ('peluqueria', 'Peluquería'),
        ('barberia', 'Barbería'),
        ('spa', 'Spa / Centro de Estética'),
    ]

    name = models.CharField(max_length=255, verbose_name="Nombre del Negocio")
    slug = models.SlugField(unique=True)
    business_type = models.CharField(max_length=50, choices=TIPO_NEGOCIO_CHOICES, default='salon_belleza', verbose_name="Tipo de Negocio")
    
    # Contacto y Ubicación
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono de Contacto")
    email = models.EmailField(blank=True, null=True, verbose_name="Correo del Negocio")
    address = models.TextField(blank=True, null=True, verbose_name="Dirección Comercial")
    instagram = models.URLField(blank=True, null=True, verbose_name="Enlace de Instagram")
    
    plan_type = models.CharField(max_length=50, choices=[
        ('free', 'Gratis'),
        ('pro', 'Pro'),
        ('premium', 'Premium')
    ], default='free')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class UserBusiness(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='business_roles')
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='staff')
    business_role = models.CharField(max_length=50, choices=[
        ('owner', 'Dueño'),
        ('manager', 'Administrador'),
        ('staff', 'Staff')
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'business') # Un usuario solo puede tener un rol por negocio

    def __str__(self):
        return f"{self.user.email} - {self.business.name} ({self.business_role})"

class Service(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100, blank=True, null=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.business.name}"

class BusinessHour(models.Model):
    DAY_CHOICES = [
        (0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'), 
        (3, 'Jueves'), (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo')
    ]
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='hours')
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    open_time = models.TimeField()
    close_time = models.TimeField()
    is_open = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('business', 'day_of_week')
        
class Appointment(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='appointments')
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appointments')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='appointments')
    date = models.DateTimeField()
    # Guardamos el precio en el momento de la cita para que no cambie si el precio del servicio cambia después
    price = models.DecimalField(max_digits=10, decimal_places=2) 
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.service.name} - {self.staff.first_name} - {self.date}"