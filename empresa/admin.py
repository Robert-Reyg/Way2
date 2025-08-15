# empresa/admin.py

from django.contrib import admin
from .models import (
    Cliente, 
    Maquinaria, 
    Movimiento, 
    Proyecto, 
    TipoLicencia, 
    Empleado,
    Supervisor,       
    InformeDiario,    
    Postura,
    Viaje,  
)

# Registramos los modelos para que aparezcan en el admin
admin.site.register(Cliente)
admin.site.register(Maquinaria)
admin.site.register(Movimiento)
admin.site.register(Proyecto)
admin.site.register(TipoLicencia)
admin.site.register(Empleado)
admin.site.register(Supervisor)     
admin.site.register(InformeDiario)  
admin.site.register(Postura)
admin.site.register(Viaje) # Añade esta línea al final   