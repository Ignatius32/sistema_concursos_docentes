from PyPDF2 import PdfReader, PdfWriter
import io
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

def add_signature_stamp(pdf_content, apellido, nombre, dni, signature_count=0):
    """Add a signature stamp to the footer of each page in a PDF.
    
    Args:
        pdf_content (bytes or str): Either PDF bytes or a comma-separated byte array string
        apellido (str): Last name of the signer
        nombre (str): First name of the signer
        dni (str): DNI of the signer
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
        stamp_text = f"Firmado por: {apellido}, {nombre} (DNI: {dni}) - {timestamp}"
        
        # Metadata to be added to the PDF - note the forward slashes for PDF spec compliance
        metadata = {
            '/SignerNombre': nombre,
            '/SignerApellido': apellido,
            '/SignerDNI': dni,
            '/SignerTimestamp': timestamp,
            '/SignatureCount': str(signature_count + 1),
        }
        
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
            # Look for signature pattern: "Firmado por: {apellido}, ... (DNI: {dni})"
            signature_pattern = f"Firmado por: {signer['apellido']}"
            dni_pattern = f"DNI: {signer['dni']}"
            
            if signature_pattern not in text or dni_pattern not in text:
                missing_signers.append(signer)
        
        return len(missing_signers) == 0, missing_signers
    
    except Exception as e:
        logger.error(f"Error verifying signed PDF: {str(e)}")
        # In case of any error, return that verification failed
        return False, expected_signers