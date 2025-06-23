from django import forms
from .models import Obra, ConfiguracionGlobal

class ConfiguracionForm(forms.ModelForm):
    """Formulario para configuración global - Solo horas por día"""
    class Meta:
        model = ConfiguracionGlobal
        fields = ['horas_por_dia']
        widgets = {
            'horas_por_dia': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'step': '1',
                'placeholder': 'Ej: 8'
            })
        }
        labels = {
            'horas_por_dia': 'Horas de trabajo por día'
        }
        help_texts = {
            'horas_por_dia': 'Total de horas que se trabajan por día (considerando todos los trabajadores)'
        }

class ObraForm(forms.ModelForm):
    """Formulario para crear obras - Sistema ultra simplificado"""
    class Meta:
        model = Obra
        fields = ['nombre', 'descripcion', 'horas_estimadas', 'color']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de la obra',
                'required': True
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción opcional de la obra'
            }),
            'horas_estimadas': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'step': '1',
                'placeholder': 'Ej: 120',
                'required': True
            }),
            'color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'style': 'height: 38px;',
                'title': 'Elige el color para esta obra'
            })
        }
        labels = {
            'nombre': 'Nombre de la obra',
            'descripcion': 'Descripción (opcional)',
            'horas_estimadas': 'Horas estimadas totales',
            'color': 'Color en el calendario'
        }
        help_texts = {
            'horas_estimadas': 'Total de horas que se estima tardará la obra completa',
            'color': 'Color que aparecerá en el calendario para identificar esta obra'
        }