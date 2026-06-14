from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Client, Business

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Definimos las columnas principales. Usamos email primero ya que es el identificador principal
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_active')
    
    # Filtros laterales muy útiles para buscar administradores, dueños o clientes
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser')
    
    # Buscador centrado en el email y nombre
    search_fields = ('email', 'first_name', 'last_name')
    
    # Inyectamos nuestro campo personalizado 'role' en las secciones del panel de Django
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Configuración de Roles (SaaS)', {
            'fields': ('role',),
        }),
    )

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'business', 'is_active')
    list_filter = ('is_active', 'business')
    search_fields = ('first_name', 'last_name', 'email', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Identificación', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'birth_date')
        }),
        ('Relaciones Multi-Tenant', {
            'fields': ('business', 'user')
        }),
        ('Información Adicional', {
            'fields': ('notes', 'is_active')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'current_plan', 'is_in_trial', 'trial_end')
    list_filter = ('current_plan', 'is_in_trial')
    search_fields = ('name', 'owner__email', 'owner__first_name')
    readonly_fields = ('trial_start',)
    
    fieldsets = (
        ('Información del Local', {
            'fields': ('owner', 'name')
        }),
        ('Suscripción SaaS', {
            'fields': ('current_plan', 'is_in_trial', 'trial_start', 'trial_end')
        }),
        ('Transbank (Card on File)', {
            'fields': ('tbk_user', 'card_number'),
            'description': 'Información de tokenización para cobros automáticos.'
        }),
    )