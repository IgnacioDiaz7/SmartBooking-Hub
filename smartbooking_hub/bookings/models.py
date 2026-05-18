from django.db import models
from django.conf import settings

class TimeBlock(models.Model):
    business = models.ForeignKey('businesses.Business', on_delete=models.CASCADE, related_name='time_blocks')
    worker = models.ForeignKey('workers.Worker', on_delete=models.CASCADE, related_name='time_blocks', null=True, blank=True)
    
    block_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reason = models.CharField(max_length=255, blank=True, null=True) # Ej: "Almuerzo", "Vacaciones"
    
    created_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_blocks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Bloqueo: {self.block_date} {self.start_time}-{self.end_time}"

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('confirmed', 'Confirmada'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada')
    ]
    
    business = models.ForeignKey('businesses.Business', on_delete=models.CASCADE, related_name='bookings')
    client = models.ForeignKey('users.Client', on_delete=models.CASCADE, related_name='bookings')
    worker = models.ForeignKey('workers.Worker', on_delete=models.CASCADE, related_name='bookings')
    service = models.ForeignKey('businesses.Service', on_delete=models.SET_NULL, null=True, related_name='bookings')
    
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=50, blank=True, null=True) # Ej: "web", "app", "manual"
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_bookings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reserva {self.id} - {self.client.first_name} - {self.booking_date}"

class BookingStatusHistory(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    changed_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    reason = models.CharField(max_length=255, blank=True, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reserva {self.booking.id}: {self.old_status} -> {self.new_status}"