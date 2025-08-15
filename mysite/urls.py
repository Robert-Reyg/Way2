# mysite/urls.py

from django.contrib import admin
from django.urls import path, include # Asegúrate de que 'include' esté aquí

urlpatterns = [
    path('admin/', admin.site.urls),

    # AÑADE ESTA LÍNEA:
    # Esto le dice al proyecto que cualquier URL que no sea '/admin/'
    # debe buscarse en el archivo de URLs de la aplicación 'empresa'.
    path('', include('empresa.urls')),
]