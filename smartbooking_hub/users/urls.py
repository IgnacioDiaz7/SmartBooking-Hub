from django.urls import path
from .views import home_view, registro_dueno

urlpatterns = [
    # Ruta para renderizar la página web de inicio
    path('', home_view, name='home'),
    path('registro-dueno/', registro_dueno, name='registro_dueno'),
]