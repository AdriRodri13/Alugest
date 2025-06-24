from django.db import models
from datetime import datetime, timedelta, date

class ConfiguracionGlobal(models.Model):
    """Configuración global del sistema - Solo horas por día"""
    horas_por_dia = models.IntegerField(
        default=8, 
        help_text="Horas de trabajo por día (considerando todos los trabajadores)"
    )
    
    class Meta:
        verbose_name = 'Configuración Global'
        verbose_name_plural = 'Configuración Global'
    
    def save(self, *args, **kwargs):
        # Solo permitir una instancia de configuración
        if not self.pk and ConfiguracionGlobal.objects.exists():
            raise ValueError('Solo puede existir una configuración global')
        super().save(*args, **kwargs)
    
    def limpiar_obras_pasadas(self):
        """Elimina automáticamente las obras que ya han pasado"""
        try:
            hoy = date.today()
            obras_pasadas = Obra.objects.filter(fecha_fin__lt=hoy)
            cantidad_eliminadas = obras_pasadas.count()
            
            if cantidad_eliminadas > 0:
                # Obtener nombres para log (opcional)
                nombres = list(obras_pasadas.values_list('nombre', flat=True))
                obras_pasadas.delete()
                print(f"Eliminadas {cantidad_eliminadas} obras pasadas: {', '.join(nombres)}")
                
                # Recalcular tras eliminar
                self.recalcular_todas_las_obras()
                
        except Exception as e:
            print(f"Error al limpiar obras pasadas: {e}")
    
    def recalcular_todas_las_obras(self):
        """Recalcula todas las obras, apilando varias por día según disponibilidad de horas"""
        try:
            hoy = date.today()
            obras = Obra.objects.all().order_by('orden')
            if not obras.exists():
                return

            horas_por_dia = self.horas_por_dia
            calendario = {}  # fecha -> horas_usadas
            fecha_actual = hoy

            # Preparar función para buscar el siguiente día laborable con espacio
            def siguiente_dia_laborable(fecha):
                while fecha.weekday() >= 5:
                    fecha += timedelta(days=1)
                return fecha

            fecha_actual = siguiente_dia_laborable(fecha_actual)

            for obra in obras:
                if obra.esta_siendo_trabajada_hoy():
                    fecha_actual = obra.fecha_fin + timedelta(days=1)
                    fecha_actual = siguiente_dia_laborable(fecha_actual)
                    continue

                horas_restantes = obra.horas_estimadas
                fechas_asignadas = []

                while horas_restantes > 0:
                    fecha_actual = siguiente_dia_laborable(fecha_actual)
                    horas_ocupadas = calendario.get(fecha_actual, 0)
                    horas_disponibles = horas_por_dia - horas_ocupadas

                    if horas_disponibles > 0:
                        horas_a_usar = min(horas_restantes, horas_disponibles)
                        calendario[fecha_actual] = horas_ocupadas + horas_a_usar
                        horas_restantes -= horas_a_usar
                        fechas_asignadas.append(fecha_actual)

                    if horas_restantes > 0:
                        fecha_actual += timedelta(days=1)

                if fechas_asignadas:
                    obra.fecha_inicio = fechas_asignadas[0]
                    obra.fecha_fin = fechas_asignadas[-1]
                    obra.save(update_fields=['fecha_inicio', 'fecha_fin'])

        except Exception as e:
            print(f"Error al recalcular obras: {e}")

    
    @classmethod
    def get_configuracion(cls):
        """Obtiene la configuración global, la crea si no existe"""
        config, created = cls.objects.get_or_create(defaults={'horas_por_dia': 8})
        return config

class Obra(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    horas_estimadas = models.IntegerField(help_text="Horas totales estimadas para completar la obra")
    color = models.CharField(
        max_length=7, 
        default='#007bff',
        help_text="Color para mostrar en el calendario (formato hex: #RRGGBB)"
    )
    orden = models.IntegerField(default=0, help_text="Orden de ejecución de las obras")
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['orden', 'creada_en']
        verbose_name = 'Obra'
        verbose_name_plural = 'Obras'

    def __str__(self):
        return f"{self.nombre} (#{self.orden})"

    def dias_necesarios(self, horas_por_dia):
        """Calcula los días necesarios para completar la obra"""
        if horas_por_dia > 0:
            return self.horas_estimadas / horas_por_dia
        return 0

    def esta_siendo_trabajada_hoy(self):
        """Determina si la obra se está trabajando HOY"""
        if not self.fecha_inicio or not self.fecha_fin:
            return False
        
        hoy = date.today()
        return self.fecha_inicio <= hoy <= self.fecha_fin

    def calcular_fechas(self, fecha_inicio_disponible, horas_por_dia):
        """Calcula las fechas de inicio y fin considerando solo días laborables"""
        if not fecha_inicio_disponible:
            return None, None
        
        # Buscar el primer día laborable para empezar
        fecha_inicio = fecha_inicio_disponible
        while fecha_inicio.weekday() >= 5:  # 5=sábado, 6=domingo
            fecha_inicio += timedelta(days=1)
        
        dias_necesarios = self.dias_necesarios(horas_por_dia)
        dias_completos = int(dias_necesarios)
        horas_restantes = (dias_necesarios - dias_completos) * horas_por_dia
        
        # Si hay horas restantes, necesitamos un día más
        if horas_restantes > 0:
            dias_completos += 1
        
        if dias_completos == 0:
            return fecha_inicio, fecha_inicio
        
        fecha_actual = fecha_inicio
        dias_trabajados = 0
        
        # Contar solo días laborables
        while dias_trabajados < dias_completos:
            if fecha_actual.weekday() < 5:  # Lunes a viernes
                dias_trabajados += 1
                if dias_trabajados < dias_completos:
                    fecha_actual += timedelta(days=1)
            else:
                fecha_actual += timedelta(days=1)
        
        return fecha_inicio, fecha_actual