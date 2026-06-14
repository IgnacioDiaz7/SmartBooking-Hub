from django.contrib import admin
from .models import Booking, TimeBlock, BookingStatusHistory

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    # Columnas que se mostrarán en la lista principal
    list_display = ('id', 'business', 'client', 'worker', 'booking_date', 'start_time', 'status', 'total_price')
    
    # Filtros laterales (muy útiles para buscar reservas de un local o estado específico)
    list_filter = ('status', 'booking_date', 'business', 'worker')
    
    # Barra de búsqueda (permite buscar por el nombre, apellido o email del cliente)
    search_fields = ('client__first_name', 'client__last_name', 'client__email', 'notes')
    
    # Navegación por fechas en la parte superior
    date_hierarchy = 'booking_date'
    
    # Campos de solo lectura por seguridad
    readonly_fields = ('created_at', 'updated_at')

@admin.register(TimeBlock)
class TimeBlockAdmin(admin.ModelAdmin):
    list_display = ('id', 'business', 'worker', 'block_date', 'start_time', 'end_time', 'reason')
    list_filter = ('business', 'worker', 'block_date')
    search_fields = ('reason', 'worker__first_name', 'worker__last_name')
    date_hierarchy = 'block_date'
    readonly_fields = ('created_at', 'updated_at')

@admin.register(BookingStatusHistory)
class BookingStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'old_status', 'new_status', 'changed_by_user', 'changed_at')
    list_filter = ('new_status', 'changed_at')
    search_fields = ('booking__id', 'reason', 'changed_by_user__email')
    
    # El historial nunca debería modificarse manualmente
    readonly_fields = ('booking', 'old_status', 'new_status', 'changed_by_user', 'reason', 'changed_at')
    
    # Desactivamos la opción de agregar un historial manualmente desde el admin
    def has_add_permission(self, request):
        return False