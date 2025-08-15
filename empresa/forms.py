# empresa/forms.py

from django import forms
from decimal import Decimal
from datetime import date
from .models import Movimiento, Postura, Viaje

class MovimientoCompletoForm(forms.ModelForm):
    # Todos los campos de los dos formularios anteriores, combinados
    class Meta:
        model = Movimiento
        fields = [
            'fecha', 'empleado', 'maquinaria', 'turno', 
            'descripcion_trabajo_especial', 'horometro_inicial',
            'horometro_final', 'horas_trabajadas',
            'proyecto', 'combustible_cargado', 'origen_combustible', 
            'detalle_chip_otro_equipo', 'nivel_inicial_combustible', 
            'nivel_final_combustible', 'observaciones'
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'descripcion_trabajo_especial': forms.Textarea(attrs={'rows': 2}),
            'empleado': forms.HiddenInput(),
            'horometro_final': forms.NumberInput(attrs={'min': 0}),
            'horas_trabajadas': forms.NumberInput(attrs={'readonly': True, 'step': '0.01'}),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Combinación de la lógica de __init__ de ambos formularios
        self.fields['horometro_final'].required = False
        self.fields['horas_trabajadas'].required = False
        self.fields['nivel_inicial_combustible'].disabled = True
        self.fields['nivel_inicial_combustible'].required = False
        self.fields['nivel_final_combustible'].required = True
        self.fields['nivel_final_combustible'].empty_label = "Seleccione un nivel"

    def clean(self):
        cleaned_data = super().clean()
        h_inicial = cleaned_data.get("horometro_inicial")
        h_final = cleaned_data.get("horometro_final")
        
        # Lógica de validación de horómetros
        if h_final is not None and h_final != '':
            try:
                h_final_int = int(h_final)
                h_inicial_int = int(h_inicial) if h_inicial else 0
                if h_final_int <= h_inicial_int:
                    self.add_error('horometro_final', "El horómetro final debe ser mayor que el inicial.")
                if (h_final_int - h_inicial_int) > 12 * 60:
                    self.add_error('horometro_final', "La diferencia no puede ser mayor a 12 horas.")
                cleaned_data['horas_trabajadas'] = round((h_final_int - h_inicial_int) / 60, 2)
            except (ValueError, TypeError):
                self.add_error('horometro_final', "Ingrese un valor numérico válido.")

        # Lógica de validación de combustible
        combustible = cleaned_data.get('combustible_cargado')
        origen = cleaned_data.get('origen_combustible')
        detalle_chip = cleaned_data.get('detalle_chip_otro_equipo')
        if combustible and not origen:
            self.add_error('origen_combustible', 'Si ingresó combustible, debe especificar el origen.')
        if origen == 'Estación Copec con Chip de otro Equipo' and not detalle_chip:
            self.add_error('detalle_chip_otro_equipo', 'Debe especificar de qué equipo usó el chip.')
            
        return cleaned_data

class PosturaForm(forms.ModelForm):
    class Meta:
        model = Postura
        fields = [
            'tipo_actividad', 'origen', 'sector_prefijo', 'sector_banco', 
            'sector_tiro', 'destino', 'material'
        ]
        labels = {
            'tipo_actividad': 'Actividad', 'origen': 'Origen',
            'sector_prefijo': 'Prefijo', 'sector_banco': 'Banco',
            'sector_tiro': 'Tiro', 'destino': 'Destino',
            'material': 'Material',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacemos que los campos del sector no sean requeridos por defecto a nivel de HTML.
        # Nuestra validación en clean() se encargará de la lógica.
        self.fields['sector_prefijo'].required = False
        self.fields['sector_banco'].required = False
        self.fields['sector_tiro'].required = False

        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if field_name in ['sector_prefijo', 'sector_banco', 'sector_tiro']:
                field.widget.attrs['placeholder'] = f"Ej: { {'sector_prefijo': 'TA', 'sector_banco': '610', 'sector_tiro': '23'}[field_name] }"
            if isinstance(field.widget, forms.Select):
                field.empty_label = "Seleccionar..."

    def clean(self):
        # Esta función contiene la lógica de validación personalizada.
        cleaned_data = super().clean()
        origen = cleaned_data.get('origen')
        
        # Los códigos de los lugares que consideramos "Mina"
        origenes_mina = ['TA', 'LA', 'LA_C', 'LA_E', 'LA_M']

        # Si el origen seleccionado es uno de la mina, entonces validamos los campos del sector.
        if origen in origenes_mina:
            if not cleaned_data.get('sector_prefijo'):
                self.add_error('sector_prefijo', 'Este campo es obligatorio para orígenes de mina.')
            if not cleaned_data.get('sector_banco'):
                self.add_error('sector_banco', 'Este campo es obligatorio para orígenes de mina.')
            if not cleaned_data.get('sector_tiro'):
                self.add_error('sector_tiro', 'Este campo es obligatorio para orígenes de mina.')

        return cleaned_data
    
class ViajeForm(forms.ModelForm):
    class Meta:
        model = Viaje
        fields = ['postura', 'cantidad']
        widgets = {
            'postura': forms.HiddenInput(), # El ID de la postura estará oculto
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'value': '0'}),
        }

    # Este campo nos servirá para mostrar la descripción de la postura en la plantilla
    postura_descripcion = forms.CharField(
        label="Postura",
        required=False,
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control-plaintext'})
    )