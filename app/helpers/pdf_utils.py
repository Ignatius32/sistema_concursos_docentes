from PyPDF2 import PdfReader, PdfWriter
import io
import base64
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import logging

# Set up logger
logger = logging.getLogger(__name__)

def convert_byte_array_to_bytes(byte_array):
    """Convert a comma-separated byte array string to bytes.
    
    Args:
        byte_array (str): A string of comma-separated byte values
        
    Returns:
        bytes: The reconstructed bytes object
    """
    try:
        # Split the string and convert each value to an integer
        values = [int(x.strip()) for x in byte_array.split(',')]
        # Convert to bytes
        return bytes(values)
    except Exception as e:
        logger.error(f"Error converting byte array to bytes: {str(e)}")
        return None

def add_signature_stamp(pdf_content, apellido, nombre, dni, cargo=None, signature_count=0):
    """Add a signature stamp to the footer of each page in a PDF.
    
    Args:
        pdf_content (bytes or str): Either PDF bytes or a comma-separated byte array string
        apellido (str): Last name of the signer
        nombre (str): First name of the signer
        dni (str): DNI of the signer
        cargo (str, optional): Role or position of the signer. If provided, included in stamp.
        signature_count (int): Current count of signatures on the document (0-based)
        
    Returns:
        bytes: The modified PDF with stamps added
    """
    logger.info(f"Adding signature for {apellido}, {nombre} (DNI: {dni}), signature count: {signature_count}")
    
    try:
        # Check if input is a string (byte array) and convert if necessary
        if isinstance(pdf_content, str):
            pdf_bytes = convert_byte_array_to_bytes(pdf_content)
            if pdf_bytes is None:
                raise ValueError("Failed to convert byte array to PDF bytes")
        else:
            pdf_bytes = pdf_content

        # Create PDF reader
        existing_pdf = PdfReader(io.BytesIO(pdf_bytes))
        output = PdfWriter()
        
        # Get page size from first page
        page = existing_pdf.pages[0]
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)
          # Create timestamp
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        # Prepare stamp text
        if cargo:
            stamp_text = f"Firmado por: {apellido}, {nombre} (Cargo: {cargo}, DNI: {dni}) - {timestamp}"
        else:
            stamp_text = f"Firmado por: {apellido}, {nombre} (DNI: {dni}) - {timestamp}"
        
        # Metadata to be added to the PDF - note the forward slashes for PDF spec compliance
        metadata = {
            '/SignerNombre': nombre,
            '/SignerApellido': apellido,
            '/SignerDNI': dni,
            '/SignerTimestamp': timestamp,
            '/SignatureCount': str(signature_count + 1),
        }
        
        # Add cargo to metadata if provided
        if cargo:
            metadata['/SignerCargo'] = cargo
        
        # Add each page with a stamp
        for i in range(len(existing_pdf.pages)):
            # Get the page
            page = existing_pdf.pages[i]
            
            # Create stamp template for this page
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(page_width, page_height))
            can.setFont("Helvetica", 8)
            
            # Calculate position based on signature count
            # Each signature will be placed higher than the previous one
            y_position = 20 + (12 * signature_count)
            
            # Maximum of 10 signatures before wrapping to second column
            if signature_count >= 10:
                # Start a second column on the left side
                column = 1 + (signature_count // 10)
                row = signature_count % 10
                y_position = 20 + (12 * row)
                text_width = can.stringWidth(stamp_text, "Helvetica", 8)
                x_position = page_width - text_width - 50 - (column * 200)  # Move left for each column
            else:
                # Add text at bottom of page
                text_width = can.stringWidth(stamp_text, "Helvetica", 8)
                x_position = page_width - text_width - 50  # 50 points from right margin
            
            # Add background for better visibility
            border_width = text_width + 10
            border_height = 12
            
            # Draw a filled rectangle with light background
            can.setFillColorRGB(0.95, 0.95, 0.95)  # Light gray background
            can.rect(x_position - 5, y_position - 2, border_width, border_height, fill=True)
            
            # Draw border
            can.setStrokeColorRGB(0.8, 0.8, 0.8)  # Light gray border
            can.rect(x_position - 5, y_position - 2, border_width, border_height)
            
            # Draw text
            can.setFillColorRGB(0, 0, 0)  # Black text
            can.drawString(x_position, y_position, stamp_text)
            can.save()
            
            # Move to beginning of the BytesIO buffer
            packet.seek(0)
            stamp = PdfReader(packet)
            
            # Merge the stamp with the page
            page.merge_page(stamp.pages[0])
            
            # Add page to output
            output.add_page(page)
        
        # Add metadata to the PDF
        output.add_metadata(metadata)
        
        # Write the modified content to a bytes buffer
        output_buffer = io.BytesIO()
        output.write(output_buffer)
        output_buffer.seek(0)
        
        logger.info(f"Successfully added signature stamp to PDF, output size: {len(output_buffer.getvalue())} bytes")
        return output_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error adding signature stamp to PDF: {str(e)}")
        # Return original content in the same format it was received
        return pdf_content

def verify_signed_pdf(pdf_bytes, expected_signers):
    """Verify if a PDF contains signatures from all expected signers.
    
    Args:
        pdf_bytes (bytes): The PDF file content
        expected_signers (list): List of dicts with signer information: [{'apellido': '...', 'dni': '...'}]
        
    Returns:
        tuple: (is_fully_signed, missing_signers)
    """
    try:
        # Extract text from PDF to search for signatures
        pdf = PdfReader(io.BytesIO(pdf_bytes))
        
        # Extract text from all pages
        text = ""
        for page_num in range(len(pdf.pages)):
            page = pdf.pages[page_num]
            text += page.extract_text()
          # Check for each expected signer
        missing_signers = []
        for signer in expected_signers:
            # Look for signature pattern: "Firmado por: {apellido}, ... (DNI: {dni})" or with Cargo
            signature_pattern = f"Firmado por: {signer['apellido']}"
            dni_pattern = f"DNI: {signer['dni']}"
            
            # A signer is present if both signature pattern and DNI pattern are found
            if signature_pattern not in text or dni_pattern not in text:
                missing_signers.append(signer)
        
        return len(missing_signers) == 0, missing_signers
    
    except Exception as e:
        logger.error(f"Error verifying signed PDF: {str(e)}")
        # In case of any error, return that verification failed
        return False, expected_signers

def create_cover_page(concurso, postulante, document_index):
    """Create a cover page (caratula) with concurso info, postulante info, and document index.
    
    Args:
        concurso: Concurso object with competition information
        postulante: Postulante object with applicant information
        document_index: List of tuples (folio_start, document_type)
        
    Returns:
        bytes: PDF bytes of the cover page
    """
    try:
        # Create a new PDF with reportlab
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Add "Folio 1" stamp at top right
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(width - 50, height - 50, "Folio 1")
          # Title
        c.setFont("Helvetica-Bold", 16)
        title = "DOCUMENTACIÓN DE POSTULANTE"
        title_width = c.stringWidth(title, "Helvetica-Bold", 16)
        c.drawString((width - title_width) / 2, height - 100, title)
        
        # Concurso Information
        y_position = height - 150
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_position, "INFORMACIÓN DEL CONCURSO")
        
        y_position -= 30
        c.setFont("Helvetica", 12)
        c.drawString(70, y_position, f"Concurso ID: {concurso.id}")
        
        y_position -= 20
        c.drawString(70, y_position, f"Departamento: {concurso.departamento_rel.nombre if concurso.departamento_rel else 'N/A'}")
        
        y_position -= 20
        c.drawString(70, y_position, f"Área: {concurso.area}")
        
        y_position -= 20
        c.drawString(70, y_position, f"Orientación: {concurso.orientacion}")
        
        y_position -= 20
        c.drawString(70, y_position, f"Categoría: {concurso.categoria_nombre} ({concurso.categoria})")
        
        y_position -= 20
        c.drawString(70, y_position, f"Dedicación: {concurso.dedicacion}")
        
        y_position -= 20
        c.drawString(70, y_position, f"Cantidad de Cargos: {concurso.cant_cargos}")
        
        # Postulante Information
        y_position -= 50
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_position, "INFORMACIÓN DEL POSTULANTE")
        
        y_position -= 30
        c.setFont("Helvetica", 12)
        c.drawString(70, y_position, f"Apellido y Nombre: {postulante.apellido}, {postulante.nombre}")
        
        y_position -= 20
        c.drawString(70, y_position, f"DNI: {postulante.dni}")
        
        y_position -= 20
        c.drawString(70, y_position, f"Correo: {postulante.correo}")
        
        if postulante.telefono:
            y_position -= 20
            c.drawString(70, y_position, f"Teléfono: {postulante.telefono}")
        
        if postulante.domicilio:
            y_position -= 20
            c.drawString(70, y_position, f"Domicilio: {postulante.domicilio}")
        
        # Document Index
        y_position -= 50
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_position, "ÍNDICE DE DOCUMENTOS")
        
        y_position -= 30
        c.setFont("Helvetica", 12)
        for folio_start, doc_type in document_index:
            c.drawString(70, y_position, f"Folio {folio_start}: {doc_type}")
            y_position -= 20
            
            # Check if we need a new page
            if y_position < 100:
                c.showPage()
                c.setFont("Helvetica-Bold", 12)
                c.drawRightString(width - 50, height - 50, "Folio 1 (continuación)")
                y_position = height - 100
                c.setFont("Helvetica", 12)
          # Footer with generation date
        c.setFont("Helvetica", 8)
        footer_text = f"Documento generado el {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        footer_width = c.stringWidth(footer_text, "Helvetica", 8)
        c.drawString((width - footer_width) / 2, 50, footer_text)
        
        c.save()
        buffer.seek(0)
        
        logger.info(f"Successfully created cover page for postulante {postulante.dni}")
        return buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error creating cover page: {str(e)}")
        return None

def add_folio_stamp(pdf_content, folio_number):
    """Add a folio number stamp to the top right of each page in a PDF.
    
    Args:
        pdf_content (bytes): PDF file content
        folio_number (int): Starting folio number for this document
        
    Returns:
        tuple: (modified_pdf_bytes, final_folio_number)
    """
    try:
        # Create PDF reader
        existing_pdf = PdfReader(io.BytesIO(pdf_content))
        output = PdfWriter()
        
        current_folio = folio_number
        
        # Add folio stamp to each page
        for i in range(len(existing_pdf.pages)):
            # Get the page
            page = existing_pdf.pages[i]
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)
            
            # Create stamp for this page
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(page_width, page_height))
            can.setFont("Helvetica-Bold", 12)
            
            # Add folio number at top right
            can.drawRightString(page_width - 50, page_height - 50, f"Folio {current_folio}")
            can.save()
            
            # Move to beginning of the BytesIO buffer
            packet.seek(0)
            stamp = PdfReader(packet)
            
            # Merge the stamp with the page
            page.merge_page(stamp.pages[0])
            
            # Add page to output
            output.add_page(page)
            
            current_folio += 1
        
        # Write the modified content to a bytes buffer
        output_buffer = io.BytesIO()
        output.write(output_buffer)
        output_buffer.seek(0)
        
        logger.info(f"Successfully added folio stamps starting from {folio_number}, ended at {current_folio - 1}")
        return output_buffer.getvalue(), current_folio - 1
        
    except Exception as e:
        logger.error(f"Error adding folio stamp to PDF: {str(e)}")
        return pdf_content, folio_number

def merge_postulante_documents(concurso, postulante, documents, drive_api=None):
    """Merge all documents for a postulante into a single PDF with cover page and folio stamps.
    
    Args:
        concurso: Concurso object
        postulante: Postulante object  
        documents: List of DocumentoPostulante objects (excluding DNI)
        drive_api: GoogleDriveAPI instance for downloading documents
        
    Returns:
        bytes: Merged PDF with cover page and folio stamps
    """
    try:
        # First, we need to download all documents and determine the folio structure
        document_index = []
        current_folio = 2  # Start at 2 because cover page is folio 1
        downloaded_docs = []
        
        # Download and build the index
        for doc in documents:
            if doc.tipo == 'DNI':  # Skip DNI documents
                continue
                
            try:
                # Extract file ID from Google Drive URL
                if '/file/d/' in doc.url:
                    file_id = doc.url.split('/file/d/')[1].split('/')[0]
                elif '/view' in doc.url:
                    file_id = doc.url.split('/')[-2]
                else:
                    logger.warning(f"Could not extract file ID from URL: {doc.url}")
                    continue
                  # Download document if drive_api is provided
                if drive_api:
                    try:
                        file_content = drive_api.get_file_content(file_id)
                        if file_content and file_content.get('fileData'):
                            # Decode base64 content
                            doc_bytes = base64.b64decode(file_content['fileData'])
                            
                            # Count pages in the document
                            try:
                                doc_pdf = PdfReader(io.BytesIO(doc_bytes))
                                page_count = len(doc_pdf.pages)
                            except:
                                page_count = 1  # Fallback to 1 page if can't read
                            
                            downloaded_docs.append({
                                'tipo': doc.tipo,
                                'bytes': doc_bytes,
                                'page_count': page_count
                            })
                            
                            document_index.append((current_folio, doc.tipo))
                            current_folio += page_count
                            
                        else:
                            logger.warning(f"No file data received for document {doc.tipo}")
                            
                    except Exception as e:
                        logger.error(f"Error downloading document {doc.tipo}: {str(e)}")
                        # Create placeholder if download fails
                        placeholder_bytes = create_placeholder_document(doc.tipo)
                        if placeholder_bytes:
                            downloaded_docs.append({
                                'tipo': doc.tipo,
                                'bytes': placeholder_bytes,
                                'page_count': 1
                            })
                            document_index.append((current_folio, doc.tipo))
                            current_folio += 1
                else:
                    # If no drive_api, create placeholder
                    placeholder_bytes = create_placeholder_document(doc.tipo)
                    if placeholder_bytes:
                        downloaded_docs.append({
                            'tipo': doc.tipo,
                            'bytes': placeholder_bytes,
                            'page_count': 1
                        })
                        document_index.append((current_folio, doc.tipo))
                        current_folio += 1
                        
            except Exception as e:
                logger.error(f"Error processing document {doc.tipo}: {str(e)}")
                continue
        
        if not downloaded_docs:
            logger.warning("No documents were successfully processed")
            return None
        
        # Create cover page
        cover_page_bytes = create_cover_page(concurso, postulante, document_index)
        if not cover_page_bytes:
            raise Exception("Failed to create cover page")
        
        # Create final merged PDF
        merger = PdfWriter()
        
        # Add cover page
        cover_pdf = PdfReader(io.BytesIO(cover_page_bytes))
        for page in cover_pdf.pages:
            merger.add_page(page)
        
        # Add each document with folio stamps
        current_folio = 2
        for doc_info in downloaded_docs:
            try:
                stamped_doc, final_folio = add_folio_stamp(doc_info['bytes'], current_folio)
                
                # Add to merger
                doc_pdf = PdfReader(io.BytesIO(stamped_doc))
                for page in doc_pdf.pages:
                    merger.add_page(page)
                
                current_folio = final_folio + 1
                
            except Exception as e:
                logger.error(f"Error processing document {doc_info['tipo']}: {str(e)}")
                continue
        
        # Write final merged PDF
        output_buffer = io.BytesIO()
        merger.write(output_buffer)
        output_buffer.seek(0)
        
        logger.info(f"Successfully merged documents for postulante {postulante.dni}")
        return output_buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error merging postulante documents: {str(e)}")
        return None

def create_placeholder_document(doc_type):
    """Create a placeholder document page for testing purposes.
    
    Args:
        doc_type (str): Type of document
        
    Returns:
        bytes: PDF bytes of placeholder page
    """
    try:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
          # Title
        c.setFont("Helvetica-Bold", 16)
        title = f"DOCUMENTO: {doc_type}"
        title_width = c.stringWidth(title, "Helvetica-Bold", 16)
        c.drawString((width - title_width) / 2, height/2, title)
        
        # Placeholder text
        c.setFont("Helvetica", 12)
        text1 = "Este es un documento placeholder"
        text1_width = c.stringWidth(text1, "Helvetica", 12)
        c.drawString((width - text1_width) / 2, height/2 - 50, text1)
        
        text2 = "En la implementación real, aquí iría el documento real"
        text2_width = c.stringWidth(text2, "Helvetica", 12)
        c.drawString((width - text2_width) / 2, height/2 - 70, text2)
        
        c.save()
        buffer.seek(0)
        
        return buffer.getvalue()
        
    except Exception as e:
        logger.error(f"Error creating placeholder document: {str(e)}")
        return None