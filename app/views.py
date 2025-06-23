
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db import models
from .models import Obra, ConfiguracionGlobal
from .forms import ObraForm, ConfiguracionForm
import json
from datetime import datetime, timedelta, date

def limpiar_sistema():
    """Función auxiliar que limpia obras pasadas antes de cualquier operación"""
    config = ConfiguracionGlobal.get_configuracion()
    config.limpiar_obras_pasadas()

def index(request):
    """Vista principal con calendario"""
    # Limpiar obras pasadas automáticamente
    limpiar_sistema()
    
    config = ConfiguracionGlobal.get_configuracion()
    obras = Obra.objects.all().order_by('orden')
    
    # Datos para el calendario
    eventos_calendario = []
    total_obras = obras.count()
    
    for obra in obras:
        if obra.fecha_inicio and obra.fecha_fin:
            eventos_obra = crear_eventos_laborables(obra, config)
            eventos_calendario.extend(eventos_obra)
    
    context = {
        'eventos': json.dumps(eventos_calendario),
        'total_obras': total_obras,
    }
    return render(request, 'app/index.html', context)

def crear_eventos_laborables(obra, config):
    """Crea eventos separados para cada período laboral (excluyendo fines de semana)"""
    eventos = []
    fecha_actual = obra.fecha_inicio
    
    # Color base y borde
    color_base = obra.color
    color_borde = ajustar_brillo_color(color_base, -0.15)
    
    while fecha_actual <= obra.fecha_fin:
        # Buscar el inicio de la semana laboral
        inicio_semana = fecha_actual
        while inicio_semana.weekday() >= 5:
            inicio_semana += timedelta(days=1)
            if inicio_semana > obra.fecha_fin:
                break
        
        if inicio_semana > obra.fecha_fin:
            break
            
        # Buscar el final de la semana laboral
        fin_semana = inicio_semana
        while fin_semana.weekday() < 5 and fin_semana <= obra.fecha_fin:
            fin_semana += timedelta(days=1)
        
        fin_semana -= timedelta(days=1)
        
        if inicio_semana <= fin_semana:
            eventos.append({
                'title': obra.nombre,
                'start': inicio_semana.isoformat(),
                'end': (fin_semana + timedelta(days=1)).isoformat(),
                'description': obra.descripcion or '',
                'horas_estimadas': obra.horas_estimadas,
                'dias_necesarios': round(obra.dias_necesarios(config.horas_por_dia), 1),
                'backgroundColor': color_base,
                'borderColor': color_borde,
                'textColor': calcular_color_texto(color_base)
            })
        
        fecha_actual = fin_semana + timedelta(days=1)
        while fecha_actual.weekday() >= 5:
            fecha_actual += timedelta(days=1)
    
    return eventos

def ajustar_brillo_color(hex_color, factor):
    """Ajusta el brillo de un color hex"""
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    new_rgb = []
    for component in rgb:
        new_component = int(component * (1 + factor))
        new_component = max(0, min(255, new_component))
        new_rgb.append(new_component)
    
    return f"#{new_rgb[0]:02x}{new_rgb[1]:02x}{new_rgb[2]:02x}"

def calcular_color_texto(hex_color):
    """Calcula si el texto debe ser blanco o negro"""
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    luminancia = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255
    return '#FFFFFF' if luminancia < 0.5 else '#000000'

def configuracion(request):
    """Vista de configuración ultra simplificada"""
    # Limpiar obras pasadas automáticamente
    limpiar_sistema()
    
    config = ConfiguracionGlobal.get_configuracion()
    obras = Obra.objects.all().order_by('orden')
    
    # Manejar formulario de configuración global
    if request.method == 'POST' and 'actualizar_config' in request.POST:
        config_form = ConfiguracionForm(request.POST, instance=config)
        if config_form.is_valid():
            config_anterior = config.horas_por_dia
            config_form.save()
            config_nuevo = config.horas_por_dia
            
            if config_anterior != config_nuevo:
                config.recalcular_todas_las_obras()
                messages.success(request, f'Configuración actualizada de {config_anterior}h a {config_nuevo}h por día. Fechas recalculadas.')
            else:
                messages.success(request, 'Configuración actualizada.')
            return redirect('app:configuracion')
        else:
            messages.error(request, 'Error en la configuración.')
    else:
        config_form = ConfiguracionForm(instance=config)
    
    # Manejar formulario de nueva obra
    if request.method == 'POST' and 'agregar_obra' in request.POST:
        obra_form = ObraForm(request.POST)
        if obra_form.is_valid():
            nueva_obra = obra_form.save(commit=False)
            ultimo_orden = Obra.objects.aggregate(models.Max('orden'))['orden__max'] or 0
            nueva_obra.orden = ultimo_orden + 1
            nueva_obra.save()
            config.recalcular_todas_las_obras()
            messages.success(request, f'Obra "{nueva_obra.nombre}" agregada al final.')
            return redirect('app:configuracion')
        else:
            messages.error(request, 'Error al crear la obra.')
    else:
        obra_form = ObraForm()
    
    # Manejar formulario de editar obra
    if request.method == 'POST' and 'editar_obra' in request.POST:
        obra_id = request.POST.get('obra_id')
        if not obra_id:
            messages.error(request, 'ID de obra no válido.')
            return redirect('app:configuracion')
            
        try:
            obra = get_object_or_404(Obra, id=obra_id)
            
            nombre = request.POST.get('nombre', '').strip()
            horas_estimadas_str = request.POST.get('horas_estimadas', '0')
            color = request.POST.get('color', '#007bff')
            descripcion = request.POST.get('descripcion', '').strip()
            
            if not nombre:
                messages.error(request, 'El nombre de la obra es requerido.')
                return redirect('app:configuracion')
            
            try:
                horas_estimadas = int(horas_estimadas_str)
                if horas_estimadas <= 0:
                    raise ValueError("Las horas estimadas deben ser positivas")
            except (ValueError, TypeError):
                messages.error(request, 'Las horas estimadas deben ser un número válido.')
                return redirect('app:configuracion')
            
            # Actualizar campos
            obra.nombre = nombre
            obra.descripcion = descripcion
            obra.horas_estimadas = horas_estimadas
            obra.color = color
            obra.save()
            
            # Recalcular fechas
            config.recalcular_todas_las_obras()
            messages.success(request, f'Obra "{obra.nombre}" actualizada. Fechas recalculadas.')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar la obra: {str(e)}')
        
        return redirect('app:configuracion')
    
    context = {
        'config': config,
        'config_form': config_form,
        'obras': obras,
        'obra_form': obra_form,
    }
    return render(request, 'app/configuracion.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def actualizar_orden_obras(request):
    """API para actualizar el orden de las obras via drag & drop"""
    try:
        # Limpiar obras pasadas automáticamente
        limpiar_sistema()
        
        data = json.loads(request.body)
        orden_obras = data.get('orden_obras', [])
        
        if not orden_obras:
            return JsonResponse({'success': False, 'error': 'No se proporcionó ningún orden de obras'})
        
        # Actualizar el orden de cada obra
        for index, obra_id in enumerate(orden_obras):
            try:
                obra_id_int = int(obra_id)
                Obra.objects.filter(id=obra_id_int).update(orden=index + 1)
            except (ValueError, TypeError):
                return JsonResponse({'success': False, 'error': f'ID de obra inválido: {obra_id}'})
        
        # Recalcular fechas tras cambio de orden
        config = ConfiguracionGlobal.get_configuracion()
        config.recalcular_todas_las_obras()
        
        return JsonResponse({'success': True, 'message': 'Orden actualizado y fechas recalculadas'})
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Datos JSON inválidos'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error interno: {str(e)}'})

def eliminar_obra(request, obra_id):
    """Eliminar una obra y recalcular"""
    try:
        # Limpiar obras pasadas automáticamente
        limpiar_sistema()
        
        obra = get_object_or_404(Obra, id=obra_id)
        nombre_obra = obra.nombre
        
        obra.delete()
        
        # Recalcular tras eliminar
        config = ConfiguracionGlobal.get_configuracion()
        config.recalcular_todas_las_obras()
        messages.success(request, f'Obra "{nombre_obra}" eliminada. Fechas recalculadas.')
    
    except Exception as e:
        messages.error(request, f'Error al eliminar la obra: {str(e)}')
    
    return redirect('app:configuracion')