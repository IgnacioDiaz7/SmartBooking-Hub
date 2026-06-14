from django.contrib import admin
from .models import Business, UserBusiness, Service, BusinessHour, Appointment

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    # Columnas principales en la lista de negocios
    list_display = ('name', 'business_type', 'plan_type', 'is_active', 'is_in_trial', 'created_at')
    
    # Filtros laterales para segmentar clientes SaaS
    list_filter = ('business_type', 'plan_type', 'is_active', 'is_in_trial')
    
    # Búsqueda rápida por nombre o contacto
    search_fields = ('name', 'email', 'phone')
    
    # Autocompleta el slug dinámicamente al escribir el nombre del negocio
    prepopulated_fields = {'slug': ('name',)}
    
    # Protege campos de auditoría
    readonly_fields = ('created_at', 'updated_at')
    
    # Organiza el formulario de detalle en secciones limpias
    fieldsets = (
        ('Información Principal', {
            'fields': ('name', 'slug', 'business_type', 'is_active')
        }),
        ('Contacto y Ubicación', {
            'fields': ('phone', 'email', 'address', 'instagram')
        }),
        ('Suscripción y Pagos (SaaS)', {
            'fields': ('plan_type', 'is_in_trial', 'trial_end', 'tbk_user', 'card_number')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(UserBusiness)
class UserBusinessAdmin(admin.ModelAdmin):
    list_display = ('user', 'business', 'business_role', 'provides_services', 'commission_percentage')
    list_filter = ('business_role', 'provides_services', 'business')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'business__name')

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'business', 'category', 'price', 'duration_minutes', 'is_active')
    list_filter = ('is_active', 'category', 'business')
    search_fields = ('name', 'description', 'business__name')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(BusinessHour)
class BusinessHourAdmin(admin.ModelAdmin):
    list_display = ('business', 'get_day_display', 'open_time', 'close_time', 'is_open')
    list_filter = ('day_of_week', 'is_open', 'business')
    
    # Método para mostrar el nombre del día en lugar del número (0, 1, 2...)
    def get_day_display(self, obj):
        return obj.get_day_of_week_display()
    get_day_display.short_description = 'Día de la semana'

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'business', 'client', 'staff', 'service', 'date', 'status', 'price')
    list_filter = ('status', 'date', 'business', 'staff')
    search_fields = ('client__first_name', 'client__last_name', 'client__email', 'service__name')
    date_hierarchy = 'date'
    readonly_fields = ('created_at',)