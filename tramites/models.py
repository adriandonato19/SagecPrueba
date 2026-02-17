from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid
import json

class Tramite(models.Model):
    # Definición de Estados
    BORRADOR = 'BORRADOR'       # El usuario consultó pero no ha enviado a aprobar
    PENDIENTE = 'PENDIENTE'     # Enviado para revisión del Trabajador/Director
    APROBADO = 'APROBADO'       # Validado por un Trabajador, listo para firma del Director
    FIRMADO = 'FIRMADO'         # El Director ya subió el documento con firma digital
    RECHAZADO = 'RECHAZADO'     # La solicitud fue denegada por datos incorrectos

    ESTADOS_CHOICES = [
        (BORRADOR, 'Borrador'),
        (PENDIENTE, 'Pendiente de Revisión'),
        (APROBADO, 'Aprobado para Firma'),
        (FIRMADO, 'Firmado y Finalizado'),
        (RECHAZADO, 'Rechazado'),
    ]

    # Campos principales
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    tipo_documento = models.CharField(max_length=20, choices=[('OFICIO', 'Oficio'), ('CERTIFICADO', 'Certificado')])
    estado = models.CharField(max_length=20, choices=ESTADOS_CHOICES, default=BORRADOR)
    numero_referencia = models.CharField(max_length=50, blank=True, help_text="Número de referencia humano-legible")
    
    # Datos de la empresa (snapshot inmutable)
    empresa_snapshot = models.JSONField(default=dict, help_text="Snapshot de datos de la empresa al momento de creación")
    origen_consulta = models.CharField(max_length=100, blank=True, help_text="RUC o número de aviso consultado")
    
    # Trazabilidad (Módulo 3 y 4 de la propuesta)
    solicitante = models.ForeignKey('identidad.UsuarioMICI', on_delete=models.PROTECT, related_name='solicitudes') 
    revisor = models.ForeignKey('identidad.UsuarioMICI', on_delete=models.SET_NULL, null=True, blank=True, related_name='revisiones') 
    firmante = models.ForeignKey('identidad.UsuarioMICI', on_delete=models.SET_NULL, null=True, blank=True, related_name='firmas') 
    
    # Campos adicionales para PDF y firma
    hash_seguridad = models.CharField(max_length=64, blank=True, help_text="SHA-256 del documento firmado")
    archivo_pdf = models.FileField(upload_to='pdfs/', null=True, blank=True, help_text="PDF original generado al crear el trámite")
    archivo_pdf_firmado = models.FileField(upload_to='pdfs/firmados/', null=True, blank=True, help_text="PDF firmado externamente y subido por el director")
    motivo_rechazo = models.TextField(blank=True, help_text="Motivo del rechazo si aplica")
    
    # Campo de pregunta adicional (opcional)
    pregunta_adicional = models.TextField(blank=True, help_text="Pregunta adicional del solicitante al crear el trámite")
    respuesta_pregunta = models.TextField(blank=True, help_text="Respuesta a la pregunta adicional, escrita por el revisor al aprobar")
    datos_qa = models.JSONField(default=dict, blank=True, help_text="Estructura QA para múltiples empresas: {id_empresa: {nombre, pregunta, respuesta}}")
        
    # Campos específicos para certificados oficiales
    destinatario = models.CharField(max_length=200, blank=True, help_text="Nombre del destinatario del documento (ej: Señor LUIS ABREGO)")
    proposito = models.TextField(blank=True, help_text="Propósito del trámite (ej: traspaso vehicular)")
    fecha_solicitud = models.DateField(null=True, blank=True, help_text="Fecha en que el MICI recibió la solicitud")
    
    # Campos para Oficios de Respuesta (Ministerio Público, Juzgados, etc.)
    oficio_entrante = models.CharField(max_length=100, blank=True, help_text="Número de Oficio entrante (ej: Oficio No. 478-2024)")
    carpetilla = models.CharField(max_length=100, blank=True, help_text="Número de Carpetilla (ej: 202300074865)")
    fecha_oficio_entrante = models.DateField(null=True, blank=True, help_text="Fecha del oficio entrante")
    fecha_recepcion = models.DateField(null=True, blank=True, help_text="Fecha de recepción en el despacho")
    solicitante_externo = models.CharField(max_length=200, blank=True, help_text="Nombre del funcionario solicitante externo (ej: Lic. Caren Cabeza)")
    cargo_solicitante = models.CharField(max_length=200, blank=True, help_text="Cargo del solicitante externo")
    institucion_solicitante = models.CharField(max_length=200, blank=True, help_text="Institución solicitante (ej: Ministerio Público)")

    # Timestamps
    fecha_creacion = models.DateTimeField(auto_now_add=True) 
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_revision = models.DateTimeField(null=True, blank=True)
    fecha_firma = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Trámite'
        verbose_name_plural = 'Trámites'
    
    def __str__(self):
        return f"{self.get_tipo_documento_display()} - {self.numero_referencia or str(self.uuid)[:8]}"
    
    def enviar(self):
        """Transición: BORRADOR -> PENDIENTE"""
        if self.estado != self.BORRADOR:
            raise ValidationError(f"No se puede enviar un trámite en estado {self.get_estado_display()}")
        self.estado = self.PENDIENTE
        self.fecha_envio = timezone.now()
        self.save()
    
    def aprobar(self, revisor):
        """Transición: PENDIENTE -> APROBADO"""
        if self.estado != self.PENDIENTE:
            raise ValidationError(f"No se puede aprobar un trámite en estado {self.get_estado_display()}")
        if not revisor.puede_aprobar:
            raise ValidationError("El usuario no tiene permisos para aprobar")
        self.estado = self.APROBADO
        self.revisor = revisor
        self.fecha_revision = timezone.now()
        self.save()
    
    def rechazar(self, revisor, motivo):
        """Transición: PENDIENTE -> RECHAZADO"""
        if self.estado != self.PENDIENTE:
            raise ValidationError(f"No se puede rechazar un trámite en estado {self.get_estado_display()}")
        if not revisor.puede_aprobar:
            raise ValidationError("El usuario no tiene permisos para rechazar")
        self.estado = self.RECHAZADO
        self.revisor = revisor
        self.motivo_rechazo = motivo
        self.fecha_revision = timezone.now()
        self.save()
    
    def marcar_firmado(self, firmante, hash_documento=None):
        """Transición: APROBADO -> FIRMADO
        
        Nota: El archivo_pdf_firmado debe ser guardado antes de llamar a este método
        usando tramite.archivo_pdf_firmado.save()
        """
        if self.estado != self.APROBADO:
            raise ValidationError(f"No se puede firmar un trámite en estado {self.get_estado_display()}")
        if not firmante.puede_firmar:
            raise ValidationError("El usuario no tiene permisos para firmar")
        self.estado = self.FIRMADO
        self.firmante = firmante
        self.fecha_firma = timezone.now()
        if hash_documento:
            self.hash_seguridad = hash_documento
        self.save()

    @property
    def nombre_solicitante_display(self):
        """Devuelve el nombre completo o username del solicitante de forma segura."""
        if not self.solicitante:
            return "N/A"
        return self.solicitante.get_full_name() or self.solicitante.username

    @property
    def nombre_revisor_display(self):
        """Devuelve el nombre completo o username del revisor de forma segura."""
        if not self.revisor:
            return "N/A"
        return self.revisor.get_full_name() or self.revisor.username

    @property
    def nombre_firmante_display(self):
        """Devuelve el nombre completo o username del firmante de forma segura."""
        if not self.firmante:
            return "N/A"
        return self.firmante.get_full_name() or self.firmante.username

    @property
    def es_multi_empresa(self):
        """Devuelve True si el snapshot es una lista de empresas."""
        return isinstance(self.empresa_snapshot, list)
        
    @property
    def empresa_principal(self):
        """Devuelve la empresa principal para mostrar datos generales con campos calculados."""
        empresa = {}
        if self.es_multi_empresa:
            empresa = self.empresa_snapshot[0] if self.empresa_snapshot else {}
        else:
            empresa = self.empresa_snapshot or {}
            
        # Calcular RUC para visualización (previene lógica compleja en templates)
        # Prioridad: ruc > cedula_representante > N/A
        ruc = empresa.get('ruc')
        cedula = empresa.get('cedula_representante')
        empresa['ruc_visualizar'] = ruc if ruc else (cedula if cedula else "N/A")
        
        return empresa
        
    @property
    def lista_empresas(self):
        """Devuelve siempre una lista iterable de empresas."""
        if self.es_multi_empresa:
            return self.empresa_snapshot
        return [self.empresa_snapshot]