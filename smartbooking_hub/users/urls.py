from django.urls import path
from .views import home_view, registro_dueno, verificar_correo, dashboard, login_user, logout_user, pantalla_test, RegistroUsuarioAPI,transbank_confirm

urlpatterns = [
    # Rutas originales
    path('', home_view, name='home'),
    path('registro-dueno/', registro_dueno, name='registro_dueno'),
    path('verificar/<uidb64>/<token>/', verificar_correo, name='verificar_correo'),
    path('dashboard/', dashboard, name='dashboard'),
    path('login/', login_user, name='login'),
    path('logout/', logout_user, name='logout'),
    path('test/', pantalla_test, name='pantalla_test'),
    path('api/registro/', RegistroUsuarioAPI.as_view(), name='api_registro_usuario'),
    path('api/registro/transbank-confirm/', transbank_confirm, name='transbank_confirm'),
]