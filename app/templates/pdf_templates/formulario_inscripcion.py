"""
PDF Template for Formulario de Inscripción (Inscription Form)
This template generates a professional inscription form for selecciones docentes.
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
    
    def _draw_page_number(self, c):
        """Draw the current page number at the bottom-right of the page."""
        try:
            c.setFont("Helvetica", 8)
            c.drawRightString(self.width - self.margin, 30, f"Página {c.getPageNumber()}")
        except Exception:
            # Fallback without breaking rendering
            pass
    
    def _wrap_text(self, c, text, max_width, font="Helvetica", size=10):
        """Wrap text into lines that fit within max_width using current canvas font metrics."""
        c.setFont(font, size)
        text = text or ""
        words = text.split()
        if not words:
            return [""]
        lines = []
        line = ""
        for w in words:
            candidate = (line + " " + w).strip()
            if c.stringWidth(candidate, font, size) <= max_width:
                line = candidate
            else:
                if line:
                    lines.append(line)
                # If a single word is longer than max_width, force-break by characters
                if c.stringWidth(w, font, size) > max_width and len(w) > 1:
                    chunk = ""
                    for ch in w:
                        if c.stringWidth(chunk + ch, font, size) <= max_width:
                            chunk += ch
                        else:
                            if chunk:
                                lines.append(chunk)
                            chunk = ch
                    line = chunk
                else:
                    line = w
        if line:
            lines.append(line)
        return lines
        
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
        # Set PDF metadata title to match the visible title
        try:
            c.setTitle("Solicitud de Inscripción y Declaración Jurada")
        except Exception:
            pass
        
        # Add header with logo
        self._add_header(c)
        
        # Add title
        self._add_title(c, placeholders)
        
        # Add concurso information section
        y_position = self._add_concurso_info(c, concurso_data, placeholders)
        
        # Check if we need a new page
        if y_position < 400:
            # finalize current page with page number before breaking
            self._draw_page_number(c)
            c.showPage()
            y_position = self.height - 80
        
        # Add personal data form section
        y_position = self._add_personal_data_form(c, y_position)
        
        # Add required documents section with dynamic data
        y_position = self._add_required_documents(c, y_position, concurso_data)

        # Add footer (signature + timestamp) on the last page
        self._add_footer(c)
        # Draw page number on the last page
        self._draw_page_number(c)

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
        title = "SOLICITUD DE INSCRIPCIÓN Y DECLARACIÓN JURADA"
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
        c.drawString(self.margin, y_start, "INFORMACIÓN DE LA SELECCIÓN")
        
        # Draw line under title
        c.line(self.margin, y_start - 5, self.width - self.margin, y_start - 5)
        
        y_position = y_start - 25
        c.setFont("Helvetica", 11)
        
        # Two columns layout with wrapping and dynamic row height
        left_column_x = self.margin
        right_column_x = self.width / 2 + 20  # provide gutter
        label_width = 90
        line_height = 16

        # Data
        info_items_left = [
            ("N° de Registro:", str(placeholders.get('id_concurso', ''))),
            ("Departamento:", str(placeholders.get('departamento_nombre', ''))),
            ("Área:", str(placeholders.get('area', ''))),
            ("Orientación:", str(placeholders.get('orientacion', ''))),
            ("Categoría:", f"{placeholders.get('categoria_nombre', '')} ({placeholders.get('categoria_codigo', '')})".strip()),
        ]
        info_items_right = [
            ("Dedicación:", str(placeholders.get('dedicacion', ''))),
            ("Localización:", str(placeholders.get('localizacion', ''))),
            ("Tipo:", str(placeholders.get('tipo_concurso', ''))),
            ("Cant. Cargos:", str(placeholders.get('cant_cargos_numero', ''))),
            ("Cierre Insc.:", str(placeholders.get('cierre_inscripcion_fecha', ''))),
            ("Expediente:", str(placeholders.get('expediente', ''))),
        ]

        # Compute max widths for values
        left_value_x = left_column_x + label_width
        left_max_right = right_column_x - 10
        max_width_left = max(10, left_max_right - left_value_x)
        right_value_x = right_column_x + label_width
        right_max_right = self.width - self.margin
        max_width_right = max(10, right_max_right - right_value_x)

        # Number of rows is the max length among both columns
        total_rows = max(len(info_items_left), len(info_items_right))
        y_cursor = y_position

        for i in range(total_rows):
            # Left item
            left_label, left_val = (info_items_left[i] if i < len(info_items_left) else ("", ""))
            # Right item
            right_label, right_val = (info_items_right[i] if i < len(info_items_right) else ("", ""))

            # Wrap values
            left_lines = self._wrap_text(c, left_val, max_width_left, font="Helvetica", size=10) if left_val else [""]
            right_lines = self._wrap_text(c, right_val, max_width_right, font="Helvetica", size=10) if right_val else [""]
            row_lines = max(len(left_lines), len(right_lines))
            row_height = max(1, row_lines) * line_height

            # Page safety (unlikely here, but safe)
            if y_cursor - row_height < 120:
                self._draw_page_number(c)
                c.showPage()
                # re-draw section header if we break page? keep it simple and continue
                y_cursor = self.height - 100

            # Draw left label and wrapped value
            if left_label:
                c.setFont("Helvetica-Bold", 10)
                c.drawString(left_column_x, y_cursor, left_label)
            c.setFont("Helvetica", 10)
            for j, l in enumerate(left_lines):
                c.drawString(left_value_x, y_cursor - (j * line_height), l)

            # Draw right label and wrapped value aligned to the same top line
            if right_label:
                c.setFont("Helvetica-Bold", 10)
                c.drawString(right_column_x, y_cursor, right_label)
            c.setFont("Helvetica", 10)
            for j, l in enumerate(right_lines):
                c.drawString(right_value_x, y_cursor - (j * line_height), l)

            # Advance cursor for next row
            y_cursor = y_cursor - row_height

        return y_cursor - 20
    
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
        """Add Declaración Jurada at the top, then required documents, then Información Importante."""
        # Ensure we start with enough space
        if y_start < 200:
            self._draw_page_number(c)
            c.showPage()
            y_start = self.height - 100

        y = y_start

        # 1) Declaración Jurada section
        c.setFont("Helvetica-Bold", 14)
        c.drawString(self.margin, y, "DECLARACIÓN JURADA")
        c.line(self.margin, y - 5, self.width - self.margin, y - 5)
        y -= 30

        declaracion_text = (
            "Por la presente informo en carácter de Declaración Jurada no estar comprendido en las causales de "
            "inhabilitación para el desempeño de cargos públicos."
        )
        x_decl = self.margin + 10
        max_width_decl = self.width - self.margin - x_decl
        lines_decl = self._wrap_text(c, declaracion_text, max_width_decl, font="Helvetica", size=10)
        c.setFont("Helvetica", 10)
        for line in lines_decl:
            if y < 150:
                self._draw_page_number(c)
                c.showPage()
                y = self.height - 100
            c.drawString(x_decl, y, line)
            y -= 12
        y -= 10

        # 2) Documentación Requerida section
        # Add a bit of extra top margin before the section title
        extra_top_margin = 10
        y -= extra_top_margin
        if y < 200:
            self._draw_page_number(c)
            c.showPage()
            y = self.height - 100 - extra_top_margin
        c.setFont("Helvetica-Bold", 14)
        c.drawString(self.margin, y, "DOCUMENTACIÓN PRESENTADA")
        c.line(self.margin, y - 5, self.width - self.margin, y - 5)
        y -= 30
        c.setFont("Helvetica", 11)

        required_docs = concurso_data.get('required_docs', [])
        doc_translations = {
    'DNI': 'Copia de DNI (un archivo).',
    'CV': 'Curriculum Vitae actualizado y documentación respaldatoria (un archivo).',
    'TITULO_UNIVERSITARIO': 'Copia del Título Universitario (un archivo).',
    'ANTECEDENTES_IDONEIDAD': 'Documentación que acredita idoneidad en caso de no contar con Título Universitario (un archivo).',
    'PROGRAMA_ACTIVIDADES': 'Programa y actividades previstas para el dictado de alguna de las asignaturas del área y orientación objeto del concurso; o bien, del área si no corresponde orientación (un archivo).',
    'PLAN_FORMACION_RRHH': 'Programa de Formación de Recursos Humanos (un archivo).',
    'PLAN_IVE': 'Plan de Actividades de Investigación, Vinculación y/o Extensión (un archivo).',
    'PLAN_IVE_OPCIONAL': 'Plan de Actividades de Investigación, Vinculación y/o Extensión (opcional) (un archivo).',
    'PLAN_O_PROGRAMA_ACTIVIDADES': 'Plan/programa de actividades prácticas y/o de aplicación para la asignatura que concursa según área y orientación (un archivo).',
    'PROPUESTA_EJERCICIO_O_TP': 'Propuesta de ejercicio o trabajo práctico de un tema específico correspondiente a una unidad o tema del programa de la asignatura a concursar, según área y orientación (un archivo).'
        }

        x_docs = self.margin + 10
        max_width_docs = self.width - self.margin - x_docs
        line_height = 16

        if required_docs:
            for doc_code in required_docs:
                friendly = doc_translations.get(doc_code, doc_code)
                item_text = f"□ {friendly}"
                lines = self._wrap_text(c, item_text, max_width_docs, font="Helvetica", size=11)
                c.setFont("Helvetica", 11)
                for line in lines:
                    if y < 150:
                        self._draw_page_number(c)
                        c.showPage()
                        y = self.height - 100
                    c.drawString(x_docs, y, line)
                    y -= line_height
        else:
            msg = "□ No hay documentación específica requerida para este concurso"
            lines = self._wrap_text(c, msg, max_width_docs, font="Helvetica", size=11)
            c.setFont("Helvetica", 11)
            for line in lines:
                if y < 150:
                    self._draw_page_number(c)
                    c.showPage()
                    y = self.height - 100
                c.drawString(x_docs, y, line)
                y -= line_height

        # 3) Información Importante section
        y -= 20
        if y < 150:
            self._draw_page_number(c)
            c.showPage()
            y = self.height - 100
        c.setFont("Helvetica-Bold", 12)
        c.drawString(self.margin, y, "INFORMACIÓN IMPORTANTE:")
        y -= 18
        notes = [
            "• La inscripción se realiza de forma digital enviando los archivos necesarios (en formato pdf) al correo electrónico institucional asignado por la Unidad Académica y que consta en la publicación del llamado.",
            "• Los archivos correspondientes al CV u documentación respaldatoria tienen carácter de declaración jurada.",
        ]
        x_notes = self.margin + 10
        max_width_notes = self.width - self.margin - x_notes
        c.setFont("Helvetica", 10)
        for note in notes:
            lines = self._wrap_text(c, note, max_width_notes, font="Helvetica", size=10)
            for line in lines:
                if y < 80:
                    self._draw_page_number(c)
                    c.showPage()
                    y = self.height - 80
                c.drawString(x_notes, y, line)
                y -= 12
            y -= 6

        return y - 60
    
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
        
    # Page number is drawn per-page by _draw_page_number
