from django.contrib import admin
from .models import Worker, WorkerService, WorkerAvailability

@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'business', 'specialty', 'is_active')
    list_filter = ('is_active', 'business', 'specialty')
    search_fields = ('first_name', 'last_name', 'email', 'phone', 'business__name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('first_name', 'last_name', 'phone', 'email')
        }),
        ('Relaciones y Rol', {
            'fields': ('business', 'user', 'specialty', 'is_active'),
            'description': 'El usuario (User) es opcional si el trabajador no requiere iniciar sesión.'
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(WorkerService)
class WorkerServiceAdmin(admin.ModelAdmin):
    list_display = ('worker', 'service', 'created_at')
    # Filtramos por el negocio del trabajador para no mezclar servicios de distintos locales
    list_filter = ('worker__business', 'service')
    search_fields = ('worker__first_name', 'worker__last_name', 'service__name')
    readonly_fields = ('created_at',)

@admin.register(WorkerAvailability)
class WorkerAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('worker', 'get_day_display', 'start_time', 'end_time', 'is_available')
    list_filter = ('day_of_week', 'is_available', 'worker__business')
    search_fields = ('worker__first_name', 'worker__last_name')
    readonly_fields = ('created_at', 'updated_at')
    
    # Función para mostrar el nombre del día en lugar del número (0, 1, 2...)
    def get_day_display(self, obj):
        return obj.get_day_of_week_display()
    get_day_display.short_description = 'Día de la semana'