# empresa/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.utils import timezone
from django.db.models import Count, Sum, Min, Max
from weasyprint import HTML
from decimal import Decimal
from datetime import date
from django.forms import formset_factory

# Se importan todos los modelos necesarios en una sola instrucción
from .models import (
    Empleado, Maquinaria, Movimiento, TipoLicencia, ProduccionEquipo,
    Supervisor, InformeDiario, Postura, Lugar, Material, Viaje
)
# Se importan los formularios que usaremos
from .forms import MovimientoCompletoForm, PosturaForm, ViajeForm


# --- VISTAS ORIGINALES ---

def limpiar_decimales(data):
    """Convierte todos los Decimal en un dict a float."""
    for key, value in data.items():
        if isinstance(value, Decimal):
            data[key] = float(value)
    return data

def lista_empleados(request):
    todos_los_empleados = Empleado.objects.all()
    return render(request, 'empresa/lista_empleados.html', {'empleados': todos_los_empleados})

def generar_certificado_pdf(request, empleado_id):
    try:
        empleado = Empleado.objects.get(id=empleado_id)
    except Empleado.DoesNotExist:
        return HttpResponse("Empleado no encontrado.", status=404)
    template = get_template('empresa/certificado.html')
    contexto = { 'empleado': empleado, 'fecha_emision': date.today() }
    html_string = template.render(contexto)
    pdf_file = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="certificado_{empleado.rut}.pdf"'
    return response

# --- VISTAS DE API ---

def buscar_empleado_api(request):
    codigo = request.GET.get('codigo', None)
    if not codigo:
        return JsonResponse({'error': 'Código de trabajador no proporcionado'}, status=400)
    try:
        empleado = Empleado.objects.get(codigo_trabajador=codigo)
        licencias = ", ".join([lic.nombre for lic in empleado.licencias.all()])
        dias_restantes = None
        fecha_vencimiento_str = 'No especificada'
        if empleado.fecha_vencimiento_licencia:
            fecha_vencimiento_str = empleado.fecha_vencimiento_licencia.strftime('%d-%m-%Y')
            diferencia = empleado.fecha_vencimiento_licencia - date.today()
            dias_restantes = diferencia.days
        data = { 
            'id': empleado.id, 
            'nombre_completo': empleado.nombre_completo, 
            'rut': empleado.rut, 
            'cargo': empleado.cargo, 
            'tipo_licencia': licencias, 
            'fecha_vencimiento_licencia': fecha_vencimiento_str, 
            'dias_vencimiento_licencia': dias_restantes 
        }
        return JsonResponse(data)
    except Empleado.DoesNotExist:
        return JsonResponse({'error': 'Empleado no encontrado'}, status=404)

def ultimo_horometro_api(request):
    maquinaria_id = request.GET.get('maquinaria_id', None)
    if not maquinaria_id:
        return JsonResponse({'error': 'ID de maquinaria no proporcionado'}, status=400)
    
    ultimo_movimiento = Movimiento.objects.filter(maquinaria_id=maquinaria_id).order_by('-fecha', '-id').first()
    
    if ultimo_movimiento:
        data = {'ultimo_horometro': ultimo_movimiento.horometro_final}
    else:
        try:
            maquina = Maquinaria.objects.get(pk=maquinaria_id)
            data = {'ultimo_horometro': maquina.horometro_actual}
        except Maquinaria.DoesNotExist:
            data = {'ultimo_horometro': 0}
            
    return JsonResponse(data)

def obtener_posturas_api(request):
    fecha_str = request.GET.get('fecha')
    turno = request.GET.get('turno')
    
    if not fecha_str or not turno:
        return JsonResponse({'error': 'Faltan los parámetros de fecha o turno'}, status=400)
    
    try:
        fecha = date.fromisoformat(fecha_str)
        informe_diario = InformeDiario.objects.get(fecha=fecha, turno=turno)
        
        posturas = Postura.objects.filter(informe=informe_diario).order_by('numero_postura')
        
        posturas_data = [
            {
                'id': postura.id,
                'descripcion': f"Postura #{postura.numero_postura}: {postura.tipo_actividad} - {postura.origen} a {postura.destino}",
            }
            for postura in posturas
        ]
        
        return JsonResponse({'posturas': posturas_data})

    except (ValueError, InformeDiario.DoesNotExist):
        return JsonResponse({'posturas': []})

# --- VISTA PARA CREAR UN MOVIMIENTO ---

def crear_movimiento(request):
    """
    Gestiona el formulario de un solo paso para crear un Movimiento y sus Viajes asociados.
    """
    ViajeFormSet = formset_factory(ViajeForm, extra=0)
    
    if request.method == 'POST':
        form = MovimientoCompletoForm(request.POST)
        formset = ViajeFormSet(request.POST, prefix='viajes')

        if form.is_valid() and formset.is_valid():
            movimiento = form.save(commit=False)
            
            # Ajuste de horas trabajadas si no se ingresó horómetro final
            if movimiento.horometro_final is None:
                movimiento.horas_trabajadas = None
                
            movimiento.save()
            
            # Guardar los objetos Viaje para cada form validado
            for viaje_form in formset:
                if viaje_form.has_changed() and viaje_form.cleaned_data.get('cantidad', 0) > 0:
                    viaje = viaje_form.save(commit=False)
                    viaje.movimiento = movimiento
                    viaje.save()

            messages.success(request, f"Movimiento y viajes del trabajador {movimiento.empleado.nombre_completo} guardados con éxito.")
            return redirect('empresa:crear_movimiento')
        else:
            messages.error(request, "Por favor, corrija los errores en el formulario.")
            
            # En caso de error, necesitamos volver a cargar las posturas
            fecha_str = request.POST.get('fecha')
            turno = request.POST.get('turno')
            
            posturas_json = []
            if fecha_str and turno:
                try:
                    fecha_obj = date.fromisoformat(fecha_str)
                    informe = InformeDiario.objects.get(fecha=fecha_obj, turno=turno)
                    posturas_qs = Postura.objects.filter(informe=informe).order_by('numero_postura')
                    posturas_json = [
                        {'id': p.id, 'descripcion': f"Postura #{p.numero_postura}: {p.tipo_actividad} - {p.origen} a {p.destino}"}
                        for p in posturas_qs
                    ]
                except (ValueError, InformeDiario.DoesNotExist):
                    pass
            
            contexto = {
                'form': form,
                'formset': formset,
                'mostrar_viajes': True,
                'posturas_json': posturas_json,
            }
            return render(request, 'empresa/movimiento_form.html', contexto)
    
    else: # Lógica para GET
        form = MovimientoCompletoForm()
        formset = ViajeFormSet(prefix='viajes')
        
        return render(request, 'empresa/movimiento_form.html', {
            'form': form,
            'formset': formset,
            'mostrar_viajes': True,
            'posturas_json': [],  # Se envía vacío en el primer render
        })

# --- OTRAS VISTAS ---

def reporte_diario(request):
    fecha_seleccionada_str = request.GET.get('fecha')
    if fecha_seleccionada_str:
        fecha_seleccionada = date.fromisoformat(fecha_seleccionada_str)
    else:
        fecha_seleccionada = timezone.localdate()

    movimientos_del_dia = Movimiento.objects.filter(fecha=fecha_seleccionada).select_related('empleado', 'maquinaria').order_by('id')
    contexto = {
        'titulo': f"Reporte Diario de Movimientos - {fecha_seleccionada.strftime('%d/%m/%Y')}",
        'movimientos': movimientos_del_dia,
        'fecha_seleccionada': fecha_seleccionada.isoformat()
    }
    return render(request, 'empresa/reporte_diario.html', contexto)

def informe_produccion_diario(request):
    fecha_seleccionada = None
    turno_seleccionado = None
    
    if request.method == 'POST':
        action = request.POST.get('action')
        fecha_seleccionada_str = request.POST.get('fecha')
        turno_seleccionado = request.POST.get('turno')
        fecha_seleccionada = date.fromisoformat(fecha_seleccionada_str)

        informe_diario, created = InformeDiario.objects.get_or_create(
            fecha=fecha_seleccionada, 
            turno=turno_seleccionado
        )

        if action == 'guardar_lideres':
            lider_id = request.POST.get('lider_tirreno')
            jefe_id = request.POST.get('jefe_mandante')
            
            informe_diario.lider_tirreno_id = lider_id if lider_id else None
            informe_diario.jefe_mandante_id = jefe_id if jefe_id else None
            informe_diario.save()
            messages.success(request, "Líderes de turno guardados con éxito.")

        elif action == 'guardar_produccion':
            ids_equipos = Maquinaria.objects.filter(
                tipo__in=['Cargador Frontal', 'Excavadora', 'Motoniveladora', 'Camión Tolva', 'Camión Aljibe']
            ).values_list('id', flat=True)

            for equipo_id in ids_equipos:
                datos_a_guardar = {}
                
                observacion_key = f'observaciones_{equipo_id}'
                if observacion_key in request.POST:
                    datos_a_guardar['observaciones'] = request.POST[observacion_key]

                tipos_material = ['cemento', 'normal', '6_15', '15_50', 'bitumix', 'fino', 'carga_buzon', 'otro']
                datos_despacho = {}
                datos_remanejo = {}
                if f'despacho_{equipo_id}_cemento' in request.POST:
                    for material in tipos_material:
                        valor_despacho = request.POST.get(f'despacho_{equipo_id}_{material}', '')
                        valor_remanejo = request.POST.get(f'remanejo_{equipo_id}_{material}', '')
                        if valor_despacho: datos_despacho[material] = valor_despacho
                        if valor_remanejo: datos_remanejo[material] = valor_remanejo
                if datos_despacho: datos_a_guardar['datos_despacho_fabrica'] = datos_despacho
                if datos_remanejo: datos_a_guardar['datos_remanejo_apoyo'] = datos_remanejo
                
                datos_tolva = {}
                if f'tolva_{equipo_id}_campo_1' in request.POST:
                    for i in range(1, 11):
                        valor = request.POST.get(f'tolva_{equipo_id}_campo_{i}', '')
                        if valor: datos_tolva[f'campo_{i}'] = valor
                if datos_tolva: datos_a_guardar['datos_camion_tolva'] = datos_tolva

                datos_aljibe = {}
                if f'aljibe_{equipo_id}_viaje_1' in request.POST:
                    for i in range(1, 5):
                        valor = request.POST.get(f'aljibe_{equipo_id}_viaje_{i}', '')
                        if valor: datos_aljibe[f'viaje_{i}'] = valor
                if datos_aljibe: datos_a_guardar['datos_camion_aljibe'] = datos_aljibe

                if datos_a_guardar:
                    ProduccionEquipo.objects.update_or_create(
                        informe=informe_diario,
                        maquinaria_id=equipo_id,
                        defaults=datos_a_guardar
                    )
            
            messages.success(request, "¡Informe de producción guardado con éxito!")

    if fecha_seleccionada is None:
        fecha_seleccionada = timezone.localdate()
        turno_seleccionado = 'Día'
    
    informe_diario, created = InformeDiario.objects.get_or_create(
        fecha=fecha_seleccionada,
        turno=turno_seleccionado
    )
    
    active_equipment_ids = Movimiento.objects.filter(
        fecha=fecha_seleccionada, 
        turno=turno_seleccionado
    ).values_list('maquinaria_id', flat=True).distinct()
    
    datos_movimientos = Movimiento.objects.filter(id__in=active_equipment_ids).values('maquinaria_id').annotate(
        hora_inicio=Min('horometro_inicial'), hora_termino=Max('horometro_final'),
        total_horas=Sum('horas_trabajadas'), total_combustible=Sum('combustible_cargado')
    )
    datos_agregados = {item['maquinaria_id']: item for item in datos_movimientos}

    datos_produccion_guardados = ProduccionEquipo.objects.filter(informe=informe_diario)
    datos_produccion_map = {item.maquinaria_id: item for item in datos_produccion_guardados}
    
    equipos_pesados = Maquinaria.objects.filter(id__in=active_equipment_ids, tipo__in=['Cargador Frontal', 'Excavadora', 'Motoniveladora']).order_by('tipo', 'codigo_eq')
    camiones_tolva = Maquinaria.objects.filter(id__in=active_equipment_ids, tipo='Camión Tolva').order_by('codigo_eq')
    camiones_aljibe = Maquinaria.objects.filter(id__in=active_equipment_ids, tipo='Camión Aljibe').order_by('codigo_eq')
    
    todos_los_equipos = list(equipos_pesados) + list(camiones_tolva) + list(camiones_aljibe)
    for equipo in todos_los_equipos:
        equipo.datos_reporte = datos_agregados.get(equipo.id)
        equipo.datos_produccion = datos_produccion_map.get(equipo.id)
        datos_guardados = equipo.datos_produccion if equipo.datos_produccion else {}
        if equipo.tipo == 'Camión Tolva':
            equipo.lista_datos_tolva = []
            datos_json = getattr(datos_guardados, 'datos_camion_tolva', {}) or {}
            for i in range(1, 11):
                equipo.lista_datos_tolva.append({'id': i, 'valor': datos_json.get(f'campo_{i}', '')})
        if equipo.tipo == 'Camión Aljibe':
            equipo.lista_datos_aljibe = []
            datos_json = getattr(datos_guardados, 'datos_camion_aljibe', {}) or {}
            for i in range(1, 5):
                equipo.lista_datos_aljibe.append({'id': i, 'valor': datos_json.get(f'viaje_{i}', '')})

    lideres_tirreno = Supervisor.objects.filter(empresa='Tirreno').order_by('nombre_completo')
    jefes_mandante = Supervisor.objects.filter(empresa='Mandante').order_by('nombre_completo')

    contexto = {
        'titulo': f"Informe de Producción - {turno_seleccionado} {fecha_seleccionada.strftime('%d-%m-%Y')}",
        'equipos_pesados': equipos_pesados,
        'camiones_tolva': camiones_tolva,
        'camiones_aljibe': camiones_aljibe,
        'fecha_seleccionada': fecha_seleccionada.isoformat(),
        'turno_seleccionado': turno_seleccionado,
        'opciones_turno': Movimiento.TURNOS,
        'informe_diario': informe_diario,
        'lideres_tirreno': lideres_tirreno,
        'jefes_mandante': jefes_mandante,
    }
    
    return render(request, 'empresa/informe_produccion.html', contexto)

def generar_informe_pdf(request, fecha, turno):
    """
    Genera una versión en PDF del Informe de Producción Diario
    para una fecha y turno específicos.
    """
    fecha_seleccionada = date.fromisoformat(fecha)
    turno_seleccionado = turno

    # --- RECOPILACIÓN DE DATOS ---
    informe_diario, _ = InformeDiario.objects.get_or_create(
        fecha=fecha_seleccionada, 
        turno=turno_seleccionado
    )
    
    active_equipment_ids = Movimiento.objects.filter(
        fecha=fecha_seleccionada, 
        turno=turno_seleccionado
    ).values_list('maquinaria_id', flat=True).distinct()
    
    datos_movimientos = Movimiento.objects.filter(
        fecha=fecha_seleccionada, turno=turno_seleccionado
    ).values('maquinaria_id').annotate(
        hora_inicio=Min('horometro_inicial'), hora_termino=Max('horometro_final'),
        total_horas=Sum('horas_trabajadas'), total_combustible=Sum('combustible_cargado')
    )
    datos_agregados = {item['maquinaria_id']: item for item in datos_movimientos}

    datos_produccion_guardados = ProduccionEquipo.objects.filter(informe=informe_diario)
    datos_produccion_map = {item.maquinaria_id: item for item in datos_produccion_guardados}
    
    equipos_pesados = Maquinaria.objects.filter(id__in=active_equipment_ids, tipo__in=['Cargador Frontal', 'Excavadora', 'Motoniveladora']).order_by('tipo', 'codigo_eq')
    camiones_tolva = Maquinaria.objects.filter(id__in=active_equipment_ids, tipo='Camión Tolva').order_by('codigo_eq')
    camiones_aljibe = Maquinaria.objects.filter(id__in=active_equipment_ids, tipo='Camión Aljibe').order_by('codigo_eq')
    
    todos_los_equipos = list(equipos_pesados) + list(camiones_tolva) + list(camiones_aljibe)
    for equipo in todos_los_equipos:
        equipo.datos_reporte = datos_agregados.get(equipo.id)
        equipo.datos_produccion = datos_produccion_map.get(equipo.id)
        datos_guardados = equipo.datos_produccion if equipo.datos_produccion else {}
        if equipo.tipo == 'Camión Tolva':
            equipo.lista_datos_tolva = []
            datos_json = getattr(datos_guardados, 'datos_camion_tolva', {}) or {}
            for i in range(1, 11):
                equipo.lista_datos_tolva.append({'id': i, 'valor': datos_json.get(f'campo_{i}', '')})
        if equipo.tipo == 'Camión Aljibe':
            equipo.lista_datos_aljibe = []
            datos_json = getattr(datos_guardados, 'datos_camion_aljibe', {}) or {}
            for i in range(1, 5):
                equipo.lista_datos_aljibe.append({'id': i, 'valor': datos_json.get(f'viaje_{i}', '')})

    contexto = {
        'titulo': f"Informe de Producción - {turno_seleccionado} {fecha_seleccionada.strftime('%d-%m-%Y')}",
        'equipos_pesados': equipos_pesados,
        'camiones_tolva': camiones_tolva,
        'camiones_aljibe': camiones_aljibe,
        'informe_diario': informe_diario,
    }

    # --- GENERACIÓN DEL PDF ---
    template_path = 'empresa/informe_produccion_pdf.html'
    template = get_template(template_path)
    html = template.render(contexto)
    
    # Usamos base_url para que WeasyPrint pueda encontrar archivos estáticos si los hubiera
    pdf_file = HTML(string=html, base_url=request.build_absolute_uri()).write_pdf()
    
    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"informe_produccion_{fecha}_{turno}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

def definir_posturas(request):
    PosturaFormSet = formset_factory(PosturaForm, extra=1, can_delete=True)

    # --- Lógica para POST (cuando se guarda el formulario) ---
    if request.method == 'POST':
        fecha_seleccionada_str = request.POST.get('fecha')
        turno_seleccionado = request.POST.get('turno')
        fecha_seleccionada = date.fromisoformat(fecha_seleccionada_str)

        informe_diario, _ = InformeDiario.objects.get_or_create(
            fecha=fecha_seleccionada,
            turno=turno_seleccionado
        )
        
        formset = PosturaFormSet(request.POST, prefix='posturas')

        if formset.is_valid():
            # Borramos las posturas anteriores para reemplazarlas con las nuevas
            Postura.objects.filter(informe=informe_diario).delete()
            
            numero_postura = 1
            for form in formset:
                # Solo procesamos el formulario si ha cambiado y no está marcado para borrar
                if form.has_changed() and not form.cleaned_data.get('DELETE', False):
                    # Creamos la nueva postura con los datos limpios del formulario
                    Postura.objects.create(
                        informe=informe_diario,
                        numero_postura=numero_postura,
                        tipo_actividad=form.cleaned_data.get('tipo_actividad'),
                        origen=form.cleaned_data.get('origen'),
                        sector_prefijo=form.cleaned_data.get('sector_prefijo'),
                        sector_banco=form.cleaned_data.get('sector_banco'),
                        sector_tiro=form.cleaned_data.get('sector_tiro'),
                        destino=form.cleaned_data.get('destino'),
                        material=form.cleaned_data.get('material')
                    )
                    numero_postura += 1
            
            messages.success(request, f"Posturas para el turno del {fecha_seleccionada_str} guardadas con éxito.")
            return redirect(f"{request.path}?fecha={fecha_seleccionada_str}&turno={turno_seleccionado}")
        else:
            # Si el formset NO es válido, mostramos un error
            messages.error(request, "Error al guardar. Por favor, revisa los campos marcados en rojo.")

    # --- Lógica para GET (cuando se carga la página) ---
    else:
        fecha_get = request.GET.get('fecha')
        turno_get = request.GET.get('turno')

        if fecha_get and turno_get:
            fecha_seleccionada = date.fromisoformat(fecha_get)
            turno_seleccionado = turno_get
            try:
                informe_existente = InformeDiario.objects.get(fecha=fecha_seleccionada, turno=turno_seleccionado)
                posturas_existentes = Postura.objects.filter(informe=informe_existente).order_by('numero_postura').values()
                
                # Si hay posturas, las cargamos. Si no, mostramos un formset vacío.
                if posturas_existentes.exists():
                    formset = PosturaFormSet(initial=list(posturas_existentes), prefix='posturas')
                else:
                    # Creamos una fila extra vacía si no hay datos
                    PosturaFormSet = formset_factory(PosturaForm, extra=1, can_delete=True)
                    formset = PosturaFormSet(prefix='posturas')

            except InformeDiario.DoesNotExist:
                formset = PosturaFormSet(prefix='posturas')
        else:
            fecha_seleccionada = timezone.localdate()
            turno_seleccionado = 'Día'
            formset = PosturaFormSet(prefix='posturas')

    contexto = {
        'titulo': 'Definir Posturas del Turno',
        'formset': formset,
        'fecha_seleccionada': fecha_seleccionada.isoformat(),
        'turno_seleccionado': turno_seleccionado,
        'opciones_turno': Movimiento.TURNOS,
    }
    return render(request, 'empresa/definir_posturas.html', contexto)