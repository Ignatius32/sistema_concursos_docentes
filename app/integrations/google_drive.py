import os
import requests
from datetime import datetime, timezone
import base64
import logging

# Set up logger for debugging
logger = logging.getLogger(__name__)

class GoogleDriveAPI:
    def __init__(self):
        self.api_url = "https://script.google.com/macros/s/AKfycbzu1aD_-L822DTVyLgqfqkn5eytgJNkorivbtXAiwlSd2dzqA5PCHyVtA9y5lHAXizu/exec"
        self.secure_token = os.environ.get('GOOGLE_DRIVE_SECURE_TOKEN')
        if not self.secure_token:
            raise ValueError("GOOGLE_DRIVE_SECURE_TOKEN environment variable is not set")

    def create_concurso_folder(self, concurso_id, departamento, area, orientacion, categoria, dedicacion):
        """Create a folder in Google Drive for a new concurso."""
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        folder_name = f"{concurso_id}_{departamento}_{area}_{orientacion}_{categoria}_{dedicacion}_{timestamp}"

        response = requests.post(self.api_url, json={
            'action': 'createFolder',
            'folderName': folder_name,
            'token': self.secure_token
        })

        if response.status_code != 200:
            raise Exception(f"Error creating Google Drive folder: {response.text}")

        folder_data = response.json()
        if folder_data.get('status') != 'success':
            raise Exception(f"Error from Google Drive API: {folder_data.get('message')}")
        
        # Create subfolders inside the main folder with descriptive names
        subfolders = {
            'borradores': f"borradores_{departamento}_{categoria}_{dedicacion}_{concurso_id}",
            'postulantes': f"postulantes_{departamento}_{categoria}_{dedicacion}_{concurso_id}",
            'documentos_firmados': f"documentos_firmados_{departamento}_{categoria}_{dedicacion}_{concurso_id}",
            'tribunal': f"tribunal_{departamento}_{categoria}_{dedicacion}_{concurso_id}"
        }
        
        subfolder_ids = {}
        
        for folder_type, subfolder_name in subfolders.items():
            subfolder_response = requests.post(self.api_url, json={
                'action': 'createNestedFolder',
                'parentFolderId': folder_data.get('folderId'),
                'folderName': subfolder_name,
                'token': self.secure_token
            })
            
            if subfolder_response.status_code != 200:
                raise Exception(f"Error creating {folder_type} folder: {subfolder_response.text}")
                
            subfolder_data = subfolder_response.json()
            if subfolder_data.get('status') != 'success':
                raise Exception(f"Error from Google Drive API when creating {folder_type} folder: {subfolder_data.get('message')}")
            
            subfolder_ids[f"{folder_type}FolderId"] = subfolder_data.get('folderId')
            
        # Return all folder IDs
        return {
            'folderId': folder_data.get('folderId'),
            'borradoresFolderId': subfolder_ids['borradoresFolderId'],
            'postulantesFolderId': subfolder_ids['postulantesFolderId'],
            'documentosFirmadosFolderId': subfolder_ids['documentos_firmadosFolderId'],
            'tribunalFolderId': subfolder_ids['tribunalFolderId']
        }

    def create_postulante_folder(self, concurso_folder_id, dni, apellido, nombre, categoria, dedicacion):
        """Create a folder in Google Drive for a postulante inside a concurso folder."""
        folder_name = f"{apellido}_{nombre}_{dni}_{categoria}_{dedicacion}"

        response = requests.post(self.api_url, json={
            'action': 'createPostulanteFolder',
            'concursoFolderId': concurso_folder_id,
            'folderName': folder_name,
            'token': self.secure_token
        })

        if response.status_code != 200:
            raise Exception(f"Error creating Google Drive folder: {response.text}")

        folder_data = response.json()
        if folder_data.get('status') != 'success':
            raise Exception(f"Error from Google Drive API: {folder_data.get('message')}")

        return folder_data.get('folderId')

    def create_document_from_template(self, template_name, data, folder_id, file_name):
        """
        Create a document from a template in Google Drive.
        
        Args:
            template_name (str): Name of the template to use (must be defined in TEMPLATES in the Apps Script)
            data (dict): Dictionary of placeholder values to replace in the template
            folder_id (str): The ID of the Google Drive folder where the document should be created
            file_name (str): The name for the new document
            
        Returns:
            tuple: (file_id, web_view_link) - ID and URL of the created document
        """
        response = requests.post(self.api_url, json={
            'action': 'createDocFromTemplate',
            'templateName': template_name,
            'data': data,
            'folderId': folder_id,
            'fileName': file_name,
            'token': self.secure_token
        })
        
        if response.status_code != 200:
            raise Exception(f"Error creating document from template: {response.text}")
            
        doc_data = response.json()
        if doc_data.get('status') != 'success':
            raise Exception(f"Error from Google Drive API: {doc_data.get('message')}")
            
        return doc_data.get('fileId'), doc_data.get('webViewLink')

    def upload_document(self, folder_id, file_name, file_data):
        """
        Upload a document to Google Drive in the specified folder.
        
        Args:
            folder_id (str): The ID of the Google Drive folder
            file_name (str): The name to give the file in Drive
            file_data (bytes): The file content as bytes
        """
        # Encode file data as base64 for transmission
        file_data_b64 = base64.b64encode(file_data).decode('utf-8')
        
        response = requests.post(self.api_url, json={
            'action': 'uploadFile',
            'folderId': folder_id,
            'fileName': file_name,
            'fileData': file_data_b64,
            'token': self.secure_token
        })

        if response.status_code != 200:
            raise Exception(f"Error uploading file to Google Drive: {response.text}")

        upload_data = response.json()
        if upload_data.get('status') != 'success':
            raise Exception(f"Error from Google Drive API: {upload_data.get('message')}")

        return upload_data.get('fileId'), upload_data.get('webViewLink')

    def get_file_content(self, file_id):
        """
        Retrieve the content of a file from Google Drive.
        
        Args:
            file_id (str): The ID of the file to retrieve
            
        Returns:
            dict: Contains fileData (base64 encoded content), fileName, and mimeType
        """
        try:
            logger.info(f"Getting file content for file_id: {file_id}")
            response = requests.post(self.api_url, json={
                'action': 'getFileContent',
                'fileId': file_id,
                'token': self.secure_token
            }, timeout=30)

            if response.status_code != 200:
                error_message = f"Error retrieving file from Google Drive: {response.text}"
                logger.error(error_message)
                raise Exception(error_message)

            data = response.json()
            if data.get('status') != 'success':
                error_message = f"Error from Google Drive API: {data.get('message')}"
                logger.error(error_message)
                raise Exception(error_message)

            return {
                'fileData': data.get('fileData'),
                'fileName': data.get('fileName'),
                'mimeType': data.get('mimeType', 'application/pdf')
            }
            
        except Exception as e:
            logger.error(f"Error getting file content from Drive: {str(e)}")
            raise

    def add_signature_to_pdf(self, file_id, nombre, apellido, dni, firma_count=0):
        """
        Add a signature directly to a PDF file in Google Drive.
        This method is deprecated. Instead, use get_file_content to download,
        add_signature_stamp from pdf_utils to stamp, and overwrite_file to upload.
        
        Args:
            file_id (str): The ID of the PDF file to sign
            nombre (str): First name of the signer
            apellido (str): Last name of the signer
            dni (str): DNI of the signer
            firma_count (int): Current count of signatures on the document
            
        Returns:
            tuple: (new_file_id, web_view_link) - ID and URL of the signed document
        """
        logger.warning("add_signature_to_pdf method is deprecated. Use the Python PDF stamping instead.")
        response = requests.post(self.api_url, json={
            'action': 'addSignatureToPdf',
            'fileId': file_id,
            'nombre': nombre,
            'apellido': apellido,
            'dni': dni,
            'firmaCount': firma_count,
            'token': self.secure_token
        })

        if response.status_code != 200:
            raise Exception(f"Error adding signature to PDF: {response.text}")

        signature_data = response.json()
        if signature_data.get('status') != 'success':
            raise Exception(f"Error from Google Drive API: {signature_data.get('message')}")

        return signature_data.get('fileId'), signature_data.get('webViewLink')

    def overwrite_file(self, file_id, file_data):
        """
        Overwrite an existing file in Google Drive.
        
        Args:
            file_id (str): The ID of the file to overwrite
            file_data (str): The base64-encoded file content
            
        Returns:
            tuple: (file_id, web_view_link) - ID and URL of the updated file
        """
        try:
            logger.info(f"Overwriting file: {file_id}")
            response = requests.post(self.api_url, json={
                'action': 'overwriteFile',
                'fileId': file_id,
                'fileData': file_data,
                'mimeType': 'application/pdf',  # Explicitly set PDF MIME type
                'token': self.secure_token
            }, timeout=30)
            
            if response.status_code != 200:
                error_message = f"Error from Google Drive API: {response.text}"
                logger.error(error_message)
                raise Exception(error_message)

            data = response.json()
            if data.get('status') != 'success':
                error_message = f"Error from Google Drive API: {data.get('message')}"
                logger.error(error_message)
                raise Exception(error_message)

            new_file_id = data.get('fileId')
            web_view_link = data.get('webViewLink')
            logger.info(f"Successfully overwrote file. New file ID: {new_file_id}")
            
            # Return as tuple since that's what's expected by the calling code
            return new_file_id, web_view_link
            
        except Exception as e:
            logger.error(f"Error overwriting file in Drive: {str(e)}")
            raise

    def delete_file(self, file_id):
        """
        Delete a file from Google Drive.
        
        Args:
            file_id (str): The ID of the file to delete
        """
        response = requests.post(self.api_url, json={
            'action': 'deleteFile',
            'fileId': file_id,
            'token': self.secure_token
        })

        if response.status_code != 200:
            raise Exception(f"Error deleting file from Google Drive: {response.text}")

        delete_data = response.json()
        if delete_data.get('status') != 'success':
            raise Exception(f"Error from Google Drive API: {delete_data.get('message')}")

        return delete_data.get('success')

    def delete_folder(self, folder_id):
        """
        Delete a folder from Google Drive.
        
        Args:
            folder_id (str): The ID of the folder to delete
        """
        response = requests.post(self.api_url, json={
            'action': 'deleteFolder',
            'folderId': folder_id,
            'token': self.secure_token
        })

        if response.status_code != 200:
            raise Exception(f"Error deleting folder from Google Drive: {response.text}")

        delete_data = response.json()
        if delete_data.get('status') != 'success':
            raise Exception(f"Error from Google Drive API: {delete_data.get('message')}")

        return delete_data.get('success')

    def get_folder_url(self, folder_id):
        """Get the URL for a Google Drive folder."""
        return f"https://drive.google.com/drive/folders/{folder_id}"

    def update_folder_name(self, folder_id, new_name):
        """
        Update a folder's name in Google Drive.
        
        Args:
            folder_id (str): The ID of the folder to rename
            new_name (str): The new name for the folder
        """
        response = requests.post(self.api_url, json={
            'action': 'renameFolder',
            'folderId': folder_id,
            'newName': new_name,
            'token': self.secure_token
        })

        if response.status_code != 200:
            raise Exception(f"Error renaming folder in Google Drive: {response.text}")

        rename_data = response.json()
        if rename_data.get('status') != 'success':
            raise Exception(f"Error from Google Drive API: {rename_data.get('message')}")

        return rename_data.get('success')

    def create_tribunal_folder(self, parent_folder_id, nombre, apellido, dni, rol):
        """Create a folder in Google Drive for a tribunal member inside the tribunal folder.
        
        Args:
            parent_folder_id (str): The ID of the parent tribunal folder
            nombre (str): First name of the tribunal member
            apellido (str): Last name of the tribunal member
            dni (str): DNI of the tribunal member
            rol (str): Role in the tribunal (Presidente/Vocal/Suplente)
            
        Returns:
            str: The ID of the created folder
        """
        folder_name = f"{rol}_{apellido}_{nombre}_{dni}"

        response = requests.post(self.api_url, json={
            'action': 'createNestedFolder',
            'parentFolderId': parent_folder_id,
            'folderName': folder_name,
            'token': self.secure_token
        })

        if response.status_code != 200:
            raise Exception(f"Error creating tribunal member folder: {response.text}")

        folder_data = response.json()
        if folder_data.get('status') != 'success':
            raise Exception(f"Error from Google Drive API: {folder_data.get('message')}")

        return folder_data.get('folderId')

    def send_email(self, to_email, subject, html_body, sender_name=None, attachment_ids=None, placeholders=None):
        """
        Send an email using Gmail with optional attachments and placeholder replacement.
        
        Args:
            to_email (str): Email address of the recipient
            subject (str): Email subject line (can contain placeholders)
            html_body (str): HTML content of the email (can contain placeholders)
            sender_name (str, optional): Name to display as the sender
            attachment_ids (list, optional): List of Google Drive file IDs to attach to the email
            placeholders (dict, optional): Dictionary of placeholder values to replace in subject and body
                                          Format: {'placeholder_name': 'replacement_value'}
                                          
        Returns:
            dict: Result information about the sent email
            
        Example:
            send_email(
                'recipient@example.com',
                'Your application for <<position>> position',
                '<p>Dear <<name>>,</p><p>Your application has been received.</p>',
                'HR Department',
                ['1Ab2Cd3Ef4Gh5Ij6Kl7Mn8Op'],
                {'name': 'John Doe', 'position': 'Professor'}
            )
        """
        response = requests.post(self.api_url, json={
            'action': 'sendEmail',
            'to': to_email,
            'subject': subject,
            'htmlBody': html_body,
            'senderName': sender_name,
            'attachmentIds': attachment_ids or [],
            'placeholders': placeholders or {},
            'token': self.secure_token
        })

        if response.status_code != 200:
            raise Exception(f"Error sending email: {response.text}")

        email_data = response.json()
        if email_data.get('status') != 'success':
            raise Exception(f"Error from Google API: {email_data.get('message')}")

        return email_data