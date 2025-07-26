/**
 * Google Drive Loading System
 * Shows loading overlay specifically for Google Drive operations
 * Provides visual feedback for long-running Drive operations
 */

class GoogleDriveLoading {
    constructor() {
        this.requestCount = 0;
        this.loadingOverlay = null;
        this.init();
    }

    init() {
        this.createLoadingOverlay();
        this.setupGlobalMethods();
    }

    createLoadingOverlay() {
        // Remove existing overlay if any
        const existing = document.getElementById('googleDriveLoadingOverlay');
        if (existing) {
            existing.remove();
        }

        // Create new loading overlay
        this.loadingOverlay = document.createElement('div');
        this.loadingOverlay.id = 'googleDriveLoadingOverlay';
        this.loadingOverlay.className = 'google-drive-loading-overlay';
        this.loadingOverlay.innerHTML = `
            <div class="spinner-container">
                <div class="google-drive-spinner"></div>
                <div class="loading-text">Procesando con Google Drive...</div>
                <div class="loading-subtitle">Por favor espere</div>
            </div>
        `;
        
        // Add styles
        this.loadingOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.7);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            opacity: 0;
            visibility: hidden;
            transition: opacity 0.3s ease, visibility 0.3s ease;
        `;
        
        document.body.appendChild(this.loadingOverlay);
        
        // Add spinner styles
        const style = document.createElement('style');
        style.textContent = `
            .google-drive-loading-overlay .spinner-container {
                text-align: center;
                background: white;
                padding: 2rem;
                border-radius: 12px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                max-width: 300px;
            }
            
            .google-drive-spinner {
                width: 48px;
                height: 48px;
                border: 4px solid #e3f2fd;
                border-top: 4px solid #2196f3;
                border-radius: 50%;
                animation: drive-spin 1s linear infinite;
                margin: 0 auto 1rem;
            }
            
            @keyframes drive-spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            .google-drive-loading-overlay .loading-text {
                font-size: 1.1rem;
                font-weight: 600;
                color: #333;
                margin-bottom: 0.5rem;
            }
            
            .google-drive-loading-overlay .loading-subtitle {
                font-size: 0.9rem;
                color: #666;
            }
            
            .google-drive-loading-overlay.active {
                opacity: 1;
                visibility: visible;
            }
        `;
        document.head.appendChild(style);
    }

    showLoading(message = 'Procesando con Google Drive...', subtitle = 'Por favor espere') {
        this.requestCount++;
        if (this.loadingOverlay) {
            const textElement = this.loadingOverlay.querySelector('.loading-text');
            const subtitleElement = this.loadingOverlay.querySelector('.loading-subtitle');
            if (textElement) {
                textElement.textContent = message;
            }
            if (subtitleElement) {
                subtitleElement.textContent = subtitle;
            }
            this.loadingOverlay.classList.add('active');
        }
    }

    hideLoading() {
        this.requestCount = Math.max(0, this.requestCount - 1);
        if (this.requestCount === 0 && this.loadingOverlay) {
            this.loadingOverlay.classList.remove('active');
        }
    }

    setupGlobalMethods() {
        // Make Google Drive loading globally accessible
        window.GoogleDriveLoading = {
            show: (message, subtitle) => this.showLoading(message, subtitle),
            hide: () => this.hideLoading(),
            
            // Predefined methods for common Google Drive operations
            showFolderCreation: () => this.showLoading('Creando carpetas en Google Drive...', 'Configurando estructura de archivos'),
            showDocumentGeneration: () => this.showLoading('Generando documento...', 'Procesando plantilla en Google Drive'),
            showFileUpload: () => this.showLoading('Subiendo archivo...', 'Guardando en Google Drive'),
            showFileDownload: () => this.showLoading('Descargando archivo...', 'Obteniendo desde Google Drive'),
            showEmailSending: () => this.showLoading('Enviando email...', 'Procesando notificación'),
            showSignatureProcess: () => this.showLoading('Procesando firma...', 'Actualizando documento'),
            showFolderDeletion: () => this.showLoading('Eliminando carpeta...', 'Limpiando Google Drive')
        };
    }
}

// Initialize Google Drive loading system
let googleDriveLoading;

document.addEventListener('DOMContentLoaded', function() {
    googleDriveLoading = new GoogleDriveLoading();
});

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible' && googleDriveLoading) {
        // Reset loading state when page becomes visible again
        googleDriveLoading.requestCount = 0;
        if (googleDriveLoading.loadingOverlay) {
            googleDriveLoading.loadingOverlay.classList.remove('active');
        }
    }
});
