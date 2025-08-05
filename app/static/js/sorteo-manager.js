/**
 * Sorteo Manager - Handles the topic lottery functionality
 * Manages the UI interaction, animation, and AJAX communication for sorteo de temas
 */

class SorteoManager {
    constructor() {
        this.concursoId = null;
        this.sorteoModal = null;
        this.btnIniciarSorteo = null;
        this.sorteoAnimation = null;
        this.sorteoResult = null;
        this.progressBar = null;
        
        this.init();
    }

    init() {
        console.log('SorteoManager: Initializing...');
        
        // Get concurso ID from the page
        this.concursoId = this.getConcursoId();
        console.log('SorteoManager: Concurso ID:', this.concursoId);
        
        // Initialize DOM elements
        this.sorteoModal = document.getElementById('sortearTemaModal');
        this.btnIniciarSorteo = document.getElementById('btn-iniciar-sorteo');
        this.sorteoAnimation = document.getElementById('sorteo-animation');
        this.sorteoResult = document.getElementById('sorteo-result');
        this.progressBar = document.querySelector('#sorteo-animation .progress-bar');
        
        console.log('SorteoManager: DOM elements found:', {
            modal: !!this.sorteoModal,
            button: !!this.btnIniciarSorteo,
            animation: !!this.sorteoAnimation,
            result: !!this.sorteoResult,
            progressBar: !!this.progressBar
        });
        
        // Bind events
        this.bindEvents();
        
        console.log('SorteoManager: Initialization complete');
    }

    getConcursoId() {
        // Extract concurso ID from the URL or a data attribute
        const path = window.location.pathname;
        const match = path.match(/\/concursos\/(\d+)/);
        return match ? parseInt(match[1]) : null;
    }

    bindEvents() {
        if (this.btnIniciarSorteo) {
            this.btnIniciarSorteo.addEventListener('click', () => this.iniciarSorteo());
        }

        // Reset modal state when it's opened
        if (this.sorteoModal) {
            this.sorteoModal.addEventListener('show.bs.modal', () => this.resetModal());
        }
    }

    resetModal() {
        // Reset to initial state
        this.showAnimation();
        this.hideResult();
        this.resetProgressBar();
        this.btnIniciarSorteo.disabled = false;
        this.btnIniciarSorteo.innerHTML = '<i class="bi bi-shuffle"></i> Iniciar Sorteo';
    }

    showAnimation() {
        if (this.sorteoAnimation) {
            this.sorteoAnimation.classList.remove('d-none');
        }
    }

    hideAnimation() {
        if (this.sorteoAnimation) {
            this.sorteoAnimation.classList.add('d-none');
        }
    }

    showResult() {
        if (this.sorteoResult) {
            this.sorteoResult.classList.remove('d-none');
        }
    }

    hideResult() {
        if (this.sorteoResult) {
            this.sorteoResult.classList.add('d-none');
        }
    }

    resetProgressBar() {
        if (this.progressBar) {
            this.progressBar.style.width = '0%';
        }
    }

    updateProgressBar(percentage) {
        if (this.progressBar) {
            this.progressBar.style.width = percentage + '%';
        }
    }

    async iniciarSorteo() {
        if (!this.concursoId) {
            this.showError('Error: No se pudo identificar el concurso');
            return;
        }

        try {
            // Disable button and show loading state
            this.btnIniciarSorteo.disabled = true;
            this.btnIniciarSorteo.innerHTML = '<i class="bi bi-hourglass-split"></i> Sorteando...';

            // Start animation
            this.startSorteoAnimation();

            // Get CSRF token if available
            const csrfToken = document.querySelector('meta[name=csrf-token]')?.getAttribute('content');
            
            // Prepare headers
            const headers = {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            };
            
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            // Make the AJAX request
            const response = await fetch(`/concursos/${this.concursoId}/realizar-sorteo`, {
                method: 'POST',
                headers: headers,
                credentials: 'same-origin'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Error del servidor (${response.status})`);
            }

            const data = await response.json();

            if (!data.success) {
                throw new Error(data.error || 'Error inesperado en la respuesta del servidor');
            }

            // Stop animation and show results
            await this.showSorteoResult(data);

        } catch (error) {
            console.error('Error durante el sorteo:', error);
            this.showError(error.message || 'Error inesperado durante el sorteo');
        }
    }

    async startSorteoAnimation() {
        // Simulate progressive loading
        const steps = [20, 40, 60, 80, 95];
        
        for (let i = 0; i < steps.length; i++) {
            await this.delay(300 + Math.random() * 200); // Random delay between 300-500ms
            this.updateProgressBar(steps[i]);
        }
    }

    async showSorteoResult(data) {
        // Complete the progress bar
        this.updateProgressBar(100);
        
        // Wait a bit for the animation to complete
        await this.delay(500);

        // Hide animation and show results
        this.hideAnimation();
        this.showResult();

        // Update the results content
        this.updateResultsContent(data);

        // Update button state
        this.btnIniciarSorteo.innerHTML = '<i class="bi bi-check-circle"></i> Sorteo Completado';
    }

    updateResultsContent(data) {
        const temasContainer = this.sorteoResult.querySelector('.temas-container');
        if (!temasContainer) return;

        // Clear previous content
        temasContainer.innerHTML = '';

        // Parse selected temas
        const selectedTemas = data.selectedTemas.split('|');
        const allTemas = data.allTemas;
        const numDrawn = data.numDrawn;

        // Create header
        const header = document.createElement('div');
        header.className = 'alert alert-success mb-4';
        header.innerHTML = `
            <h4 class="alert-heading">
                <i class="bi bi-trophy"></i> 
                ${numDrawn === 1 ? 'Tema Sorteado' : 'Temas Sorteados'}
            </h4>
            <p class="mb-0">
                ${numDrawn === 1 ? 'El tema seleccionado es:' : `Los ${numDrawn} temas seleccionados son:`}
            </p>
        `;
        temasContainer.appendChild(header);

        // Create selected temas display
        selectedTemas.forEach((tema, index) => {
            const temaElement = document.createElement('div');
            temaElement.className = 'card mb-3 border-success shadow-sm';
            temaElement.style.animation = `fadeInUp 0.5s ease-out ${index * 0.2}s both`;
            temaElement.innerHTML = `
                <div class="card-body text-center">
                    <h5 class="card-title text-success mb-3">
                        <i class="bi bi-star-fill"></i> 
                        ${numDrawn > 1 ? `Tema ${index + 1}` : 'Tema Sorteado'}
                    </h5>
                    <p class="card-text fs-5 fw-bold text-dark">${tema.trim()}</p>
                </div>
            `;
            temasContainer.appendChild(temaElement);
        });

        // Add all available topics info (collapsed)
        if (allTemas.length > numDrawn) {
            const availableTopicsElement = document.createElement('div');
            availableTopicsElement.className = 'mt-4';
            availableTopicsElement.innerHTML = `
                <div class="card border-light">
                    <div class="card-header bg-light">
                        <button class="btn btn-link btn-sm p-0 text-decoration-none" type="button" 
                                data-bs-toggle="collapse" data-bs-target="#availableTopics" 
                                aria-expanded="false" aria-controls="availableTopics">
                            <i class="bi bi-list-ul"></i> Ver todos los temas disponibles (${allTemas.length})
                        </button>
                    </div>
                    <div class="collapse" id="availableTopics">
                        <div class="card-body">
                            <div class="row">
                                ${allTemas.map((tema, idx) => {
                                    const isSelected = selectedTemas.includes(tema);
                                    return `
                                        <div class="col-md-6 mb-2">
                                            <span class="badge ${isSelected ? 'bg-success' : 'bg-secondary'} me-2">
                                                ${idx + 1}
                                            </span>
                                            ${tema.trim()}
                                            ${isSelected ? '<i class="bi bi-check-circle-fill text-success ms-1"></i>' : ''}
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            `;
            temasContainer.appendChild(availableTopicsElement);
        }

        // Show summary info
        const summaryElement = document.createElement('div');
        summaryElement.className = 'mt-4 text-muted small text-center';
        summaryElement.innerHTML = `
            <div class="border-top pt-3">
                <p class="mb-1">
                    <strong>Temas disponibles:</strong> ${allTemas.length} |
                    <strong>Temas sorteados:</strong> ${numDrawn}
                </p>
                <p class="mb-0">
                    <i class="bi bi-clock"></i> Sorteo realizado el ${new Date().toLocaleString('es-ES')}
                </p>
            </div>
        `;
        temasContainer.appendChild(summaryElement);
        
        // Add CSS for animations
        this.addAnimationStyles();

        // Show success message and reload info
        const reloadInfo = document.createElement('div');
        reloadInfo.className = 'alert alert-info mt-3 mb-0';
        reloadInfo.innerHTML = `
            <i class="bi bi-info-circle"></i> 
            <small>La página se actualizará automáticamente en unos segundos para mostrar el resultado del sorteo.</small>
        `;
        temasContainer.appendChild(reloadInfo);

        // Trigger page reload after a delay to show updated state
        setTimeout(() => {
            window.location.reload();
        }, 6000);
    }

    showError(errorMessage) {
        // Hide animation and show error
        this.hideAnimation();
        
        // Update results area with error
        const temasContainer = this.sorteoResult.querySelector('.temas-container');
        if (temasContainer) {
            temasContainer.innerHTML = `
                <div class="alert alert-danger">
                    <h4 class="alert-heading">
                        <i class="bi bi-exclamation-triangle"></i> Error en el Sorteo
                    </h4>
                    <p class="mb-0">${errorMessage}</p>
                    <hr>
                    <p class="mb-0">
                        <small class="text-muted">
                            Verifique que los temas estén consolidados y que tenga permisos de administrador.
                        </small>
                    </p>
                </div>
            `;
        }
        
        this.showResult();

        // Reset button
        this.btnIniciarSorteo.disabled = false;
        this.btnIniciarSorteo.innerHTML = '<i class="bi bi-shuffle"></i> Intentar Nuevamente';
    }

    addAnimationStyles() {
        // Add fadeInUp animation if not already added
        if (!document.getElementById('sorteo-animations')) {
            const style = document.createElement('style');
            style.id = 'sorteo-animations';
            style.textContent = `
                @keyframes fadeInUp {
                    from {
                        opacity: 0;
                        transform: translateY(30px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('SorteoManager: DOM Content Loaded');
    
    // Only initialize if we're on a concurso details page and the modal exists
    const sorteoModal = document.getElementById('sortearTemaModal');
    console.log('SorteoManager: Modal found:', !!sorteoModal);
    
    if (sorteoModal) {
        console.log('SorteoManager: Creating new instance...');
        const manager = new SorteoManager();
        
        // Expose to window for debugging
        window.sorteoManager = manager;
        console.log('SorteoManager: Instance created and exposed as window.sorteoManager');
    } else {
        console.log('SorteoManager: Not on sorteo page, skipping initialization');
    }
});
