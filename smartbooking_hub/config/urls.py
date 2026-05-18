from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Panel de administración de Django
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    
    # IMPORTANTE: Dejamos estas comentadas temporalmente hasta que 
    # creemos los archivos urls.py dentro de cada una de estas apps.
    # Si las descomentamos ahora, Django arrojará un error de módulo no encontrado.
    # path('api/v1/businesses/', include('businesses.urls')),
    # path('api/v1/workers/', include('workers.urls')),
    # path('api/v1/bookings/', include('bookings.urls')),
]