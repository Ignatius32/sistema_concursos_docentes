/**
 * Tribunal Search Module
 * Handles persona search functionality for tribunal member management
 */
class TribunalSearchManager {
    constructor(concursoId) {
        this.concursoId = concursoId;
        this.searchTimeout = null;
        this.init();
    }
    
    init() {
        this.bindSearchEvents();
        console.log('TribunalSearchManager initialized for concurso:', this.concursoId);
    }
    
    bindSearchEvents() {
        // Search input
        const personaSearch = document.getElementById('personaSearch');
        if (personaSearch) {
            personaSearch.addEventListener('input', (e) => this.handleSearch(e));
            console.log('Search input event bound');
        } else {
            console.error('personaSearch input not found');
        }
        
        // Close search results button
        const closeSearchBtn = document.querySelector('#searchResults .btn-outline-secondary');
        if (closeSearchBtn) {
            closeSearchBtn.addEventListener('click', () => this.hideSearchResults());
        }
    }
    
    handleSearch(e) {
        const query = e.target.value.trim();
        
        // Clear previous timeout
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }
        
        // Hide results if query is too short
        if (query.length < 2) {
            this.hideSearchResults();
            return;
        }
        
        console.log('Searching for:', query);
        
        // Debounce search
        this.searchTimeout = setTimeout(() => {
            this.searchPersonas(query);
        }, 300);
    }
      async searchPersonas(query) {
        try {
            console.log('API call - Searching for:', query);
              // Use the API URL from the global configuration if available
            const baseUrl = window.location.pathname.includes('/selecciones-docentes') ? '/selecciones-docentes' : '';
            let apiUrl = `${baseUrl}/api/buscar-personas`;
            if (window.TRIBUNAL_API_CONFIG && window.TRIBUNAL_API_CONFIG.buscarPersonasUrl) {
                apiUrl = window.TRIBUNAL_API_CONFIG.buscarPersonasUrl;
            }
            
            // Build URL with query parameters
            const params = new URLSearchParams({
                q: query
            });
            
            // Add concurso_id if available to exclude already assigned personas
            if (window.TRIBUNAL_API_CONFIG && window.TRIBUNAL_API_CONFIG.concursoId) {
                params.append('concurso_id', window.TRIBUNAL_API_CONFIG.concursoId);
            }
            
            const url = `${apiUrl}?${params.toString()}`;
            console.log('API URL:', url);
            
            const response = await fetch(url);
            console.log('Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
              const data = await response.json();
            console.log('API Response:', data);
            
            // Handle different response formats
            let personas = [];
            if (data.personas) {
                // Direct personas array (from tribunal endpoint)
                personas = data.personas;
            } else if (data.status === 'success' && data.personas) {
                // Wrapped response (from api endpoint)
                personas = data.personas;
            } else if (Array.isArray(data)) {
                // Direct array response
                personas = data;
            }
            
            this.displaySearchResults(personas);
        } catch (error) {
            console.error('Error searching personas:', error);
            this.showAlert('Error al buscar personas: ' + error.message, 'danger');
        }
    }
    
    displaySearchResults(personas) {
        const resultsContainer = document.getElementById('searchResultsList');
        const searchResults = document.getElementById('searchResults');
        
        if (!resultsContainer || !searchResults) {
            console.error('Search result containers not found');
            return;
        }
        
        console.log('Displaying', personas.length, 'search results');
        
        if (personas.length === 0) {
            resultsContainer.innerHTML = '<div class="list-group-item text-muted text-center py-3">No se encontraron personas</div>';
        } else {
            resultsContainer.innerHTML = personas.map(persona => `
                <div class="list-group-item list-group-item-action d-flex justify-content-between align-items-center" 
                     data-persona-id="${persona.id}">
                    <div class="flex-grow-1">
                        <strong>${persona.apellido}, ${persona.nombre}</strong><br>
                        <small class="text-muted">DNI: ${persona.dni}${persona.correo ? ' - ' + persona.correo : ''}</small>
                    </div>
                    <button type="button" class="btn btn-sm btn-outline-primary add-member" 
                            data-persona-id="${persona.id}"
                            data-persona='${JSON.stringify(persona)}'>
                        <i class="fas fa-plus"></i> Agregar
                    </button>
                </div>
            `).join('');
            
            // Bind add member events
            this.bindAddMemberEvents();
        }
        
        searchResults.style.display = 'block';
    }
    
    bindAddMemberEvents() {
        const addButtons = document.querySelectorAll('#searchResultsList .add-member');
        console.log('Binding events for', addButtons.length, 'add buttons');
        
        addButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                try {
                    const personaData = JSON.parse(e.target.closest('.add-member').dataset.persona);
                    console.log('Adding member:', personaData);
                    
                    // Dispatch custom event for member addition
                    const event = new CustomEvent('memberAdd', {
                        detail: { persona: personaData }
                    });
                    document.dispatchEvent(event);
                    
                } catch (error) {
                    console.error('Error parsing persona data:', error);
                    this.showAlert('Error al procesar los datos de la persona', 'danger');
                }
            });
        });
    }
    
    hideSearchResults() {
        const searchResults = document.getElementById('searchResults');
        if (searchResults) {
            searchResults.style.display = 'none';
        }
    }
    
    clearSearch() {
        const personaSearch = document.getElementById('personaSearch');
        if (personaSearch) {
            personaSearch.value = '';
        }
        this.hideSearchResults();
    }
    
    showAlert(message, type = 'info') {
        const alertArea = document.getElementById('alertArea');
        if (!alertArea) {
            console.error('Alert area not found');
            return;
        }
        
        const alertId = 'alert-' + Date.now();
        const alertHtml = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'warning' ? 'exclamation-triangle' : type === 'danger' ? 'exclamation-circle' : 'info-circle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        alertArea.insertAdjacentHTML('beforeend', alertHtml);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    }
}

// Export for use in other modules
window.TribunalSearchManager = TribunalSearchManager;
