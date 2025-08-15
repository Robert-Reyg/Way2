# empresa/models.py

from django.db import models

class Cliente(models.Model):
    nombre = models.CharField(max_length=200, help_text="Nombre de la empresa o persona cliente")
    rut = models.CharField(max_length=12, unique=True, help_text="RUT del cliente (ej: 76.123.456-7)")
    direccion = models.CharField(max_length=255, blank=True, null=True, help_text="Dirección física del cliente")
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True, help_text="Correo electrónico de contacto")

    def __str__(self):
        return self.nombre

class Maquinaria(models.Model):
    codigo_eq = models.CharField(max_length=20, unique=True, default='SIN-CODIGO')
    marca = models.CharField(max_length=50, default='SIN-MARCA')
    modelo = models.CharField(max_length=50, default='SIN-MODELO')
    tipo = models.CharField(max_length=50, help_text="Ej: Excavadora, Cargador Frontal", default='SIN-TIPO')
    patente = models.CharField(max_length=10, blank=True, null=True)
    horometro_actual = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.codigo_eq} ({self.marca} {self.modelo})"

class TipoLicencia(models.Model):
    nombre = models.CharField(max_length=50, unique=True) # Ej: "Clase B", "Clase D"

    def __str__(self):
        return self.nombre

class Empleado(models.Model):
    TIPOS_CONTRATO = [('Indefinido', 'Indefinido'), ('Plazo Fijo', 'Plazo Fijo')]
    CARGOS = [
        ('Administrativo', 'Administrativo'), ('Jefe de Turno', 'Jefe de Turno'),
        ('Supervisor', 'Supervisor'), ('Operador Camión Tolva', 'Operador Camión Tolva'),
        ('Operador Maquinaria', 'Operador Maquinaria'), ('Operador Multiservicio', 'Operador Multiservicio'),
        ('Operador Mantenedor', 'Operador Mantenedor'), ('Mantenedor', 'Mantenedor'),
    ]
    codigo_trabajador = models.CharField(max_length=4, unique=True, default='0000')
    nombre_completo = models.CharField(max_length=255)
    rut = models.CharField(max_length=12, unique=True)
    cargo = models.CharField(max_length=100, choices=CARGOS)
    tipo_contrato = models.CharField(max_length=20, choices=TIPOS_CONTRATO)
    fecha_contratacion = models.DateField()
    fecha_termino_contrato = models.DateField(null=True, blank=True)
    licencias = models.ManyToManyField(TipoLicencia, blank=True)
    fecha_vencimiento_licencia = models.DateField(null=True, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.nombre_completo

class Proyecto(models.Model):
    nombre = models.CharField(max_length=200, help_text="Nombre de la obra o proyecto")
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    ubicacion = models.CharField(max_length=255)
    fecha_inicio = models.DateField()
    fecha_termino = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.nombre

NIVEL_COMBUSTIBLE_CHOICES = [
    ('vacio', 'Vacío'), ('alarma', 'Alarma Nivel Bajo'), ('un_cuarto', '1/4 Estanque'),
    ('medio', '1/2 Estanque'), ('tres_cuartos', '3/4 Estanque'), ('full', 'Estanque Full'),
]

class Movimiento(models.Model):
    PROYECTOS = [
        ('Mina El Way', 'Mina El Way'), ('Mina Juana', 'Mina Juana'),
        ('Mina Paty', 'Mina Paty'), ('CBB Fábrica', 'CBB Fábrica'),
    ]
    TURNOS = [('Día', 'Turno Día'), ('Noche', 'Turno Noche'), ('Horas Extras', 'Horas Extras'), ('Trabajo Especial', 'Trabajo Especial')]
    ORIGENES_COMBUSTIBLE = [
        ('Estación Copec con Chip del Equipo', 'Estación Copec con Chip del Equipo'),
        ('Estación Copec con Chip de otro Equipo', 'Estación Copec con Chip de otro Equipo'),
        ('Con Camión Combustible', 'Con Camión Combustible'), ('Carga Manual Con Bidones', 'Carga Manual Con Bidones'),
    ]
    fecha = models.DateField()
    empleado = models.ForeignKey(Empleado, on_delete=models.SET_NULL, null=True)
    maquinaria = models.ForeignKey(Maquinaria, on_delete=models.SET_NULL, null=True)
    proyecto = models.CharField(max_length=50, choices=PROYECTOS, default='Mina El Way')
    horometro_inicial = models.PositiveIntegerField()
    horometro_final = models.PositiveIntegerField(null=True, blank=True)
    horas_trabajadas = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    turno = models.CharField(max_length=20, choices=TURNOS, default='Día')
    descripcion_trabajo_especial = models.CharField(max_length=500, blank=True, null=True)
    combustible_cargado = models.DecimalField(max_digits=6, decimal_places=2, help_text="Litros de combustible", null=True, blank=True)
    origen_combustible = models.CharField(max_length=100, choices=ORIGENES_COMBUSTIBLE, null=True, blank=True)
    detalle_chip_otro_equipo = models.CharField(max_length=100, null=True, blank=True, help_text="Especifique el código o patente del otro equipo")
    nivel_inicial_combustible = models.CharField(max_length=50, choices=NIVEL_COMBUSTIBLE_CHOICES, null=True, blank=True)
    nivel_final_combustible = models.CharField(max_length=50, choices=NIVEL_COMBUSTIBLE_CHOICES, default='vacio')
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        fecha_str = self.fecha.strftime('%d-%m-%Y') if self.fecha else 'Sin Fecha'
        return f"Movimiento del {fecha_str} - {self.empleado}"


# --- NUEVOS MODELOS PARA EL INFORME DE PRODUCCIÓN Y POSTURAS ---

class Supervisor(models.Model):
    EMPRESA_CHOICES = [('Tirreno', 'Tirreno'), ('Mandante', 'Empresa Mandante')]
    nombre_completo = models.CharField(max_length=255, unique=True)
    empresa = models.CharField(max_length=20, choices=EMPRESA_CHOICES)
    def __str__(self):
        return f"{self.nombre_completo} ({self.empresa})"

class InformeDiario(models.Model):
    fecha = models.DateField()
    turno = models.CharField(max_length=20, choices=Movimiento.TURNOS)
    lider_tirreno = models.ForeignKey(Supervisor, on_delete=models.SET_NULL, null=True, blank=True, related_name='informes_como_lider')
    jefe_mandante = models.ForeignKey(Supervisor, on_delete=models.SET_NULL, null=True, blank=True, related_name='informes_como_jefe')
    class Meta:
        unique_together = ('fecha', 'turno')
    def __str__(self):
        return f"Informe del {self.fecha.strftime('%d-%m-%Y')} - Turno {self.turno}"

class ProduccionEquipo(models.Model):
    informe = models.ForeignKey(InformeDiario, on_delete=models.CASCADE, related_name='produccion_equipos', null=True)
    maquinaria = models.ForeignKey(Maquinaria, on_delete=models.CASCADE)
    datos_despacho_fabrica = models.JSONField(null=True, blank=True, default=dict)
    datos_remanejo_apoyo = models.JSONField(null=True, blank=True, default=dict)
    datos_camion_tolva = models.JSONField(null=True, blank=True, default=dict)
    datos_camion_aljibe = models.JSONField(null=True, blank=True, default=dict)
    observaciones = models.TextField(blank=True, null=True)
    class Meta:
        unique_together = ('informe', 'maquinaria')
    def __str__(self):
        return f"Producción de {self.maquinaria.codigo_eq} para {self.informe}"

# --- NUEVOS MODELOS PARA LAS POSTURAS (DEBEN ESTAR AL FINAL) ---

class Lugar(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=10)
    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

class Material(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.nombre

class Postura(models.Model):
    ACTIVIDAD_CHOICES = [
        ('Producción', 'Producción'), ('Confinamiento', 'Confinamiento'),
        ('Remanejo', 'Remanejo'), ('Arriendo', 'Arriendo'),
        ('Despacho', 'Despacho'), ('Limpieza', 'Limpieza'),
        ('Apoyo Mina', 'Apoyo Mina'),
    ]

    LUGAR_CHOICES = [
        ('TA', 'Mina Sector Tableado (TA)'), ('LA', 'Mina Sector Lagarto (LA)'),
        ('LA_C', 'Mina Sector Lagarto/Cedro (LA)'), ('LA_E', 'Mina Sector Lagarto/Camino Emergencia (LA)'),
        ('LA_M', 'Mina Sector Mastodonte (LA)'), ('PCH', 'Planta Chancado (PCH)'),
        ('BA', 'Buzón Alimentación (BA)'), ('BF', 'Buzón de Fino (BF)'),
        ('BTN', 'Botadero Norte (BTN)'), ('BTS', 'Botadero Sur (BTS)'), # <-- Corregí el duplicado
        ('BE', 'Botadero Ecometales (BE)'), ('CS', 'Canchas de Stock (CS)'),
        ('CBBF', 'Fábrica (CBBF)'),
    ]

    MATERIAL_CHOICES = [
        ('Cal Alta Ley', 'Cal tronada Alta Ley'), ('Cal Normal', 'Cal tronada Normal'),
        ('Cal Cemento', 'Cal tronada Cemento o Baja Ley'), ('Fino', 'Fino'),
        ('Fino Ecometales', 'Fino Ecometales'), ('Fino Bitumix', 'Fino Bitumix'),
        ('Estéril', 'Estéril'), ('Descarte', 'Materiales de Descarte'),
        ('Cal 15-50 AL', 'Cal 15-50 mm Alta Ley'), ('Cal 15-50 N', 'Cal 15-50 mm Normal'),
        ('Cal 6-15 AL', 'Cal 6-15 mm Alta Ley'), ('Cal 6-15 N', 'Cal 6-15 mm Normal'),
        ('Cemento', 'Cemento'),
    ]

    informe = models.ForeignKey(InformeDiario, on_delete=models.CASCADE, related_name="posturas")
    numero_postura = models.PositiveIntegerField()
    tipo_actividad = models.CharField(max_length=50, choices=ACTIVIDAD_CHOICES)

    # --- CAMPOS MODIFICADOS ---
    origen = models.CharField(max_length=50, choices=LUGAR_CHOICES, default='TA')
    sector_prefijo = models.CharField(max_length=10, help_text="Ej: TA, LA")
    sector_banco = models.CharField(max_length=10, help_text="Ej: 610")
    sector_tiro = models.CharField(max_length=10, help_text="Ej: 23")
    destino = models.CharField(max_length=50, choices=LUGAR_CHOICES, default='PCH')
    material = models.CharField(max_length=50, choices=MATERIAL_CHOICES, default='Estéril')

    class Meta:
        ordering = ['informe', 'numero_postura']
        unique_together = ('informe', 'numero_postura')

    def __str__(self):
        return f"Postura #{self.numero_postura} para {self.informe}"

class Viaje(models.Model):
    """
    Representa la cantidad de viajes que un operador realiza
    para una postura específica dentro de su movimiento diario.
    """
    movimiento = models.ForeignKey(Movimiento, on_delete=models.CASCADE, related_name='viajes')
    postura = models.ForeignKey(Postura, on_delete=models.CASCADE, related_name='viajes_realizados')
    cantidad = models.PositiveIntegerField(default=0)

    class Meta:
        # Asegura que no se pueda registrar más de una vez la misma postura para el mismo movimiento
        unique_together = ('movimiento', 'postura')

    def __str__(self):
        return f"{self.cantidad} viajes para {self.postura} en mov. #{self.movimiento.id}"