"""
PDF Template for Formulario de Inscripción (Inscription Form)
This template generates a professional inscription form for concursos docentes.
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from datetime import datetime
import os
import io

class FormularioInscripcionTemplate:
    def __init__(self):
        self.width, self.height = A4
        self.margin = 1 * inch
        self.content_width = self.width - (2 * self.margin)
        
    def generate_pdf(self, concurso_data, placeholders):
        """
        Generate the inscription form PDF using concurso data and placeholders.
        
        Args:
            concurso_data (dict): Dictionary with concurso information including instructivo and required_docs
            placeholders (dict): Dictionary with resolved placeholders
            
        Returns:
            bytes: PDF content as bytes
        """
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        
        # Add header with logo
        self._add_header(c)
        
        # Add title
        self._add_title(c, placeholders)
        
        # Add concurso information section
        y_position = self._add_concurso_info(c, concurso_data, placeholders)
        
        # Check if we need a new page
        if y_position < 400:
            c.showPage()
            y_position = self.height - 80
        
        # Add personal data form section
        y_position = self._add_personal_data_form(c, y_position)
        
        # Add required documents section with dynamic data
        y_position = self._add_required_documents(c, y_position, concurso_data)
        
        # Add footer
        self._add_footer(c)
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    
    def _add_header(self, c):
        """Add header with UNCo Bariloche logo"""
        try:
            # Try to load the logo with transparency support - positioned on the right
            logo_path = os.path.join(os.path.dirname(__file__), '../../static/img/logo-unco-bariloche.png')
            if os.path.exists(logo_path):
                # Use mask='auto' to automatically handle PNG transparency
                c.drawImage(logo_path, self.width - self.margin - 100, self.height - 120, 
                           width=100, height=80, 
                           preserveAspectRatio=True, 
                           mask='auto')
            
            # University name and details - positioned on the left
            c.setFont("Helvetica-Bold", 14)
            c.drawString(self.margin, self.height - 50, "UNIVERSIDAD NACIONAL DEL COMAHUE")
            
            c.setFont("Helvetica-Bold", 12)
            c.drawString(self.margin, self.height - 70, "CENTRO REGIONAL UNIVERSITARIO BARILOCHE")
            
            c.setFont("Helvetica", 12)
            c.drawString(self.margin, self.height - 90, "Secretaría Académica")
            c.drawString(self.margin, self.height - 105, "Selección de Personal Docente")
            
        except Exception as e:
            # If logo fails to load, just add text header
            c.setFont("Helvetica-Bold", 16)
            c.drawString(self.margin, self.height - 50, "UNIVERSIDAD NACIONAL DEL COMAHUE")
            c.setFont("Helvetica-Bold", 14)
            c.drawString(self.margin, self.height - 70, "CENTRO REGIONAL UNIVERSITARIO BARILOCHE")
    
    def _add_title(self, c, placeholders):
        """Add the form title"""
        c.setFont("Helvetica-Bold", 16)
        title = "FORMULARIO DE INSCRIPCIÓN"
        title_width = c.stringWidth(title, "Helvetica-Bold", 16)
        c.drawString((self.width - title_width) / 2, self.height - 160, title)
        
        c.setFont("Helvetica-Bold", 12)
        subtitle = "SELECCIÓN DE PERSONAL DOCENTE"
        subtitle_width = c.stringWidth(subtitle, "Helvetica-Bold", 12)
        c.drawString((self.width - subtitle_width) / 2, self.height - 180, subtitle)
    
    def _add_concurso_info(self, c, concurso_data, placeholders):
        """Add concurso information section"""
        y_start = self.height - 220
        
        # Section title
        c.setFont("Helvetica-Bold", 14)
        c.drawString(self.margin, y_start, "INFORMACIÓN DEL CONCURSO")
        
        # Draw line under title
        c.line(self.margin, y_start - 5, self.width - self.margin, y_start - 5)
        
        y_position = y_start - 25
        c.setFont("Helvetica", 11)
        
        # Concurso details in two columns
        left_column_x = self.margin
        right_column_x = self.width / 2 + 20
        line_height = 18
        
        # Left column - with wider spacing for labels
        info_items_left = [
            ("Concurso N°:", placeholders.get('id_concurso', '')),
            ("Departamento:", placeholders.get('departamento_nombre', '')),
            ("Área:", placeholders.get('area', '')),
            ("Orientación:", placeholders.get('orientacion', '')),
            ("Categoría:", f"{placeholders.get('categoria_nombre', '')} ({placeholders.get('categoria_codigo', '')})"),
        ]
        
        # Right column - with shorter labels and wider spacing
        info_items_right = [
            ("Dedicación:", placeholders.get('dedicacion', '')),
            ("Localización:", placeholders.get('localizacion', '')),
            ("Tipo:", placeholders.get('tipo_concurso', '')),
            ("Cant. Cargos:", placeholders.get('cant_cargos_numero', '')),
            ("Cierre Insc.:", placeholders.get('cierre_inscripcion_fecha', '')),
            ("Expediente:", placeholders.get('expediente', '')),
        ]
        
        # Draw left column with adequate spacing
        for i, (label, value) in enumerate(info_items_left):
            y = y_position - (i * line_height)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(left_column_x, y, label)
            c.setFont("Helvetica", 10)
            c.drawString(left_column_x + 90, y, str(value))
        
        # Draw right column with adequate spacing  
        for i, (label, value) in enumerate(info_items_right):
            y = y_position - (i * line_height)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(right_column_x, y, label)
            c.setFont("Helvetica", 10)
            c.drawString(right_column_x + 90, y, str(value))
        
        return y_position - (len(info_items_left) * line_height) - 20
    
    def _add_personal_data_form(self, c, y_start):
        """Add personal data form section"""
        # Section title
        c.setFont("Helvetica-Bold", 14)
        c.drawString(self.margin, y_start, "DATOS PERSONALES DEL POSTULANTE")
        
        # Draw line under title
        c.line(self.margin, y_start - 5, self.width - self.margin, y_start - 5)
        
        y_position = y_start - 30
        form_width = self.content_width
        field_height = 25
        box_height = 20
        
        # Personal data fields
        fields = [
            "Apellido y Nombre:",
            "DNI:",
            "CUIL:",
            "Fecha de Nacimiento:",
            "Domicilio:",
            "Localidad:",
            "Código Postal:",
            "Teléfono:",
            "Correo Electrónico:",
            "Título de Grado:",
            "Universidad de Egreso:",
            "Año de Egreso:",
        ]
        
        c.setFont("Helvetica", 11)
        
        for i, field in enumerate(fields):
            y = y_position - (i * field_height)
            
            # Draw field label - positioned to align with middle of box
            label_y = y - 8  # Adjust to center label with box middle
            c.drawString(self.margin, label_y, field)
            
            # Draw field box aligned with the label
            box_x = self.margin + 140  # More space for longer labels
            box_width = form_width - 140
            box_y = y - box_height  # Box positioned relative to y
            c.rect(box_x, box_y, box_width, box_height)
        
        return y_position - (len(fields) * field_height) - 20
    
    def _add_required_documents(self, c, y_start, concurso_data):
        """Add required documents checklist using dynamic data from JSON"""
        # Check if we need a new page
        if y_start < 200:
            c.showPage()
            y_start = self.height - 100
        
        # Section title
        c.setFont("Helvetica-Bold", 14)
        c.drawString(self.margin, y_start, "DOCUMENTACIÓN REQUERIDA")
        
        # Draw line under title
        c.line(self.margin, y_start - 5, self.width - self.margin, y_start - 5)
        
        y_position = y_start - 30
        c.setFont("Helvetica", 11)
        
        # Use dynamic required documents from JSON data
        required_docs = concurso_data.get('required_docs', [])
        
        # Document type translations/friendly names
        doc_translations = {
            'DNI': 'Fotocopia certificada del DNI',
            'CV': 'Curriculum Vitae actualizado y documentación respaldatoria',
            'DOCUMENTACION_RESPALDATORIA_CV': 'Documentación respaldatoria del CV',
            'TITULO_UNIVERSITARIO': 'Fotocopia certificada del título universitario',
            'ANTECEDENTES_IDONEIDAD': 'Certificados de antecedentes de idoneidad',
            'PROPUESTA_PROGRAMA': 'Propuesta de programa detallada',
            'ACTIVIDADES_PREVISTAS': 'Plan de actividades previstas',
            'PLAN_FORMACION_RRHH': 'Programa de formación de recursos humanos',
            'PLAN_IVE': 'Plan de investigación/vinculación/extensión',
            'PLAN_IVE_OPCIONAL': 'Plan de investigación/vinculación/extensión (opcional)',
            'PLAN_O_PROGRAMA_ACTIVIDADES': 'Plan o programa de actividades',
            'PROPUESTA_EJERCICIO_O_TP': 'Propuesta de ejercicio o trabajo práctico',
        }
        
        # Create document list with checkboxes
        documents = []
        
        if required_docs:
            # Use only documents from JSON - no fallback or fixed documents
            for doc_code in required_docs:
                friendly_name = doc_translations.get(doc_code, doc_code)
                documents.append(f"□ {friendly_name}")
        
        # If no dynamic documents available, show a message
        if not documents:
            documents = ["□ No hay documentación específica requerida para este concurso"]
        
        line_height = 16
        for i, document in enumerate(documents):
            y = y_position - (i * line_height)
            # Check if we need a new page
            if y < 150:
                c.showPage()
                y = self.height - 100 - (i * line_height)
            c.drawString(self.margin + 10, y, document)
        
        # Add important note
        y_note = y_position - (len(documents) * line_height) - 30
        
        # Check if we need a new page for the note
        if y_note < 150:
            c.showPage()
            y_note = self.height - 100
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(self.margin, y_note, "INFORMACIÓN IMPORTANTE:")
        
        c.setFont("Helvetica", 10)
        note_text = [
            "• Toda la documentación debe presentarse en original y fotocopia.",
            "• Las fotocopias serán certificadas por la Secretaría Académica al momento de la presentación.",
            "• El postulante debe verificar que toda la documentación esté completa antes de la presentación.",
            "• La documentación incompleta puede resultar en la descalificación de la postulación.",
            f"• Para más información sobre requisitos específicos, consulte la Secretaría Académica.",
        ]
        
        for i, note in enumerate(note_text):
            y = y_note - 20 - (i * 12)
            # Check if we need a new page for notes
            if y < 80:
                c.showPage()
                y = self.height - 80 - (i * 12)
            c.drawString(self.margin + 10, y, note)
        
        return y_note - 100
    
    def _add_footer(self, c):
        """Add footer with signature area and date"""
        # Signature area
        footer_y = 150
   
        
        # Signature lines
        sig_y = footer_y - 60
        left_sig_x = self.margin + 50
        right_sig_x = self.width - self.margin - 200
        
        # Postulant signature
        c.line(left_sig_x, sig_y, left_sig_x + 150, sig_y)
        c.drawString(left_sig_x + 30, sig_y - 15, "Lugar y Fecha")
        
        # Reception signature (for office use)
        c.line(right_sig_x, sig_y, right_sig_x + 150, sig_y)
        c.drawString(right_sig_x + 15, sig_y - 15, "Firma del Postulante")
        
        # Generation timestamp
        c.setFont("Helvetica", 8)
        timestamp = f"Documento generado el {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        c.drawString(self.margin, 30, timestamp)
        
        # Page number
        c.drawRightString(self.width - self.margin, 30, "Página 1")
