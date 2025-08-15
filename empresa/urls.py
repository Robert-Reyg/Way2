# empresa/urls.py

from django.urls import path
from . import views

app_name = 'empresa'

urlpatterns = [
    # --- Vistas de Páginas ---
    path('empleados/', views.lista_empleados, name='lista_empleados'),
    path('movimiento/nuevo/', views.crear_movimiento, name='crear_movimiento'),
    
    path('certificado/<int:empleado_id>/', views.generar_certificado_pdf, name='generar_certificado_pdf'),
    
    # path('reportes/por-turno/', views.reporte_por_turno, name='reporte_por_turno'),
    path('reportes/diario/', views.reporte_diario, name='reporte_diario'),

    # --- Endpoints de API ---
    path('api/buscar-empleado/', views.buscar_empleado_api, name='api_buscar_empleado'),
    path('api/ultimo-horometro/', views.ultimo_horometro_api, name='api_ultimo_horometro'),

    path('produccion/diaria/', views.informe_produccion_diario, name='informe_produccion_diario'),

    # --- AÑADE ESTA LÍNEA PARA EXPORTAR EL INFORME A PDF ---
    path('produccion/diaria/pdf/<str:fecha>/<str:turno>/', views.generar_informe_pdf, name='generar_informe_pdf'),

    # --- AÑADE ESTA LÍNEA PARA LA NUEVA PÁGINA DE POSTURAS ---
    path('produccion/definir-posturas/', views.definir_posturas, name='definir_posturas'),
]