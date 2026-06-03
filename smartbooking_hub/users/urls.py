from django.urls import path
from .views import home_view, verificar_correo, dashboard, login_user, logout_user, pantalla_test, RegistroUsuarioAPI, transbank_confirm, public_booking, get_available_slots, confirm_booking, webpay_return

urlpatterns = [
    # Rutas originales
    path('', home_view, name='home'),
    path('verificar/<uidb64>/<token>/', verificar_correo, name='verificar_correo'),
    path('dashboard/', dashboard, name='dashboard'),
    path('login/', login_user, name='login'),
    path('logout/', logout_user, name='logout'),
    path('test/', pantalla_test, name='pantalla_test'),
    path('api/registro/', RegistroUsuarioAPI.as_view(), name='api_registro_usuario'),
    path('api/registro/transbank-confirm/', transbank_confirm, name='transbank_confirm'),
    path('reservar/<slug:business_slug>/', public_booking, name='public_booking'),
    path('api/disponibilidad/<slug:business_slug>/', get_available_slots, name='api_disponibilidad'),
    path('reservar/<slug:business_slug>/confirmar/', confirm_booking, name='confirm_booking'),
    path('reservar/<slug:business_slug>/webpay-return/', webpay_return, name='webpay_return'),
    
]