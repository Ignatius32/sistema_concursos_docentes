"""
Google Drive Loading Integration
Provides utilities to integrate Google Drive operations with frontend loading indicators
"""

from functools import wraps
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

class GoogleDriveLoadingManager:
    """
    Manager class for coordinating Google Drive operations with frontend loading
    """
    
    @staticmethod
    def is_ajax_request():
        """Check if the current request is an AJAX request"""
        return request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    @staticmethod
    def with_loading(operation_type=None, custom_message=None):
        """
        Decorator to wrap Google Drive operations with loading indicators
        
        Args:
            operation_type (str): Type of operation (folder_creation, document_generation, etc.)
            custom_message (str): Custom loading message
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # For AJAX requests, we can send loading state info
                if GoogleDriveLoadingManager.is_ajax_request():
                    try:
                        # Log the start of the operation
                        operation_name = operation_type or func.__name__
                        logger.info(f"Starting Google Drive operation: {operation_name}")
                        
                        # Execute the function
                        result = func(*args, **kwargs)
                        
                        # Log success
                        logger.info(f"Completed Google Drive operation: {operation_name}")
                        return result
                        
                    except Exception as e:
                        # Log error
                        logger.error(f"Failed Google Drive operation: {operation_name} - {str(e)}")
                        raise
                else:
                    # For regular requests, just execute normally
                    return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    @staticmethod
    def create_loading_response(operation_type, message=None, progress=None):
        """
        Create a response that can be used to update loading state
        
        Args:
            operation_type (str): Type of operation being performed
            message (str): Custom message to display
            progress (int): Progress percentage (0-100)
        """
        response_data = {
            'loading': True,
            'operation_type': operation_type,
            'message': message or f'Procesando {operation_type}...',
        }
        
        if progress is not None:
            response_data['progress'] = progress
            
        return jsonify(response_data)

# Predefined decorators for common operations
def with_folder_creation_loading(func):
    """Decorator for folder creation operations"""
    return GoogleDriveLoadingManager.with_loading('folder_creation')(func)

def with_document_generation_loading(func):
    """Decorator for document generation operations"""
    return GoogleDriveLoadingManager.with_loading('document_generation')(func)

def with_file_upload_loading(func):
    """Decorator for file upload operations"""
    return GoogleDriveLoadingManager.with_loading('file_upload')(func)

def with_file_download_loading(func):
    """Decorator for file download operations"""
    return GoogleDriveLoadingManager.with_loading('file_download')(func)

def with_email_sending_loading(func):
    """Decorator for email sending operations"""
    return GoogleDriveLoadingManager.with_loading('email_sending')(func)

def with_signature_process_loading(func):
    """Decorator for signature processing operations"""
    return GoogleDriveLoadingManager.with_loading('signature_process')(func)

# Template helper functions for Jinja2
def get_loading_script_for_operation(operation_type):
    """
    Get JavaScript code to show loading for a specific operation type
    
    Args:
        operation_type (str): Type of operation
        
    Returns:
        str: JavaScript code to show loading
    """
    operation_map = {
        'folder_creation': 'showFolderCreation',
        'document_generation': 'showDocumentGeneration',
        'file_upload': 'showFileUpload',
        'file_download': 'showFileDownload',
        'email_sending': 'showEmailSending',
        'signature_process': 'showSignatureProcess',
        'folder_deletion': 'showFolderDeletion'
    }
    
    method_name = operation_map.get(operation_type, 'show')
    return f"if (window.GoogleDriveLoading) {{ window.GoogleDriveLoading.{method_name}(); }}"

def get_hide_loading_script():
    """Get JavaScript code to hide loading"""
    return "if (window.GoogleDriveLoading) { window.GoogleDriveLoading.hide(); }"

# Helper functions for manual control in views
class GoogleDriveJS:
    """Helper class to generate JavaScript for Google Drive loading"""
    
    @staticmethod
    def show_folder_creation():
        return "GoogleDriveLoading.showFolderCreation();"
    
    @staticmethod
    def show_document_generation():
        return "GoogleDriveLoading.showDocumentGeneration();"
    
    @staticmethod
    def show_file_upload():
        return "GoogleDriveLoading.showFileUpload();"
    
    @staticmethod
    def show_file_download():
        return "GoogleDriveLoading.showFileDownload();"
    
    @staticmethod
    def show_email_sending():
        return "GoogleDriveLoading.showEmailSending();"
    
    @staticmethod
    def show_signature_process():
        return "GoogleDriveLoading.showSignatureProcess();"
    
    @staticmethod
    def show_folder_deletion():
        return "GoogleDriveLoading.showFolderDeletion();"
    
    @staticmethod
    def hide():
        return "GoogleDriveLoading.hide();"
