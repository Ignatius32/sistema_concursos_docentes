import os
import requests
from datetime import datetime, timezone
import base64

class GoogleDriveAPI:
    def __init__(self):
        self.api_url = "https://script.google.com/macros/s/AKfycbzu1aD_-L822DTVyLgqfqkn5eytgJNkorivbtXAiwlSd2dzqA5PCHyVtA9y5lHAXizu/exec"
        self.secure_token = os.environ.get('SECURE_TOKEN')

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
        
        # Create a postulantes folder inside the main folder
        postulantes_folder_name = f"postulantes_{departamento}_{categoria}_{dedicacion}_{concurso_id}"
        postulantes_response = requests.post(self.api_url, json={
            'action': 'createNestedFolder',
            'parentFolderId': folder_data.get('folderId'),
            'folderName': postulantes_folder_name,
            'token': self.secure_token
        })
        
        if postulantes_response.status_code != 200:
            raise Exception(f"Error creating postulantes folder: {postulantes_response.text}")
            
        postulantes_data = postulantes_response.json()
        if postulantes_data.get('status') != 'success':
            raise Exception(f"Error from Google Drive API when creating postulantes folder: {postulantes_data.get('message')}")
            
        # Return all folder IDs
        return {
            'folderId': folder_data.get('folderId'),
            'borradoresFolderId': folder_data.get('borradoresFolderId'),
            'postulantesFolderId': postulantes_data.get('folderId'),
            'documentosFirmadosFolderId': folder_data.get('documentosFirmadosFolderId')
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

    def overwrite_file(self, file_id, file_data):
        """
        Overwrite an existing file in Google Drive.
        
        Args:
            file_id (str): The ID of the file to overwrite
            file_data (bytes): The new file content as bytes
        """
        # Encode file data as base64 for transmission
        file_data_b64 = base64.b64encode(file_data).decode('utf-8')
        
        response = requests.post(self.api_url, json={
            'action': 'overwriteFile',
            'fileId': file_id,
            'fileData': file_data_b64,
            'token': self.secure_token
        })

        if response.status_code != 200:
            raise Exception(f"Error overwriting file in Google Drive: {response.text}")

        overwrite_data = response.json()
        if overwrite_data.get('status') != 'success':
            raise Exception(f"Error from Google Drive API: {overwrite_data.get('message')}")

        return overwrite_data.get('fileId'), overwrite_data.get('webViewLink')

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